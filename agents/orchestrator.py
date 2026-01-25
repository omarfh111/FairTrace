"""
Orchestrator - Final Decision Synthesizer

This agent synthesizes verdicts from all three specialized agents
(Risk, Fairness, Trajectory) into a final credit decision.

Decision Logic:
1. Unanimous REJECT → REJECT (highest risk signal)
2. Unanimous APPROVE → APPROVE
3. Mixed verdicts → CONDITIONAL or ESCALATE based on risk levels
4. Any CRITICAL risk → ESCALATE to human review
"""

import json
import os
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

load_dotenv()

LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.2  # Even lower temperature for final decisions


class Orchestrator:
    """Synthesizes agent verdicts into a final decision."""
    
    def __init__(self):
        self.name = "Orchestrator"
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY"),
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    
    @property
    def system_prompt(self) -> str:
        return """You are the Orchestrator in a multi-agent credit decision system.

You receive verdicts from three specialized agents:
1. Risk Agent (The Prosecutor) - Finds reasons to reject
2. Fairness Agent (The Advocate) - Ensures equitable treatment
3. Trajectory Agent (The Predictor) - Predicts future outcomes

Your job is to SYNTHESIZE these perspectives into a FINAL DECISION.

Decision Rules:
- If ANY agent flags CRITICAL risk → ESCALATE to human review
- If all agents recommend REJECT → REJECT
- If all agents recommend APPROVE → APPROVE
- If agents disagree → Weigh by confidence levels and risk severity
- When in doubt → CONDITIONAL (with clear conditions)

You must provide a final decision with:
- recommendation: APPROVE, REJECT, CONDITIONAL, or ESCALATE
- confidence: LOW, MEDIUM, or HIGH
- risk_level: Overall risk level
- reasoning: Clear explanation of how you synthesized the verdicts
- conditions: List of conditions if CONDITIONAL
- agent_agreement: Did agents agree or disagree?

Output as JSON:
{
    "recommendation": "APPROVE|REJECT|CONDITIONAL|ESCALATE",
    "confidence": "LOW|MEDIUM|HIGH",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "reasoning": "string",
    "conditions": ["list of conditions if applicable"],
    "agent_agreement": "UNANIMOUS|MAJORITY|SPLIT",
    "key_factors": ["most important factors"],
    "dissenting_views": ["any disagreements between agents"]
}"""
    
    def synthesize(
        self,
        application: dict,
        risk_verdict: dict,
        fairness_verdict: dict,
        trajectory_verdict: dict
    ) -> dict:
        """Synthesize agent verdicts into final decision."""
        
        # Format verdicts for LLM
        verdicts_text = f"""
RISK AGENT VERDICT:
- Recommendation: {risk_verdict.get('recommendation', 'N/A')}
- Confidence: {risk_verdict.get('confidence', 'N/A')}
- Risk Level: {risk_verdict.get('risk_level', 'N/A')}
- Key Concerns: {', '.join(risk_verdict.get('key_concerns', []))}
- Reasoning: {risk_verdict.get('reasoning', 'N/A')}

FAIRNESS AGENT VERDICT:
- Recommendation: {fairness_verdict.get('recommendation', 'N/A')}
- Confidence: {fairness_verdict.get('confidence', 'N/A')}
- Risk Level: {fairness_verdict.get('risk_level', 'N/A')}
- Positive Signals: {', '.join(fairness_verdict.get('positive_signals', fairness_verdict.get('mitigating_factors', [])))}
- Reasoning: {fairness_verdict.get('reasoning', 'N/A')}

TRAJECTORY AGENT VERDICT:
- Recommendation: {trajectory_verdict.get('recommendation', 'N/A')}
- Confidence: {trajectory_verdict.get('confidence', 'N/A')}
- Risk Level: {trajectory_verdict.get('risk_level', 'N/A')}
- Predicted Outcome: {trajectory_verdict.get('predicted_outcome', 'N/A')}
- Trajectory Pattern: {trajectory_verdict.get('trajectory_pattern', 'N/A')}
- Reasoning: {trajectory_verdict.get('reasoning', 'N/A')}
"""
        
        # Format application
        app_text = "APPLICATION:\n" + "\n".join(
            f"  {k}: {v}" for k, v in application.items() if not isinstance(v, dict)
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Synthesize these agent verdicts into a final credit decision:

{app_text}

{verdicts_text}

Provide your final decision as JSON."""}
        ]
        
        # Call LLM
        langchain_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"])
        ]
        config = RunnableConfig(run_name="Orchestrator_final_decision")
        response = self.llm.invoke(langchain_messages, config=config)
        
        try:
            decision = json.loads(response.content)
            decision["orchestrator"] = self.name
            decision["timestamp"] = datetime.utcnow().isoformat()
            
            # Add agent verdicts summary
            decision["agent_verdicts"] = {
                "risk": {
                    "recommendation": risk_verdict.get("recommendation"),
                    "risk_level": risk_verdict.get("risk_level")
                },
                "fairness": {
                    "recommendation": fairness_verdict.get("recommendation"),
                    "risk_level": fairness_verdict.get("risk_level")
                },
                "trajectory": {
                    "recommendation": trajectory_verdict.get("recommendation"),
                    "risk_level": trajectory_verdict.get("risk_level")
                }
            }
            
        except json.JSONDecodeError:
            decision = {
                "orchestrator": self.name,
                "recommendation": "ESCALATE",
                "confidence": "LOW",
                "risk_level": "MEDIUM",
                "reasoning": f"Unable to parse structured response: {response.content}",
                "conditions": [],
                "agent_agreement": "UNKNOWN",
                "key_factors": ["Parsing error"],
                "dissenting_views": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return decision


# Test
if __name__ == "__main__":
    orchestrator = Orchestrator()
    
    # Mock verdicts
    risk_verdict = {
        "recommendation": "REJECT",
        "confidence": "HIGH",
        "risk_level": "CRITICAL",
        "reasoning": "High burn rate with limited runway indicates severe default risk",
        "key_concerns": ["Burn multiple > 5x", "Only 6 months runway"]
    }
    
    fairness_verdict = {
        "recommendation": "CONDITIONAL",
        "confidence": "MEDIUM",
        "risk_level": "MEDIUM",
        "reasoning": "Similar startups have been approved with VC backing",
        "mitigating_factors": ["Strong ARR growth", "Experienced team"]
    }
    
    trajectory_verdict = {
        "recommendation": "REJECT",
        "confidence": "HIGH",
        "risk_level": "HIGH",
        "reasoning": "Pattern indicates burnout trajectory",
        "predicted_outcome": "BANKRUPT",
        "trajectory_pattern": "BURN_OUT_TRAJECTORY"
    }
    
    test_app = {
        "sector": "SaaS",
        "arr_current": 500000,
        "burn_multiple": 5.5,
        "runway_months": 6
    }
    
    print("Testing Orchestrator...")
    decision = orchestrator.synthesize(
        test_app, risk_verdict, fairness_verdict, trajectory_verdict
    )
    print(json.dumps(decision, indent=2))
