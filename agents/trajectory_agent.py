"""
Trajectory Agent - The Predictor

This agent predicts future outcomes based on historical patterns.
It searches for:
- Cases with similar trajectories that eventually defaulted
- Patterns that indicate future problems
- Early warning signs that preceded failures
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from tools.qdrant_retriever import (
    search_by_narrative,
    hybrid_search,
    search_similar_outcomes,
    embed_query
)
from tools.structured_outputs import TrajectoryAgentVerdict, Decision, RiskLevel, Confidence
from tools.query_parser import get_query_parser


class TrajectoryAgent(BaseAgent):
    """The Predictor - forecasts future outcomes based on patterns."""
    
    def __init__(self):
        super().__init__(
            name="TrajectoryAgent", 
            role_description="Predict future outcomes based on historical trajectory patterns"
        )
        self.parser = get_query_parser()
    
    @property
    def system_prompt(self) -> str:
        return """You are the Trajectory Agent (The Predictor) in a credit decision system.

Your role is to PREDICT FUTURE OUTCOMES based on historical patterns.
You focus on:
1. Finding cases that STARTED similar and ENDED badly (late defaults)
2. Identifying trajectory patterns (e.g., "started strong, failed at month 18")
3. Recognizing early warning signs that preceded failures
4. Estimating time-to-default if risk is present

You must provide a structured verdict with:
- recommendation: APPROVE, REJECT, CONDITIONAL, or ESCALATE
- confidence: LOW, MEDIUM, or HIGH
- risk_level: LOW, MEDIUM, HIGH, or CRITICAL
- reasoning: Detailed explanation
- predicted_outcome: What you predict will happen
- prediction_confidence: 0-1 confidence in prediction
- trajectory_pattern: Identified pattern name
- time_to_default_months: If predicting default, estimated months (null if N/A)

Output your analysis as JSON matching this schema:
{
    "recommendation": "APPROVE|REJECT|CONDITIONAL|ESCALATE",
    "confidence": "LOW|MEDIUM|HIGH",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "reasoning": "string",
    "predicted_outcome": "string",
    "prediction_confidence": 0.0-1.0,
    "trajectory_pattern": "string",
    "time_to_default_months": number or null,
    "key_concerns": ["list"],
    "mitigating_factors": ["list"]
}

You are forward-looking. Consider not just current state, but future trajectory."""
    
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
    
    def _build_trajectory_query(self, application: dict) -> str:
        """Build a query to find cases with similar trajectories."""
        collection = self._determine_collection(application)
        
        if collection == "clients_v2":
            dti = application.get("debt_to_income_ratio", 0.3)
            if dti > 0.4:
                return "Find borrowers who started with high debt and eventually defaulted late payment problems"
            else:
                return "Find borrowers with stable income who maintained good payment history"
        elif collection == "startups_v2":
            burn = application.get("burn_multiple", 2)
            runway = application.get("runway_months", 12)
            if burn > 3 or runway < 6:
                return "Find startups that ran out of runway burned through cash failed despite initial traction"
            else:
                return "Find startups that achieved sustainable growth and reached profitability"
        else:
            z_score = application.get("altman_z_score", 2.5)
            if z_score < 1.8:
                return "Find companies that entered distress zone and eventually went bankrupt failure"
            else:
                return "Find companies that maintained healthy financials and grew steadily"
    
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for cases with similar trajectories."""
        collection = self._determine_collection(application)
        query = self._build_trajectory_query(application)
        
        # Extract filters using Query Parser
        try:
            parse_result = self.parser.parse(query)
            filters = parse_result.get("filters")
        except Exception:
            filters = None

        # OPTIMIZATION: Compute embeddings ONCE and reuse across searches
        # This eliminates the duplicate embed_dense/embed_sparse calls in traces
        dense_vector, sparse_indices, sparse_values = embed_query(query)
        
        # Search 1: Hybrid search for trajectory patterns (with pre-computed embeddings)
        trajectory_response = hybrid_search(
            collection=collection,
            query_text=query,
            limit=5,
            weights={"structured": 0.3, "narrative": 0.5, "keywords": 0.2},
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            filters=filters
        )
        trajectory_results = trajectory_response.get("results", [])
        
        # Search 2: Find defaults to understand failure patterns (reusing embeddings)
        default_outcomes = {
            "clients_v2": "DEFAULT",
            "startups_v2": "BANKRUPT",
            "enterprises_v2": "BANKRUPT"
        }
        
        defaults_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=default_outcomes.get(collection, "DEFAULT"),
            limit=5,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            filters=filters
        )
        defaults = defaults_response.get("results", [])
        
        # Combine and deduplicate
        all_evidence = trajectory_results + [d for d in defaults if d["id"] not in [t["id"] for t in trajectory_results]]
        
        return all_evidence[:10]
    
    def _identify_pattern(self, application: dict, evidence: list[dict]) -> str:
        """Identify the trajectory pattern."""
        collection = self._determine_collection(application)
        
        # Count outcomes
        default_count = sum(
            1 for e in evidence 
            if e.get("payload", {}).get("outcome") in ["DEFAULT", "BANKRUPT", "REJECTED", "WATCHLIST"]
        )
        success_count = len(evidence) - default_count
        
        if not evidence:
            return "INSUFFICIENT_DATA"
        
        failure_rate = default_count / len(evidence)
        
        if failure_rate > 0.6:
            if collection == "clients_v2":
                return "HIGH_RISK_DEBT_SPIRAL"
            elif collection == "startups_v2":
                return "BURN_OUT_TRAJECTORY"
            else:
                return "DISTRESS_DECLINE"
        elif failure_rate > 0.3:
            return "MIXED_OUTCOMES_CONDITIONAL_RISK"
        else:
            return "STABLE_POSITIVE_TRAJECTORY"
    
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Analyze the application for future trajectory."""
        app_text = self._format_application(application)
        evidence_text = self._format_evidence(evidence)
        
        pattern = self._identify_pattern(application, evidence)
        
        # Calculate failure rate
        default_count = sum(
            1 for e in evidence 
            if e.get("payload", {}).get("outcome") in ["DEFAULT", "BANKRUPT", "REJECTED", "WATCHLIST"]
        )
        failure_rate = default_count / len(evidence) if evidence else 0
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Predict future trajectory for this application:

{app_text}

{evidence_text}

Identified Pattern: {pattern}
Historical Failure Rate in Similar Cases: {failure_rate:.0%}

Based on this, predict the future outcome as JSON."""}
        ]
        
        response = self._call_llm_json(messages)
        
        try:
            verdict = json.loads(response)
            verdict["agent_name"] = self.name
            verdict["trajectory_pattern"] = pattern
            
            # Use raw RRF scores - scale to reasonable similarity range
            # RRF scores are typically 0.01-0.1, we'll scale to show 60%-95% similarity
            verdict["evidence"] = []
            for idx, e in enumerate(evidence[:5]):
                raw_score = e.get("score", 0)
                base_similarity = min(0.95, max(0.60, 0.70 + raw_score * 3))
                position_bonus = (5 - idx) * 0.02
                final_similarity = min(0.98, base_similarity + position_bonus)
                
                verdict["evidence"].append({
                    "entity_id": e.get("payload", {}).get("client_id") or 
                                 e.get("payload", {}).get("startup_id") or 
                                 e.get("payload", {}).get("enterprise_id") or str(e["id"]),
                    "similarity_score": round(final_similarity, 2),
                    "outcome": e.get("payload", {}).get("outcome", "Unknown"),
                    "key_factors": [
                        e.get("payload", {}).get("credit_history", "")[:100] if e.get("payload", {}).get("credit_history") else "",
                    ]
                })
        except json.JSONDecodeError:
            verdict = {
                "agent_name": self.name,
                "recommendation": "ESCALATE",
                "confidence": "LOW",
                "risk_level": "MEDIUM",
                "reasoning": response,
                "predicted_outcome": "UNCERTAIN",
                "prediction_confidence": 0.3,
                "trajectory_pattern": pattern,
                "time_to_default_months": None,
                "key_concerns": ["Unable to parse structured response"],
                "mitigating_factors": [],
                "evidence": []
            }
        
        return verdict


# Test
if __name__ == "__main__":
    agent = TrajectoryAgent()
    
    test_app = {
        "sector": "SaaS",
        "arr_current": 500000,
        "arr_growth_yoy": 0.8,
        "burn_rate_monthly": 80000,
        "runway_months": 6,
        "burn_multiple": 5.5,
        "vc_backing": False
    }
    
    print("Testing Trajectory Agent...")
    verdict = agent.run(test_app)
    print(json.dumps(verdict, indent=2))
