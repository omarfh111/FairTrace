"""
Orchestrator Agent - Coordonne les agents et produit la décision finale.
Utilise LangGraph pour le workflow multi-agents.
Uses LangChain for automatic LangSmith tracing.
"""

import json
import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from .schemas import (
    ApplicationType, DecisionOutcome, RiskLevel,
    AgentAnalysis, FinalDecision, PredictionResult, SimilarCase
)
from . import rag_retriever
from . import financial_agent
from . import risk_agent
from . import narrative_agent
from . import prediction_agent

# Ensure LangSmith tracing is enabled
os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


# =============================================================================
# WORKFLOW STATE
# =============================================================================
class CreditDecisionState(TypedDict):
    """State for the multi-agent workflow."""
    application: dict
    application_type: str
    similar_cases: list
    financial_analysis: dict | None
    risk_analysis: dict | None
    narrative_analysis: dict | None
    prediction_result: dict | None
    final_decision: dict | None
    errors: list
    start_time: float


# =============================================================================
# WORKFLOW NODES
# =============================================================================
def retrieve_similar_cases_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Retrieve similar cases from Qdrant."""
    try:
        similar_cases = rag_retriever.retrieve_similar_cases(
            application_type=state["application_type"],
            application_data=state["application"],
            top_k=10
        )
        state["similar_cases"] = similar_cases
    except Exception as e:
        state["errors"].append(f"RAG Retrieval failed: {str(e)}")
        state["similar_cases"] = []
    return state


def financial_analysis_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Run financial metrics analysis."""
    try:
        analysis = financial_agent.analyze(
            application_type=state["application_type"],
            application=state["application"],
            similar_cases=state["similar_cases"]
        )
        state["financial_analysis"] = analysis.model_dump()
    except Exception as e:
        state["errors"].append(f"Financial Agent failed: {str(e)}")
        state["financial_analysis"] = None
    return state


def risk_analysis_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Run risk pattern analysis."""
    try:
        analysis = risk_agent.analyze(
            application_type=state["application_type"],
            application=state["application"],
            similar_cases=state["similar_cases"]
        )
        state["risk_analysis"] = analysis.model_dump()
    except Exception as e:
        state["errors"].append(f"Risk Agent failed: {str(e)}")
        state["risk_analysis"] = None
    return state


def narrative_analysis_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Run narrative analysis."""
    try:
        analysis = narrative_agent.analyze(
            application_type=state["application_type"],
            application=state["application"],
            similar_cases=state["similar_cases"]
        )
        state["narrative_analysis"] = analysis.model_dump()
    except Exception as e:
        state["errors"].append(f"Narrative Agent failed: {str(e)}")
        state["narrative_analysis"] = None
    return state


def prediction_analysis_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Run prediction analysis."""
    try:
        analysis, prediction = prediction_agent.analyze(
            application_type=state["application_type"],
            application=state["application"],
            similar_cases=state["similar_cases"]
        )
        state["prediction_result"] = {
            "analysis": analysis.model_dump(),
            "prediction": prediction.model_dump()
        }
    except Exception as e:
        state["errors"].append(f"Prediction Agent failed: {str(e)}")
        state["prediction_result"] = None
    return state


ORCHESTRATOR_SYSTEM_PROMPT = """Tu es l'Orchestrator Agent - l'agent final de décision de crédit.
Tu synthétises les analyses de 4 agents spécialisés pour prendre une décision finale.

Tu dois:
1. Pondérer les analyses de chaque agent
2. Identifier les consensus et divergences
3. Produire une décision finale: APPROVED, REJECTED, ou REVIEW_NEEDED
4. Expliquer clairement les raisons de ta décision
5. Citer les cas similaires historiques comme preuves

Réponds UNIQUEMENT en JSON valide avec cette structure:
{
    "decision": "APPROVED|REJECTED|REVIEW_NEEDED",
    "confidence": 0.0-1.0,
    "overall_risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "executive_summary": "résumé exécutif en 2-3 phrases",
    "key_reasons": ["raison1", "raison2", "raison3"],
    "conditions": ["condition1 si approuvé", "condition2"],
    "next_steps": ["étape1", "étape2"]
}"""


def final_decision_node(state: CreditDecisionState) -> CreditDecisionState:
    """Node: Synthesize all analyses and make final decision."""
    try:
        # Build synthesis context
        synthesis_context = f"""
=== TYPE DE DEMANDE ===
{state["application_type"].upper()}

=== ANALYSE FINANCIÈRE ===
"""
        if state["financial_analysis"]:
            fa = state["financial_analysis"]
            synthesis_context += f"""
Niveau de risque: {fa.get('risk_level', 'N/A')}
Confiance: {fa.get('confidence', 0)*100:.0f}%
Findings: {', '.join(fa.get('key_findings', [])[:3])}
Red flags: {', '.join(fa.get('red_flags', [])[:3])}
Signaux positifs: {', '.join(fa.get('positive_signals', [])[:3])}
Recommandation: {fa.get('recommendation', 'N/A')}
"""
        else:
            synthesis_context += "Non disponible\n"

        synthesis_context += "\n=== ANALYSE DE RISQUE ==="
        if state["risk_analysis"]:
            ra = state["risk_analysis"]
            synthesis_context += f"""
Niveau de risque: {ra.get('risk_level', 'N/A')}
Red flags: {', '.join(ra.get('red_flags', [])[:5])}
Recommandation: {ra.get('recommendation', 'N/A')}
"""
        else:
            synthesis_context += "Non disponible\n"

        synthesis_context += "\n=== ANALYSE NARRATIVE ==="
        if state["narrative_analysis"]:
            na = state["narrative_analysis"]
            synthesis_context += f"""
Niveau de risque: {na.get('risk_level', 'N/A')}
Findings: {', '.join(na.get('key_findings', [])[:3])}
Recommandation: {na.get('recommendation', 'N/A')}
"""
        else:
            synthesis_context += "Non disponible\n"

        synthesis_context += "\n=== PRÉDICTION ==="
        if state["prediction_result"]:
            pr = state["prediction_result"]
            pred = pr.get('prediction', {})
            synthesis_context += f"""
Probabilité de défaut: {pred.get('default_probability', 0)*100:.0f}%
Timeline risque: {pred.get('time_to_risk', 'N/A')}
Trajectoire: {pred.get('risk_trajectory', 'N/A')}
Signaux d'alerte: {', '.join(pred.get('warning_signals', [])[:3])}
"""
        else:
            synthesis_context += "Non disponible\n"

        # Add similar cases summary
        synthesis_context += "\n=== CAS SIMILAIRES HISTORIQUES ===\n"
        if state["similar_cases"]:
            outcomes = {}
            for case in state["similar_cases"]:
                outcome = case['payload'].get('outcome', 'UNKNOWN')
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
            
            for outcome, count in outcomes.items():
                synthesis_context += f"- {outcome}: {count} cas similaires\n"
        
        # Add any errors
        if state["errors"]:
            synthesis_context += f"\n⚠️ ERREURS: {', '.join(state['errors'])}\n"

        # Call LLM with LangChain (auto-traced)
        llm = get_llm()
        messages = [
            SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Prends la décision finale basée sur ces analyses:\n{synthesis_context}")
        ]
        
        response = llm.invoke(
            messages,
            config={"run_name": "Orchestrator Agent - Final Decision", "tags": ["orchestrator", "final_decision"]}
        )
        
        # Parse JSON with error handling
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            result = {
                "decision": "REVIEW_NEEDED",
                "confidence": 0.5,
                "overall_risk_level": "MEDIUM",
                "executive_summary": "Analyse complétée - revue manuelle recommandée",
                "key_reasons": ["Analyse automatique en cours de traitement"],
                "conditions": [],
                "next_steps": ["Révision par un analyste recommandée"]
            }
        
        # Calculate processing time
        processing_time = time.time() - state["start_time"]
        
        # Build final decision
        state["final_decision"] = {
            "decision": result.get('decision', 'REVIEW_NEEDED'),
            "confidence": result.get('confidence', 0.5),
            "overall_risk_level": result.get('overall_risk_level', 'MEDIUM'),
            "executive_summary": result.get('executive_summary', ''),
            "key_reasons": result.get('key_reasons', []),
            "conditions": result.get('conditions', []),
            "next_steps": result.get('next_steps', []),
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        state["errors"].append(f"Final Decision failed: {str(e)}")
        state["final_decision"] = {
            "decision": "REVIEW_NEEDED",
            "confidence": 0.0,
            "overall_risk_level": "HIGH",
            "executive_summary": f"Erreur dans le processus de décision: {str(e)}",
            "key_reasons": ["Échec du processus automatisé"],
            "conditions": [],
            "next_steps": ["Révision manuelle requise"]
        }
    
    return state


# =============================================================================
# BUILD WORKFLOW GRAPH
# =============================================================================
def build_credit_decision_graph():
    """Build the LangGraph workflow for credit decision."""
    
    # Create graph
    workflow = StateGraph(CreditDecisionState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_similar_cases_node)
    workflow.add_node("financial", financial_analysis_node)
    workflow.add_node("risk", risk_analysis_node)
    workflow.add_node("narrative", narrative_analysis_node)
    workflow.add_node("prediction", prediction_analysis_node)
    workflow.add_node("decision", final_decision_node)
    
    # Define edges (sequential for now, could be parallel)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "financial")
    workflow.add_edge("financial", "risk")
    workflow.add_edge("risk", "narrative")
    workflow.add_edge("narrative", "prediction")
    workflow.add_edge("prediction", "decision")
    workflow.add_edge("decision", END)
    
    return workflow.compile()


# =============================================================================
# MAIN ORCHESTRATOR FUNCTION
# =============================================================================
def evaluate_credit_application(
    application: dict,
    application_type: str
) -> FinalDecision:
    """
    Main entry point - evaluate a credit application through the multi-agent system.
    
    Args:
        application: Dict containing application data
        application_type: One of 'client', 'startup', 'enterprise'
    
    Returns:
        FinalDecision object with the decision and all analyses
    """
    # Initialize state
    initial_state: CreditDecisionState = {
        "application": application,
        "application_type": application_type,
        "similar_cases": [],
        "financial_analysis": None,
        "risk_analysis": None,
        "narrative_analysis": None,
        "prediction_result": None,
        "final_decision": None,
        "errors": [],
        "start_time": time.time()
    }
    
    # Build and run graph
    graph = build_credit_decision_graph()
    final_state = graph.invoke(initial_state)
    
    # Build FinalDecision object
    fd = final_state["final_decision"]
    
    # Collect all similar cases cited
    all_cited_cases = []
    for case in final_state["similar_cases"][:5]:
        all_cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={},
            summary=f"Cas historique avec outcome {case['payload'].get('outcome', 'UNKNOWN')}"
        ))
    
    # Build AgentAnalysis objects if available
    financial_analysis = None
    if final_state["financial_analysis"]:
        fa = final_state["financial_analysis"]
        financial_analysis = AgentAnalysis(
            agent_name=fa.get('agent_name', 'Financial Agent'),
            risk_level=RiskLevel(fa.get('risk_level', 'MEDIUM')),
            confidence=fa.get('confidence', 0.7),
            key_findings=fa.get('key_findings', []),
            red_flags=fa.get('red_flags', []),
            positive_signals=fa.get('positive_signals', []),
            recommendation=fa.get('recommendation', '')
        )
    
    risk_analysis = None
    if final_state["risk_analysis"]:
        ra = final_state["risk_analysis"]
        risk_analysis = AgentAnalysis(
            agent_name=ra.get('agent_name', 'Risk Agent'),
            risk_level=RiskLevel(ra.get('risk_level', 'MEDIUM')),
            confidence=ra.get('confidence', 0.7),
            key_findings=ra.get('key_findings', []),
            red_flags=ra.get('red_flags', []),
            positive_signals=ra.get('positive_signals', []),
            recommendation=ra.get('recommendation', '')
        )
    
    narrative_analysis = None
    if final_state["narrative_analysis"]:
        na = final_state["narrative_analysis"]
        narrative_analysis = AgentAnalysis(
            agent_name=na.get('agent_name', 'Narrative Agent'),
            risk_level=RiskLevel(na.get('risk_level', 'MEDIUM')),
            confidence=na.get('confidence', 0.7),
            key_findings=na.get('key_findings', []),
            red_flags=na.get('red_flags', []),
            positive_signals=na.get('positive_signals', []),
            recommendation=na.get('recommendation', '')
        )
    
    prediction_result = None
    if final_state["prediction_result"]:
        pr = final_state["prediction_result"].get('prediction', {})
        prediction_result = PredictionResult(
            default_probability=pr.get('default_probability', 0.5),
            time_to_risk=pr.get('time_to_risk'),
            risk_trajectory=pr.get('risk_trajectory', 'stable'),
            warning_signals=pr.get('warning_signals', [])
        )
    
    return FinalDecision(
        application_type=ApplicationType(application_type),
        decision=DecisionOutcome(fd.get('decision', 'REVIEW_NEEDED')),
        confidence=fd.get('confidence', 0.5),
        overall_risk_level=RiskLevel(fd.get('overall_risk_level', 'MEDIUM')),
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
        narrative_analysis=narrative_analysis,
        prediction_result=prediction_result,
        executive_summary=fd.get('executive_summary', ''),
        key_reasons=fd.get('key_reasons', []),
        similar_precedents=all_cited_cases,
        conditions=fd.get('conditions', []),
        next_steps=fd.get('next_steps', []),
        processing_time_seconds=fd.get('processing_time_seconds')
    )
