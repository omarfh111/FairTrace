"""
Scenario Agent - The Strategist

This on-demand agent enables interactive what-if modeling, allowing users
to explore different scenarios and their potential outcomes. It provides:
- Impact analysis of changing specific metrics
- Probability estimates for different scenarios
- Recommended changes with expected outcomes
- Sensitivity analysis for key variables

The agent is called AFTER the initial decision to help applicants
understand what changes would most impact their decision.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from tools.qdrant_retriever import (
    search_similar_outcomes,
    embed_query,
)


class ScenarioAgent(BaseAgent):
    """The Strategist - models what-if scenarios and their outcomes."""
    
    def __init__(self):
        super().__init__(
            name="ScenarioAgent",
            role_description="Model what-if scenarios and predict outcome probabilities"
        )
    
    @property
    def system_prompt(self) -> str:
        return """You are the Scenario Agent (The Strategist) in a credit decision system.

Your role is to perform WHAT-IF ANALYSIS, helping applicants understand how
changes to their application would affect the decision. You focus on:
1. Modeling the impact of changing specific metrics
2. Estimating outcome probabilities for different scenarios
3. Identifying the most impactful changes (sensitivity analysis)
4. Providing actionable pathways to approval

You must provide a structured response with:
- current_assessment: Summary of current application likelihood
- scenarios: Multiple what-if scenarios with predictions
- sensitivity_analysis: Which metrics have the most impact
- optimal_path: The most efficient path to approval
- risk_factors: Variables that could derail improvement plans

Output your analysis as JSON matching this schema:
{
    "current_assessment": {
        "approval_probability": number (0-100),
        "current_outcome": "LIKELY_APPROVE|BORDERLINE|LIKELY_REJECT",
        "limiting_factors": ["string"]
    },
    "scenarios": [
        {
            "scenario_name": "string - descriptive name",
            "changes": [
                {
                    "metric": "string",
                    "from_value": "string or number",
                    "to_value": "string or number"
                }
            ],
            "predicted_outcome": "APPROVE|CONDITIONAL|REJECT",
            "new_probability": number (0-100),
            "probability_change": number (positive is improvement),
            "feasibility": "EASY|MODERATE|DIFFICULT|VERY_DIFFICULT",
            "timeframe": "string - estimated time to achieve"
        }
    ],
    "sensitivity_analysis": [
        {
            "metric": "string",
            "impact_score": number (0-100, how much changing this helps),
            "current_value": "string or number",
            "threshold_value": "string - value needed for approval",
            "improvement_needed": "string - description of change needed"
        }
    ],
    "optimal_path": {
        "description": "string - summary of best approach",
        "steps": [
            {
                "step_number": number,
                "action": "string",
                "expected_impact": "string",
                "difficulty": "EASY|MODERATE|HARD"
            }
        ],
        "estimated_timeframe": "string",
        "success_probability": number (0-100)
    },
    "risk_factors": [
        {
            "risk": "string",
            "likelihood": "LOW|MEDIUM|HIGH",
            "potential_impact": "string"
        }
    ],
    "confidence": "LOW|MEDIUM|HIGH"
}

Be realistic about probabilities and timeframes. Base predictions on historical data."""

    def _determine_collection(self, application: dict) -> str:
        """Determine which Qdrant collection to search."""
        if "client_id" in application or "debt_to_income_ratio" in application:
            return "clients_v2"
        elif "startup_id" in application or "burn_multiple" in application:
            return "startups_v2"
        elif "enterprise_id" in application or "altman_z_score" in application:
            return "enterprises_v2"
        else:
            return "clients_v2"

    @traceable(name="ScenarioAgent.search_evidence", run_type="retriever")
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for cases with various outcomes for scenario modeling."""
        collection = self._determine_collection(application)
        
        # Build query similar to the application
        if collection == "clients_v2":
            query = f"borrower income {application.get('income_annual', 0)} credit history debt ratio"
        elif collection == "startups_v2":
            sector = application.get('sector', 'technology')
            query = f"startup {sector} funding journey growth metrics runway"
        else:
            industry = application.get('industry_code', 'general')
            query = f"enterprise {industry} financials credit decision"
        
        dense_vector, sparse_indices, sparse_values = embed_query(query)
        
        # Get mix of outcomes for comparison
        all_evidence = []
        
        # Approved cases
        approved_outcomes = {"clients_v2": "APPROVED", "startups_v2": "FUNDED", "enterprises_v2": "APPROVED"}
        approved_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=approved_outcomes.get(collection, "APPROVED"),
            limit=8,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        all_evidence.extend(approved_response.get("results", []))
        
        # Rejected/failed cases
        rejected_outcomes = {"clients_v2": "REJECTED", "startups_v2": "BANKRUPT", "enterprises_v2": "REJECTED"}
        rejected_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=rejected_outcomes.get(collection, "REJECTED"),
            limit=5,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        all_evidence.extend(rejected_response.get("results", []))
        
        # Conditional cases (edge cases are valuable for scenarios)
        conditional_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome="CONDITIONAL",
            limit=5,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        all_evidence.extend(conditional_response.get("results", []))
        
        return all_evidence

    @traceable(name="ScenarioAgent.analyze", run_type="chain")
    def analyze(self, application: dict, evidence: list[dict], 
                custom_scenarios: list[dict] = None) -> dict:
        """Generate what-if scenario analysis."""
        collection = self._determine_collection(application)
        
        app_text = self._format_application(application)
        evidence_text = self._format_scenario_data(evidence, collection)
        
        # Build custom scenario prompts if provided
        scenario_prompt = ""
        if custom_scenarios:
            scenario_prompt = "\n\nUSER-REQUESTED SCENARIOS TO MODEL:\n"
            for i, scenario in enumerate(custom_scenarios, 1):
                scenario_prompt += f"{i}. {scenario.get('description', 'Custom scenario')}\n"
                for change in scenario.get('changes', []):
                    scenario_prompt += f"   - Change {change.get('metric')}: {change.get('to_value')}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Perform what-if scenario analysis for this application:

CURRENT APPLICATION:
{app_text}

HISTORICAL DATA FOR MODELING (Approved, Rejected, Conditional cases):
{evidence_text}

{scenario_prompt}

Generate realistic scenarios showing:
1. What changes would most likely lead to approval
2. The probability impact of each change
3. The optimal path forward
4. Risks that could prevent improvement

Provide your analysis as JSON."""}
        ]
        
        config = RunnableConfig(run_name="ScenarioAgent_what_if_modeling")
        response = self._call_llm_json_with_config(messages, config)
        
        try:
            result = json.loads(response)
            result["agent_name"] = self.name
            result["cases_modeled"] = len(evidence)
        except json.JSONDecodeError:
            result = {
                "agent_name": self.name,
                "current_assessment": {
                    "approval_probability": 50,
                    "current_outcome": "BORDERLINE",
                    "limiting_factors": ["Analysis parsing error"]
                },
                "scenarios": [],
                "sensitivity_analysis": [],
                "optimal_path": {
                    "description": response,
                    "steps": [],
                    "estimated_timeframe": "Unknown",
                    "success_probability": 50
                },
                "risk_factors": [],
                "confidence": "LOW",
                "cases_modeled": len(evidence)
            }
        
        return result
    
    def _format_scenario_data(self, evidence: list[dict], collection: str) -> str:
        """Format evidence by outcome for scenario modeling."""
        grouped = {"approved": [], "rejected": [], "conditional": [], "other": []}
        
        approved_outcomes = ["APPROVED", "FUNDED", "SUCCESS"]
        rejected_outcomes = ["REJECTED", "DEFAULT", "BANKRUPT", "FAILED"]
        
        for e in evidence:
            outcome = e.get("payload", {}).get("outcome", "").upper()
            if outcome in approved_outcomes:
                grouped["approved"].append(e)
            elif outcome in rejected_outcomes:
                grouped["rejected"].append(e)
            elif outcome == "CONDITIONAL":
                grouped["conditional"].append(e)
            else:
                grouped["other"].append(e)
        
        lines = []
        
        # Format by outcome
        for category, cases in grouped.items():
            if cases:
                lines.append(f"\n=== {category.upper()} CASES ({len(cases)}) ===")
                for e in cases[:3]:
                    lines.append(self._format_case_summary(e, collection))
        
        return "\n".join(lines)
    
    def _format_case_summary(self, evidence: dict, collection: str) -> str:
        """Format a single case for scenario context."""
        payload = evidence.get("payload", {})
        score = evidence.get("score", 0)
        outcome = payload.get("outcome", "Unknown")
        
        entity_id = (payload.get("client_id") or 
                    payload.get("startup_id") or 
                    payload.get("enterprise_id") or "Unknown")
        
        # Get key metrics based on collection
        if collection == "clients_v2":
            metrics = f"Income: ${payload.get('income_annual', 0):,.0f}, DTI: {payload.get('debt_to_income_ratio', 0):.1%}"
        elif collection == "startups_v2":
            metrics = f"Burn: {payload.get('burn_multiple', 0):.1f}x, Runway: {payload.get('runway_months', 0):.0f}mo"
        else:
            metrics = f"Z-Score: {payload.get('altman_z_score', 0):.2f}, Revenue: ${payload.get('revenue_annual', 0):,.0f}"
        
        return f"[{entity_id}] {outcome} - {metrics} (sim: {score:.2f})"
    
    def _call_llm_json_with_config(self, messages: list[dict], config: RunnableConfig) -> str:
        """Call LLM with JSON response format and custom config."""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        langchain_messages = [
            SystemMessage(content=m["content"]) if m["role"] == "system" 
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        response = self.llm_json.invoke(langchain_messages, config=config)
        return response.content

    @traceable(name="ScenarioAgent.run", run_type="chain")
    def run(self, application: dict, custom_scenarios: list[dict] = None) -> dict:
        """
        Perform what-if scenario analysis.
        
        Args:
            application: The application data
            custom_scenarios: Optional list of user-defined scenarios to model
                Example: [{"description": "If I increase income by 20%", 
                          "changes": [{"metric": "income_annual", "to_value": 60000}]}]
        """
        evidence = self.search_evidence(application)
        return self.analyze(application, evidence, custom_scenarios)


# Test
if __name__ == "__main__":
    agent = ScenarioAgent()
    
    test_app = {
        "age": 29,
        "contract_type": "CDD",
        "income_annual": 35000,
        "debt_to_income_ratio": 0.55,
        "missed_payments_last_12m": 2,
        "credit_score_internal": 580
    }
    
    # Test with custom scenario
    custom = [
        {
            "description": "If I pay off existing debt",
            "changes": [{"metric": "debt_to_income_ratio", "to_value": 0.30}]
        }
    ]
    
    print("Testing Scenario Agent...")
    result = agent.run(test_app, custom)
    print(json.dumps(result, indent=2, default=str))
