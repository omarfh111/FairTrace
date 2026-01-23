"""
Narrative Analysis Agent - Analyse les données textuelles.
Évalue le pitch, l'historique de crédit, et les rapports de risque.
Uses LangChain for automatic LangSmith tracing.
"""

import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from .schemas import AgentAnalysis, RiskLevel, SimilarCase

os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


NARRATIVE_SYSTEM_PROMPT = """Tu es un agent expert en analyse narrative et textuelle pour les décisions de crédit.
Tu analyses les éléments textuels des dossiers de crédit:
- Historique de crédit (clients)
- Pitch et vision (startups)
- Rapports de risque et profil CEO (entreprises)

Tu dois:
1. Extraire les signaux positifs et négatifs du texte
2. Détecter les incohérences ou éléments préoccupants
3. Évaluer la qualité et crédibilité des narratifs
4. Comparer avec les narratifs de cas similaires

Réponds UNIQUEMENT en JSON valide avec cette structure:
{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "red_flags": ["flag1", "flag2"],
    "positive_signals": ["signal1", "signal2"],
    "recommendation": "ta recommandation",
    "sentiment": "positive|neutral|negative",
    "credibility_score": 0.0-1.0
}"""


def analyze_narratives(
    application_type: str,
    application: dict,
    similar_cases: list[dict]
) -> AgentAnalysis:
    """Analyze narrative/textual data from the application."""
    
    if application_type == "client":
        main_narrative = application.get('credit_history', 'Aucun historique de crédit fourni.')
        
        narrative_context = f"""
=== NARRATIF DU DEMANDEUR (Client) ===
Objectif du prêt: {application.get('loan_purpose', 'Non spécifié')}
Type de contrat: {application.get('contract_type', 'Non spécifié')}

Historique de crédit:
\"\"\"{main_narrative}\"\"\"

=== NARRATIFS DE CAS SIMILAIRES ===
"""
        for i, case in enumerate(similar_cases[:3], 1):
            p = case['payload']
            narrative_context += f"""
--- Cas {i} (Outcome: {p.get('outcome', 'UNKNOWN')}, Similarité: {case['score']:.2f}) ---
Historique: \"\"\"{p.get('credit_history', 'Non disponible')[:300]}...\"\"\"
"""

    elif application_type == "startup":
        main_narrative = application.get('pitch_narrative', 'Aucun pitch fourni.')
        
        narrative_context = f"""
=== NARRATIF DU DEMANDEUR (Startup) ===
Secteur: {application.get('sector', 'Non spécifié')}
VC Backing: {'Oui' if application.get('vc_backing') else 'Non'}

Pitch:
\"\"\"{main_narrative}\"\"\"

=== PITCHS DE CAS SIMILAIRES ===
"""
        for i, case in enumerate(similar_cases[:3], 1):
            p = case['payload']
            narrative_context += f"""
--- Cas {i} (Outcome: {p.get('outcome', 'UNKNOWN')}, Similarité: {case['score']:.2f}) ---
Secteur: {p.get('sector', 'Unknown')}
Pitch: \"\"\"{p.get('pitch_narrative', 'Non disponible')[:300]}...\"\"\"
"""

    else:  # enterprise
        risk_section = application.get('annual_report_risk_section', 'Aucun rapport de risque fourni.')
        ceo_resume = application.get('ceo_resume_summary', 'Non disponible')
        
        narrative_context = f"""
=== NARRATIF DU DEMANDEUR (Entreprise) ===
Industrie: {application.get('industry_code', 'Non spécifié')}
CEO: {application.get('ceo_name', 'Non spécifié')}
Track Record CEO: {application.get('ceo_track_record', 'Non spécifié')}

Résumé CEO:
\"\"\"{ceo_resume}\"\"\"

Section Risques du Rapport Annuel:
\"\"\"{risk_section}\"\"\"

=== NARRATIFS DE CAS SIMILAIRES ===
"""
        for i, case in enumerate(similar_cases[:3], 1):
            p = case['payload']
            ceo = p.get('ceo_profile', {})
            narrative_context += f"""
--- Cas {i} (Outcome: {p.get('outcome', 'UNKNOWN')}, Similarité: {case['score']:.2f}) ---
CEO Track Record: {ceo.get('track_record', 'Unknown')}
Risques: \"\"\"{p.get('annual_report_risk_section', 'Non disponible')[:300]}...\"\"\"
"""

    llm = get_llm()
    messages = [
        SystemMessage(content=NARRATIVE_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse ces éléments narratifs:\n{narrative_context}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": f"Narrative Agent - {application_type.capitalize()}", "tags": ["narrative", application_type]}
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
            "risk_level": "MEDIUM",
            "confidence": 0.5,
            "key_findings": ["Analyse narrative en cours"],
            "red_flags": [],
            "positive_signals": [],
            "recommendation": "Analyse manuelle recommandée"
        }
    
    cited_cases = []
    for case in similar_cases[:3]:
        cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={"sentiment": result.get('sentiment', 'neutral')},
            summary=f"Cas avec narratif analysé (outcome: {case['payload'].get('outcome', 'UNKNOWN')})"
        ))
    
    return AgentAnalysis(
        agent_name="Narrative Analysis Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('red_flags', []),
        positive_signals=result.get('positive_signals', []),
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )


def analyze(application_type: str, application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Main entry point for narrative analysis."""
    return analyze_narratives(application_type, application, similar_cases)
