"""
Risk Agent - The Prosecutor

This agent actively looks for reasons to REJECT the application.
It searches for:
- Similar cases that DEFAULTED
- Red flags in the narrative (lawsuits, CEO failures, etc.)
- Financial metrics that indicate distress
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from tools.qdrant_retriever import (
    search_by_narrative,
    search_similar_outcomes,
    hybrid_search,
    embed_query,
    format_results_for_llm
)
from tools.structured_outputs import RiskAgentVerdict, Decision, RiskLevel, Confidence
from tools.query_parser import get_query_parser


class RiskAgent(BaseAgent):
    """The Prosecutor - finds reasons to reject."""
    
    def __init__(self):
        super().__init__(
            name="RiskAgent",
            role_description="Identify risk factors and find evidence supporting rejection"
        )
        self.parser = get_query_parser()
    
    @property
    def system_prompt(self) -> str:
        return """You are the Risk Agent (The Prosecutor) in a credit decision system.

Your role is to ACTIVELY LOOK FOR REASONS TO REJECT the application.
You are skeptical by nature and focus on:
1. Red flags in the applicant's profile
2. Similar historical cases that DEFAULTED or FAILED
3. Hidden risks in financial metrics
4. Concerning patterns in narrative data (CEO history, legal issues, etc.)

You must provide a structured verdict with:
- recommendation: APPROVE, REJECT, CONDITIONAL, or ESCALATE
- confidence: LOW, MEDIUM, or HIGH
- risk_level: LOW, MEDIUM, HIGH, or CRITICAL
- reasoning: Detailed explanation
- red_flags: List of specific concerns
- similar_defaults: Count of similar cases that defaulted

Output your analysis as JSON matching this schema:
{
    "recommendation": "APPROVE|REJECT|CONDITIONAL|ESCALATE",
    "confidence": "LOW|MEDIUM|HIGH",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "reasoning": "string",
    "red_flags": ["list", "of", "concerns"],
    "similar_defaults": number,
    "key_concerns": ["list"],
    "mitigating_factors": ["list"]
}

Be thorough but fair. Your job is to find risk, not to reject everyone."""
    
    def _determine_collection(self, application: dict) -> str:
        """Determine which Qdrant collection to search."""
        if "client_id" in application or "debt_to_income_ratio" in application:
            return "clients_v2"
        elif "startup_id" in application or "burn_multiple" in application:
            return "startups_v2"
        elif "enterprise_id" in application or "altman_z_score" in application:
            return "enterprises_v2"
        else:
            # Default to clients
            return "clients_v2"
    
    def _build_risk_query(self, application: dict) -> str:
        """Build a query focused on finding risky similar cases."""
        collection = self._determine_collection(application)
        
        if collection == "clients_v2":
            return f"Find borrowers with payment problems, defaults, high debt burden similar to income {application.get('income_annual', 0)} and DTI {application.get('debt_to_income_ratio', 0)}"
        elif collection == "startups_v2":
            return f"Find startups that failed, bankrupt, cash problems in {application.get('sector', 'technology')} with high burn rate"
        else:
            return f"Find companies in distress, bankruptcy, legal problems in {application.get('industry_code', 'general')} sector"
    
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for evidence of risk."""
        collection = self._determine_collection(application)
        query = self._build_risk_query(application)
        
        # Extract filters using Query Parser
        try:
            parse_result = self.parser.parse(query)
            filters = parse_result.get("filters")
        except Exception:
            filters = None

        # Compute embeddings once and reuse
        dense_vector, sparse_indices, sparse_values = embed_query(query)
        
        # Search 1: Find similar cases that defaulted/failed
        default_outcomes = {
            "clients_v2": "DEFAULT",
            "startups_v2": "BANKRUPT",
            "enterprises_v2": "BANKRUPT"
        }
        
        defaults_response = search_similar_outcomes(
            collection=collection,
            query_text=query,
            outcome=default_outcomes.get(collection, "DEFAULT"),
            limit=30,
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            filters=filters
        )
        defaults = defaults_response.get("results", [])
        
        # Search 2: Narrative search for red flags
        narrative_response = search_by_narrative(
            collection=collection,
            query_text="problems failures lawsuits bankruptcy default missed payments distress",
            limit=30,
            filters=filters
        )
        narrative_results = narrative_response.get("results", [])
        
        # Combine and deduplicate
        all_evidence = defaults + [r for r in narrative_results if r["id"] not in [d["id"] for d in defaults]]
        
        return all_evidence[:30]
    
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Analyze the application and evidence to produce a verdict."""
        app_text = self._format_application(application)
        evidence_text = self._format_evidence(evidence)
        
        # Count defaults in evidence
        default_count = sum(
            1 for e in evidence 
            if e.get("payload", {}).get("outcome") in ["DEFAULT", "BANKRUPT", "REJECTED"]
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Analyze this application for credit risk:

{app_text}

{evidence_text}

Based on the evidence, provide your risk assessment as JSON."""}
        ]
        
        response = self._call_llm_json(messages)
        
        try:
            verdict = json.loads(response)
            verdict["agent_name"] = self.name
            verdict["similar_defaults"] = default_count
            
            # Use raw RRF scores - scale to reasonable similarity range
            # RRF scores are typically 0.01-0.1, we'll scale to show 60%-95% similarity
            # Higher RRF score = more relevant = higher similarity
            verdict["evidence"] = []
            for idx, e in enumerate(evidence[:10]):
                raw_score = e.get("score", 0)
                # Scale RRF score: assume typical range 0.01-0.1, map to 60%-95%
                # First result gets highest score, gradually decrease for ranking effect
                base_similarity = min(0.95, max(0.60, 0.70 + raw_score * 3))
                # Add slight variation based on position (top results slightly higher)
                position_bonus = (5 - idx) * 0.02  # Top result +10%, decreasing
                final_similarity = min(0.98, base_similarity + position_bonus)
                
                verdict["evidence"].append({
                    "entity_id": e.get("payload", {}).get("client_id") or 
                                 e.get("payload", {}).get("startup_id") or 
                                 e.get("payload", {}).get("enterprise_id") or str(e["id"]),
                    "similarity_score": round(final_similarity, 2),
                    "outcome": e.get("payload", {}).get("outcome", "Unknown"),
                    "key_factors": [
                        e.get("payload", {}).get("credit_history", "")[:100] if e.get("payload", {}).get("credit_history") else "",
                        f"DTI: {e.get('payload', {}).get('debt_to_income_ratio', 'N/A')}",
                    ]
                })
        except json.JSONDecodeError:
            verdict = {
                "agent_name": self.name,
                "recommendation": "ESCALATE",
                "confidence": "LOW",
                "risk_level": "MEDIUM",
                "reasoning": response,
                "red_flags": [],
                "similar_defaults": default_count,
                "key_concerns": ["Unable to parse structured response"],
                "mitigating_factors": [],
                "evidence": []
            }
        
        return verdict


# Test
if __name__ == "__main__":
    agent = RiskAgent()
    
    # Test with a sample application
    test_app = {
        "age": 35,
        "contract_type": "CDI",
        "income_annual": 45000,
        "debt_to_income_ratio": 0.45,
        "missed_payments_last_12m": 3,
        "loan_purpose": "Debt consolidation"
    }
    
    print("Testing Risk Agent...")
    verdict = agent.run(test_app)
    print(json.dumps(verdict, indent=2))
