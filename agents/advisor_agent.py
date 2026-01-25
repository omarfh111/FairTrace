"""
Advisor Agent - The Counselor

This on-demand agent suggests actionable improvements to increase
the chances of application approval. It analyzes:
- Current weak points in the application
- Similar approved cases and their characteristics
- Specific, actionable recommendations for improvement

The agent is called AFTER the initial decision is made, to provide
guidance on how to improve a CONDITIONAL or REJECTED application.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from tools.qdrant_retriever import (
    search_by_narrative,
    search_similar_outcomes,
    hybrid_search,
    embed_query,
)


class AdvisorAgent(BaseAgent):
    """The Counselor - provides actionable improvement recommendations."""
    
    def __init__(self):
        super().__init__(
            name="AdvisorAgent",
            role_description="Suggest actionable improvements to increase approval chances"
        )
    
    @property
    def system_prompt(self) -> str:
        return """You are the Advisor Agent (The Counselor) in a credit decision system.

Your role is to provide ACTIONABLE, SPECIFIC recommendations to improve an application's chances of approval.
You focus on:
1. Identifying the weakest aspects of the current application
2. Finding similar APPROVED cases and analyzing what made them successful
3. Providing concrete, achievable improvement suggestions
4. Prioritizing recommendations by impact and feasibility

You must provide a structured response with:
- improvement_areas: List of areas that need improvement (ranked by priority)
- recommendations: Specific, actionable steps the applicant can take
- timeline: Estimated timeline for each recommendation
- expected_impact: How each change might affect the decision
- similar_approved: Key characteristics of similar approved cases
- confidence: Your confidence in these recommendations

Output your analysis as JSON matching this schema:
{
    "improvement_areas": [
        {
            "area": "string",
            "current_state": "string",
            "target_state": "string",
            "priority": "HIGH|MEDIUM|LOW"
        }
    ],
    "recommendations": [
        {
            "action": "string - specific actionable step",
            "rationale": "string - why this helps",
            "timeline": "string - realistic timeframe",
            "expected_impact": "HIGH|MEDIUM|LOW",
            "difficulty": "EASY|MODERATE|HARD"
        }
    ],
    "similar_approved_characteristics": [
        "string - key traits of similar approved cases"
    ],
    "overall_outlook": "PROMISING|CHALLENGING|DIFFICULT",
    "confidence": "LOW|MEDIUM|HIGH"
}

Be encouraging but realistic. Focus on what CAN be improved, not what cannot be changed."""

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
    
    def _build_success_query(self, application: dict) -> str:
        """Build a query to find successful similar cases."""
        collection = self._determine_collection(application)
        
        if collection == "clients_v2":
            income = application.get('income_annual', 0)
            dti = application.get('debt_to_income_ratio', 0)
            return f"Find approved borrowers with similar income around {income} who improved their DTI ratio from {dti} good credit history"
        elif collection == "startups_v2":
            sector = application.get('sector', 'technology')
            return f"Find successful funded startups in {sector} with good burn rate management strong ARR growth"
        else:
            industry = application.get('industry_code', 'general')
            return f"Find approved enterprises in {industry} with strong financials good Z-score clean legal record"

    @traceable(name="AdvisorAgent.search_evidence", run_type="retriever")
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for approved cases to learn from."""
        collection = self._determine_collection(application)
        query = self._build_success_query(application)
        
        # Compute embeddings once
        dense_vector, sparse_indices, sparse_values = embed_query(query)
        
        # Search for approved/funded cases
        approved_outcomes = {
            "clients_v2": "APPROVED",
            "startups_v2": "FUNDED",
            "enterprises_v2": "APPROVED"
        }
        
        approved_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=approved_outcomes.get(collection, "APPROVED"),
            limit=8,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        approved_cases = approved_response.get("results", [])
        
        # Also get some conditional cases - they show edge cases
        conditional_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome="CONDITIONAL",
            limit=3,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        conditional_cases = conditional_response.get("results", [])
        
        return approved_cases + conditional_cases

    @traceable(name="AdvisorAgent.analyze", run_type="chain")
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Generate improvement recommendations based on application and successful cases."""
        app_text = self._format_application(application)
        
        # Format approved cases specially to highlight success factors
        success_text = self._format_success_evidence(evidence)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Analyze this application and provide improvement recommendations:

{app_text}

Here are similar APPROVED/FUNDED cases for reference:
{success_text}

Based on:
1. The applicant's current weaknesses
2. What made similar cases successful
3. Realistic improvement opportunities

Provide specific, actionable recommendations as JSON."""}
        ]
        
        config = RunnableConfig(run_name="AdvisorAgent_recommendations")
        response = self._call_llm_json_with_config(messages, config)
        
        try:
            result = json.loads(response)
            result["agent_name"] = self.name
            result["success_cases_analyzed"] = len([
                e for e in evidence 
                if e.get("payload", {}).get("outcome") in ["APPROVED", "FUNDED"]
            ])
            result["evidence"] = [
                {
                    "entity_id": e.get("payload", {}).get("client_id") or 
                                 e.get("payload", {}).get("startup_id") or 
                                 e.get("payload", {}).get("enterprise_id") or str(e["id"]),
                    "similarity_score": e.get("score", 0),
                    "outcome": e.get("payload", {}).get("outcome", "Unknown")
                }
                for e in evidence[:5]
            ]
        except json.JSONDecodeError:
            result = {
                "agent_name": self.name,
                "improvement_areas": [],
                "recommendations": [{
                    "action": "Unable to generate detailed recommendations",
                    "rationale": response,
                    "timeline": "N/A",
                    "expected_impact": "MEDIUM",
                    "difficulty": "MODERATE"
                }],
                "similar_approved_characteristics": [],
                "overall_outlook": "CHALLENGING",
                "confidence": "LOW",
                "success_cases_analyzed": 0,
                "evidence": []
            }
        
        return result
    
    def _format_success_evidence(self, evidence: list[dict]) -> str:
        """Format approved cases highlighting success factors."""
        if not evidence:
            return "No similar approved cases found."
        
        lines = []
        for i, e in enumerate(evidence[:8], 1):
            payload = e.get("payload", {})
            score = e.get("score", 0)
            outcome = payload.get("outcome", "Unknown")
            
            # Determine entity type
            if "client_id" in payload:
                entity = f"Client {payload['client_id']}"
                key_metrics = f"DTI: {payload.get('debt_to_income_ratio', 0):.1%}, Income: ${payload.get('income_annual', 0):,.0f}"
            elif "startup_id" in payload:
                entity = f"Startup {payload['startup_id']}"
                key_metrics = f"Burn Multiple: {payload.get('burn_multiple', 0):.1f}x, Runway: {payload.get('runway_months', 0):.0f}mo"
            elif "enterprise_id" in payload:
                entity = f"Enterprise {payload['enterprise_id']}"
                key_metrics = f"Z-Score: {payload.get('altman_z_score', 0):.2f}, Lawsuits: {payload.get('legal_lawsuits_active', 0)}"
            else:
                entity = f"Entity {i}"
                key_metrics = "N/A"
            
            lines.append(f"{i}. {entity} ({outcome}, Similarity: {score:.2f})")
            lines.append(f"   Key Metrics: {key_metrics}")
        
        return "\n".join(lines)
    
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

    @traceable(name="AdvisorAgent.run", run_type="chain")
    def run(self, application: dict, original_decision: dict = None) -> dict:
        """
        Generate improvement advice for an application.
        
        Args:
            application: The application data
            original_decision: Optional - the original decision from the main pipeline
        """
        # Add context from original decision if available
        if original_decision:
            application = application.copy()
            application["_original_decision"] = original_decision.get("recommendation", "UNKNOWN")
            application["_original_concerns"] = original_decision.get("key_concerns", [])
        
        evidence = self.search_evidence(application)
        return self.analyze(application, evidence)


# Test
if __name__ == "__main__":
    agent = AdvisorAgent()
    
    test_app = {
        "age": 28,
        "contract_type": "CDD",
        "income_annual": 32000,
        "debt_to_income_ratio": 0.52,
        "missed_payments_last_12m": 2,
        "loan_purpose": "Home improvement"
    }
    
    print("Testing Advisor Agent...")
    result = agent.run(test_app)
    print(json.dumps(result, indent=2))
