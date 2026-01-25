"""
Comparator Agent - The Analyst

This on-demand agent performs detailed gap analysis by comparing the
current application against successful cases. It provides:
- Side-by-side metric comparisons
- Specific gaps that need to be closed
- Percentile rankings vs. approved cases
- Visual gap indicators

The agent is called AFTER the initial decision to show exactly
where the application falls short compared to successful peers.
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


class ComparatorAgent(BaseAgent):
    """The Analyst - compares application against successful cases."""
    
    def __init__(self):
        super().__init__(
            name="ComparatorAgent",
            role_description="Compare application against successful cases and identify gaps"
        )
    
    @property
    def system_prompt(self) -> str:
        return """You are the Comparator Agent (The Analyst) in a credit decision system.

Your role is to perform DETAILED GAP ANALYSIS by comparing the current application
against similar SUCCESSFUL cases. You focus on:
1. Identifying specific metrics where the application falls short
2. Quantifying the gaps (e.g., "DTI is 15% higher than approved average")
3. Ranking the application against approved peers (percentiles)
4. Highlighting both weaknesses AND strengths relative to successful cases

You must provide a structured response with:
- overall_gap_score: 0-100 score where 0=matches approved, 100=far from approved
- metric_comparisons: Detailed comparison for each key metric
- strengths: Where the application meets or exceeds approved averages
- gaps: Where the application falls short
- percentile_ranking: Where this application ranks vs. approved cases
- closest_approved_case: The most similar approved case for reference

Output your analysis as JSON matching this schema:
{
    "overall_gap_score": number (0-100),
    "metric_comparisons": [
        {
            "metric_name": "string",
            "applicant_value": "string or number",
            "approved_average": "string or number",
            "approved_range": {"min": number, "max": number},
            "gap_percentage": number (negative is better, positive is worse),
            "status": "ABOVE_AVERAGE|AT_AVERAGE|BELOW_AVERAGE|CRITICAL_GAP"
        }
    ],
    "strengths": [
        {
            "metric": "string",
            "description": "string",
            "advantage_percentage": number
        }
    ],
    "gaps": [
        {
            "metric": "string",
            "description": "string",
            "gap_severity": "MINOR|MODERATE|SIGNIFICANT|CRITICAL",
            "target_value": "string - what value would be competitive"
        }
    ],
    "percentile_ranking": {
        "overall": number (0-100, where 100 is best),
        "by_metric": {"metric_name": number}
    },
    "closest_approved_case": {
        "entity_id": "string",
        "similarity_score": number,
        "key_differences": ["string"]
    },
    "executive_summary": "string - 2-3 sentence summary",
    "confidence": "LOW|MEDIUM|HIGH"
}

Be precise and quantitative. Use actual numbers from the data."""

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

    def _get_key_metrics(self, application: dict, collection: str) -> list[str]:
        """Get key metrics to compare based on entity type."""
        if collection == "clients_v2":
            return ["income_annual", "debt_to_income_ratio", "missed_payments_last_12m", 
                    "credit_score_internal", "age", "employment_years"]
        elif collection == "startups_v2":
            return ["arr_current", "arr_growth_yoy", "burn_rate_monthly", 
                    "runway_months", "burn_multiple", "team_size"]
        else:
            return ["revenue_annual", "altman_z_score", "legal_lawsuits_active",
                    "ceo_prior_bankruptcies", "years_in_business"]

    @traceable(name="ComparatorAgent.search_evidence", run_type="retriever")
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for approved cases to compare against."""
        collection = self._determine_collection(application)
        
        # Build query for similar approved cases
        if collection == "clients_v2":
            query = f"approved borrower income {application.get('income_annual', 0)} good credit history low debt"
        elif collection == "startups_v2":
            sector = application.get('sector', 'technology')
            query = f"funded successful startup {sector} healthy metrics good runway"
        else:
            industry = application.get('industry_code', 'general')
            query = f"approved enterprise {industry} strong financials good Z-score"
        
        dense_vector, sparse_indices, sparse_values = embed_query(query)
        
        # Get approved cases
        approved_outcomes = {
            "clients_v2": "APPROVED",
            "startups_v2": "FUNDED",
            "enterprises_v2": "APPROVED"
        }
        
        approved_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=approved_outcomes.get(collection, "APPROVED"),
            limit=15,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )
        
        return approved_response.get("results", [])

    @traceable(name="ComparatorAgent.analyze", run_type="chain")
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Perform gap analysis comparing application to approved cases."""
        collection = self._determine_collection(application)
        key_metrics = self._get_key_metrics(application, collection)
        
        app_text = self._format_application(application)
        comparison_text = self._format_comparison_data(application, evidence, key_metrics)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Perform a gap analysis comparing this application to approved cases:

CURRENT APPLICATION:
{app_text}

APPROVED CASES FOR COMPARISON (n={len(evidence)}):
{comparison_text}

KEY METRICS TO COMPARE:
{', '.join(key_metrics)}

Analyze the gaps and provide detailed metric-by-metric comparison as JSON."""}
        ]
        
        config = RunnableConfig(run_name="ComparatorAgent_gap_analysis")
        response = self._call_llm_json_with_config(messages, config)
        
        try:
            result = json.loads(response)
            result["agent_name"] = self.name
            result["approved_cases_analyzed"] = len(evidence)
        except json.JSONDecodeError:
            result = {
                "agent_name": self.name,
                "overall_gap_score": 50,
                "metric_comparisons": [],
                "strengths": [],
                "gaps": [],
                "percentile_ranking": {"overall": 50, "by_metric": {}},
                "closest_approved_case": None,
                "executive_summary": response,
                "confidence": "LOW",
                "approved_cases_analyzed": len(evidence)
            }
        
        return result
    
    def _format_comparison_data(self, application: dict, evidence: list[dict], 
                                 key_metrics: list[str]) -> str:
        """Format approved cases for comparison with statistics."""
        if not evidence:
            return "No approved cases found for comparison."
        
        lines = []
        
        # Calculate statistics for each metric
        metric_stats = {}
        for metric in key_metrics:
            values = []
            for e in evidence:
                payload = e.get("payload", {})
                if metric in payload and payload[metric] is not None:
                    try:
                        values.append(float(payload[metric]))
                    except (ValueError, TypeError):
                        pass
            
            if values:
                metric_stats[metric] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values)
                }
        
        # Format statistics
        lines.append("=== APPROVED CASES STATISTICS ===")
        for metric, stats in metric_stats.items():
            app_value = application.get(metric, "N/A")
            lines.append(f"\n{metric}:")
            lines.append(f"  Applicant: {app_value}")
            lines.append(f"  Approved Avg: {stats['avg']:.2f}")
            lines.append(f"  Approved Range: {stats['min']:.2f} - {stats['max']:.2f}")
            lines.append(f"  Sample Size: {stats['count']}")
        
        # Show top 5 closest approved cases
        lines.append("\n=== CLOSEST APPROVED CASES ===")
        for i, e in enumerate(evidence[:5], 1):
            payload = e.get("payload", {})
            score = e.get("score", 0)
            
            entity_id = (payload.get("client_id") or 
                        payload.get("startup_id") or 
                        payload.get("enterprise_id") or str(e.get("id")))
            
            lines.append(f"\n{i}. Entity {entity_id} (Similarity: {score:.2f})")
            for metric in key_metrics[:4]:
                if metric in payload:
                    lines.append(f"   {metric}: {payload[metric]}")
        
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

    @traceable(name="ComparatorAgent.run", run_type="chain")
    def run(self, application: dict) -> dict:
        """
        Perform gap analysis for an application.
        
        Args:
            application: The application data to compare
        """
        evidence = self.search_evidence(application)
        return self.analyze(application, evidence)


# Test
if __name__ == "__main__":
    agent = ComparatorAgent()
    
    test_app = {
        "age": 32,
        "contract_type": "CDI",
        "income_annual": 38000,
        "debt_to_income_ratio": 0.48,
        "missed_payments_last_12m": 1,
        "credit_score_internal": 620
    }
    
    print("Testing Comparator Agent...")
    result = agent.run(test_app)
    print(json.dumps(result, indent=2, default=str))
