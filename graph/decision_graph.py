"""
Decision Graph - LangGraph Workflow for Credit Decisioning

This implements the multi-agent debate as a state machine:
1. Initialize with application
2. Run Risk Agent, Fairness Agent, Trajectory Agent IN PARALLEL
3. Orchestrator synthesizes final decision

Uses async execution for true parallelism.
"""

import json
import sys
import asyncio
from datetime import datetime
from typing import TypedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

from agents.risk_agent import RiskAgent
from agents.fairness_agent import FairnessAgent
from agents.trajectory_agent import TrajectoryAgent


# =============================================================================
# STATE DEFINITION
# =============================================================================
class CreditDecisionState(TypedDict):
    """State that flows through the decision graph."""
    # Input
    application: dict
    application_type: str  # "client", "startup", "enterprise"
    
    # Agent verdicts
    risk_verdict: dict | None
    fairness_verdict: dict | None
    trajectory_verdict: dict | None
    
    # Final decision
    final_decision: dict | None
    
    # Metadata
    decision_id: str
    start_time: str
    end_time: str | None
    error: str | None


# =============================================================================
# AGENT NODES (Async-compatible)
# =============================================================================
async def risk_node(state: CreditDecisionState) -> dict:
    """Run the Risk Agent (async wrapper for CPU-bound work)."""
    try:
        # Run in thread pool to not block event loop
        def run_agent():
            agent = RiskAgent()
            return agent.run(state["application"])
        
        verdict = await asyncio.to_thread(run_agent)
        return {"risk_verdict": verdict}
    except Exception as e:
        return {"risk_verdict": {"error": str(e), "recommendation": "ESCALATE"}}


async def fairness_node(state: CreditDecisionState) -> dict:
    """Run the Fairness Agent (async wrapper for CPU-bound work)."""
    try:
        def run_agent():
            agent = FairnessAgent()
            return agent.run(state["application"])
        
        verdict = await asyncio.to_thread(run_agent)
        return {"fairness_verdict": verdict}
    except Exception as e:
        return {"fairness_verdict": {"error": str(e), "recommendation": "ESCALATE"}}


async def trajectory_node(state: CreditDecisionState) -> dict:
    """Run the Trajectory Agent (async wrapper for CPU-bound work)."""
    try:
        def run_agent():
            agent = TrajectoryAgent()
            return agent.run(state["application"])
        
        verdict = await asyncio.to_thread(run_agent)
        return {"trajectory_verdict": verdict}
    except Exception as e:
        return {"trajectory_verdict": {"error": str(e), "recommendation": "ESCALATE"}}


async def orchestrator_node(state: CreditDecisionState) -> dict:
    """Synthesize final decision from agent verdicts."""
    from agents.base_agent import llm_json
    from langchain_core.messages import SystemMessage, HumanMessage
    import uuid
    
    # Get verdicts
    risk = state.get("risk_verdict", {})
    fairness = state.get("fairness_verdict", {})
    trajectory = state.get("trajectory_verdict", {})
    
    # Format for LLM
    system_prompt = """You are the Final Decision Maker. Synthesize verdicts from three agents:
- Risk Agent: Finds reasons to reject
- Fairness Agent: Ensures consistency
- Trajectory Agent: Predicts future outcomes

Make a final decision: APPROVE, REJECT, CONDITIONAL, or ESCALATE.
Provide reasoning that references all three agents.

Output as JSON:
{
    "decision": "APPROVE|REJECT|CONDITIONAL|ESCALATE",
    "confidence": "LOW|MEDIUM|HIGH",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "reasoning": "string",
    "key_factors": ["list"],
    "conditions": []
}"""
    
    verdicts_summary = f"""
RISK AGENT:
- Recommendation: {risk.get('recommendation', 'N/A')}
- Risk Level: {risk.get('risk_level', 'N/A')}
- Red Flags: {risk.get('red_flags', [])}
- Reasoning: {risk.get('reasoning', 'N/A')[:500]}

FAIRNESS AGENT:
- Recommendation: {fairness.get('recommendation', 'N/A')}
- Similar Approved: {fairness.get('similar_approved', 0)}
- Consistency Score: {fairness.get('consistency_score', 0)}
- Reasoning: {fairness.get('reasoning', 'N/A')[:500]}

TRAJECTORY AGENT:
- Recommendation: {trajectory.get('recommendation', 'N/A')}
- Predicted Outcome: {trajectory.get('predicted_outcome', 'N/A')}
- Pattern: {trajectory.get('trajectory_pattern', 'N/A')}
- Reasoning: {trajectory.get('reasoning', 'N/A')[:500]}
"""
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Application: {json.dumps(state['application'])}\n\n{verdicts_summary}\n\nMake final decision as JSON.")
        ]
        config = RunnableConfig(run_name="Orchestrator_final_decision")
        
        # Run LLM call in thread to not block
        def call_llm():
            return llm_json.invoke(messages, config=config)
        
        response = await asyncio.to_thread(call_llm)
        final = json.loads(response.content)
    except Exception as e:
        final = {
            "decision": "ESCALATE",
            "confidence": "LOW",
            "risk_level": "MEDIUM",
            "reasoning": f"Error in synthesis: {str(e)}",
            "key_factors": [],
            "conditions": []
        }
    
    # Enrich
    final["decision_id"] = state.get("decision_id", f"DEC-{uuid.uuid4().hex[:8].upper()}")
    final["agent_verdicts"] = {
        "risk": {"recommendation": risk.get("recommendation"), "risk_level": risk.get("risk_level")},
        "fairness": {"recommendation": fairness.get("recommendation"), "similar_approved": fairness.get("similar_approved")},
        "trajectory": {"recommendation": trajectory.get("recommendation"), "predicted_outcome": trajectory.get("predicted_outcome")}
    }
    
    return {
        "final_decision": final,
        "end_time": datetime.now().isoformat()
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================
def build_decision_graph() -> StateGraph:
    """Build the LangGraph decision workflow with parallel agent execution."""
    
    # Create graph
    workflow = StateGraph(CreditDecisionState)
    
    # Add nodes (now async)
    workflow.add_node("risk_agent", risk_node)
    workflow.add_node("fairness_agent", fairness_node)
    workflow.add_node("trajectory_agent", trajectory_node)
    workflow.add_node("orchestrator", orchestrator_node)
    
    # Add edges - all 3 agents start from START (parallel execution!)
    workflow.add_edge(START, "risk_agent")
    workflow.add_edge(START, "fairness_agent")
    workflow.add_edge(START, "trajectory_agent")
    
    # All agents feed into orchestrator
    workflow.add_edge("risk_agent", "orchestrator")
    workflow.add_edge("fairness_agent", "orchestrator")
    workflow.add_edge("trajectory_agent", "orchestrator")
    
    # Orchestrator is the end
    workflow.add_edge("orchestrator", END)
    
    return workflow.compile()


# =============================================================================
# ENTRY POINTS
# =============================================================================
async def run_credit_decision_async(application: dict) -> dict:
    """
    Run the full credit decision pipeline ASYNCHRONOUSLY.
    
    This is the preferred method for true parallel execution.
    
    Args:
        application: The loan/credit application data
        
    Returns:
        Full decision with all agent verdicts and final recommendation
    """
    import uuid
    
    # Initialize state
    initial_state = CreditDecisionState(
        application=application,
        application_type=_detect_type(application),
        risk_verdict=None,
        fairness_verdict=None,
        trajectory_verdict=None,
        final_decision=None,
        decision_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
        start_time=datetime.now().isoformat(),
        end_time=None,
        error=None
    )
    
    # Build and run graph
    graph = build_decision_graph()
    
    # Use RunnableConfig for LangSmith tracing
    config = RunnableConfig(
        run_name="FairTrace_Credit_Decision",
        tags=["credit_decision", "multi_agent", "async"]
    )
    
    # ASYNC INVOKE - agents run in parallel!
    result = await graph.ainvoke(initial_state, config=config)
    
    return result


def run_credit_decision(application: dict) -> dict:
    """
    Run the full credit decision pipeline (sync wrapper).
    
    For backward compatibility. Prefers async version internally.
    
    Args:
        application: The loan/credit application data
        
    Returns:
        Full decision with all agent verdicts and final recommendation
    """
    try:
        # Try to use existing event loop
        loop = asyncio.get_running_loop()
        # If we're already in an async context, use nest_asyncio pattern
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(run_credit_decision_async(application))
    except RuntimeError:
        # No running loop, safe to create one
        return asyncio.run(run_credit_decision_async(application))


def _detect_type(application: dict) -> str:
    """Detect application type from fields."""
    if "debt_to_income_ratio" in application or "contract_type" in application:
        return "client"
    elif "burn_multiple" in application or "arr_current" in application:
        return "startup"
    elif "altman_z_score" in application or "industry_code" in application:
        return "enterprise"
    return "unknown"


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    async def test():
        print("Testing Decision Graph (Async)...")
        print("=" * 60)
        
        test_app = {
            "age": 35,
            "contract_type": "CDI",
            "income_annual": 45000,
            "debt_to_income_ratio": 0.42,
            "missed_payments_last_12m": 2,
            "loan_purpose": "Debt consolidation"
        }
        
        start = datetime.now()
        result = await run_credit_decision_async(test_app)
        elapsed = (datetime.now() - start).total_seconds()
        
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(f"Decision: {result.get('final_decision', {}).get('decision', 'N/A')}")
        print(f"Confidence: {result.get('final_decision', {}).get('confidence', 'N/A')}")
        print(f"Risk Level: {result.get('final_decision', {}).get('risk_level', 'N/A')}")
        print(f"\nReasoning: {result.get('final_decision', {}).get('reasoning', 'N/A')}")
        print(f"\n⏱️ Total Time: {elapsed:.2f}s (should be ~10s with parallelism)")
    
    asyncio.run(test())

