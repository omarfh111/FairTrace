"""
Production-Grade Evaluation Dataset Generator

Generates comprehensive Q&A pairs for evaluating:
1. Retrieval Quality (Recall@K, Precision@K, MRR)
2. Agent Reasoning (Faithfulness, Correctness)
3. End-to-End Decision Quality

Features:
- Diverse query formulations (not just templates)
- Positive AND negative examples
- Multi-hop queries
- Difficulty gradation (easy, medium, hard)
- Agent-specific test cases
"""

import json
import random
from pathlib import Path
from typing import Literal

# Paths
DATA_DIR = Path(__file__).parent.parent / "data_generation" / "output"
EVAL_DIR = Path(__file__).parent
OUTPUT_FILE = EVAL_DIR / "golden_qa.json"


# =============================================================================
# QUERY TEMPLATES (Diverse Formulations)
# =============================================================================
CLIENT_QUERY_TEMPLATES = {
    "high_risk": [
        "Find clients with poor payment history and high default risk",
        "Show me borrowers who have missed multiple payments",
        "Identify high-risk individual loan applicants",
        "Which clients have concerning credit behavior?",
        "Find applicants similar to someone who defaulted"
    ],
    "low_risk": [
        "Find financially stable clients with clean credit history",
        "Show me reliable borrowers with no missed payments",
        "Identify low-risk loan applicants",
        "Which clients have excellent payment records?",
        "Find applicants similar to approved and successful loans"
    ],
    "contract_specific": [
        "Find {contract_type} employees seeking loans",
        "Show me loan applications from {contract_type} workers",
        "Identify borrowers with {contract_type} employment contracts"
    ]
}

STARTUP_QUERY_TEMPLATES = {
    "high_risk": [
        "Find startups with dangerous burn rates",
        "Show me companies burning cash faster than they grow",
        "Identify startups with poor unit economics",
        "Which startups have unsustainable burn multiples?",
        "Find {sector} companies likely to run out of runway"
    ],
    "low_risk": [
        "Find well-funded startups with healthy metrics",
        "Show me VC-backed companies with strong growth",
        "Identify startups with good CAC/LTV ratios",
        "Which startups have sustainable business models?",
        "Find {sector} companies with solid runway"
    ],
    "sector_specific": [
        "Find {sector} startups seeking funding",
        "Show me investment opportunities in {sector}",
        "Identify promising {sector} companies"
    ]
}

ENTERPRISE_QUERY_TEMPLATES = {
    "distress": [
        "Find companies in financial distress",
        "Show me enterprises with bankruptcy risk",
        "Identify companies with poor solvency ratios",
        "Which enterprises have Altman Z-Score in distress zone?",
        "Find {industry} companies at risk of failure"
    ],
    "healthy": [
        "Find financially healthy enterprises",
        "Show me companies with strong balance sheets",
        "Identify enterprises with excellent liquidity",
        "Which companies have safe Altman Z-Scores?",
        "Find {industry} leaders with solid financials"
    ],
    "legal_risk": [
        "Find companies with significant legal exposure",
        "Show me enterprises facing multiple lawsuits",
        "Identify companies with litigation risk",
        "Which enterprises have legal troubles?"
    ],
    "ceo_risk": [
        "Find companies led by CEOs with failed ventures",
        "Show me enterprises with concerning leadership history",
        "Identify companies where CEO has bankruptcy background"
    ]
}

MULTI_HOP_TEMPLATES = [
    "Find {industry} companies in distress zone AND with multiple lawsuits",
    "Show me startups in {sector} with high burn rate AND no VC backing",
    "Identify clients with {contract_type} contract AND multiple missed payments",
    "Find enterprises with low Z-Score AND CEO with failed track record"
]


# =============================================================================
# EVALUATION CASE GENERATOR
# =============================================================================
class EvaluationGenerator:
    def __init__(self):
        self.clients = []
        self.startups = []
        self.enterprises = []
        self.eval_cases = []
    
    def load_data(self):
        """Load generated data."""
        with open(DATA_DIR / "clients.json") as f:
            self.clients = json.load(f)
        with open(DATA_DIR / "startups.json") as f:
            self.startups = json.load(f)
        with open(DATA_DIR / "enterprises.json") as f:
            self.enterprises = json.load(f)
        
        # Filter to test split only
        self.test_clients = [c for c in self.clients if c.get("split") == "test"]
        self.test_startups = [s for s in self.startups if s.get("split") == "test"]
        self.test_enterprises = [e for e in self.enterprises if e.get("split") == "test"]
        
        print(f"Loaded: {len(self.test_clients)} test clients, {len(self.test_startups)} test startups, {len(self.test_enterprises)} test enterprises")
    
    def _create_case(
        self,
        query: str,
        expected_ids: list[str],
        collection: str,
        case_type: Literal["retrieval", "reasoning", "decision", "fairness"],
        difficulty: Literal["easy", "medium", "hard"],
        is_negative: bool = False,
        agent: str | None = None,
        reasoning: str = ""
    ) -> dict:
        """Create a single evaluation case."""
        return {
            "query": query,
            "expected_ids": expected_ids,
            "collection": collection,
            "case_type": case_type,
            "difficulty": difficulty,
            "is_negative": is_negative,  # If True, these IDs should NOT be retrieved
            "agent": agent,  # Which agent this tests (risk, fairness, trajectory, or None for retrieval)
            "reasoning": reasoning
        }
    
    def generate_client_cases(self):
        """Generate evaluation cases for clients."""
        # Define groups
        high_risk_clients = [c for c in self.test_clients if c["missed_payments_last_12m"] >= 3]
        low_risk_clients = [c for c in self.test_clients if c["missed_payments_last_12m"] == 0]
        
        high_risk_ids = [c["client_id"] for c in high_risk_clients]
        low_risk_ids = [c["client_id"] for c in low_risk_clients]
        
        # 1. Broad Category Queries (High Recall expected)
        for template in CLIENT_QUERY_TEMPLATES["high_risk"]:
            self.eval_cases.append(self._create_case(
                query=template,
                expected_ids=high_risk_ids,  # Expect ANY/ALL of these
                collection="clients_v2",
                case_type="retrieval",
                difficulty="easy",
                reasoning="Broad query for high-risk clients (missed payments >= 3)"
            ))
            
        for template in CLIENT_QUERY_TEMPLATES["low_risk"]:
            self.eval_cases.append(self._create_case(
                query=template,
                expected_ids=low_risk_ids,
                collection="clients_v2",
                case_type="retrieval",
                difficulty="easy",
                reasoning="Broad query for low-risk clients (clean history)"
            ))

        # 2. Specific Item Queries (Precision expected)
        # Select a few specific clients to test similarity search
        for client in high_risk_clients[:5]:
            self.eval_cases.append(self._create_case(
                query=f"Assess credit risk for profile similar to {client['client_id']}",
                expected_ids=[client["client_id"]],
                collection="clients_v2",
                case_type="reasoning",
                difficulty="medium",
                agent="risk_agent",
                reasoning=f"Specific retrieval for {client['client_id']}"
            ))

    def generate_startup_cases(self):
        """Generate evaluation cases for startups."""
        # Define groups
        high_risk_startups = [s for s in self.test_startups if s.get("burn_rate_monthly", 0) > 100000 or s.get("burn_multiple", 0) > 5.0]
        sustainable_startups = [s for s in self.test_startups if s.get("burn_rate_monthly", 0) < 50000 and s.get("runway_months", 0) > 18]
        
        high_risk_ids = [s["startup_id"] for s in high_risk_startups]
        sustainable_ids = [s["startup_id"] for s in sustainable_startups]
        
        # Broad Cases
        for template in STARTUP_QUERY_TEMPLATES["high_risk"]:
            if "{sector}" in template:
                sectors = {s.get("sector") for s in high_risk_startups if s.get("sector")}
                for sector in list(sectors)[:3]:
                    sector_ids = [s["startup_id"] for s in high_risk_startups if s.get("sector") == sector]
                    if sector_ids:
                        self.eval_cases.append(self._create_case(
                            query=template.format(sector=sector),
                            expected_ids=sector_ids,
                            collection="startups_v2",
                            case_type="retrieval",
                            difficulty="medium",
                            reasoning=f"High risk startups in {sector}"
                        ))
            else:
                self.eval_cases.append(self._create_case(
                    query=template,
                    expected_ids=high_risk_ids,
                    collection="startups_v2",
                    case_type="retrieval",
                    difficulty="easy",
                    reasoning="Broad query for high burn rate startups"
                ))

        for template in STARTUP_QUERY_TEMPLATES["low_risk"]:
            if "{sector}" in template:
                sectors = {s.get("sector") for s in sustainable_startups if s.get("sector")}
                for sector in list(sectors)[:3]:
                    sector_ids = [s["startup_id"] for s in sustainable_startups if s.get("sector") == sector]
                    if sector_ids:
                         self.eval_cases.append(self._create_case(
                            query=template.format(sector=sector),
                            expected_ids=sector_ids,
                            collection="startups_v2",
                            case_type="retrieval",
                            difficulty="medium",
                            reasoning=f"Sustainable startups in {sector}"
                        ))
            else:
                self.eval_cases.append(self._create_case(
                    query=template,
                    expected_ids=sustainable_ids,
                    collection="startups_v2",
                    case_type="retrieval",
                    difficulty="easy",
                    reasoning="Broad query for sustainable startups"
                ))
    
    def generate_enterprise_cases(self):
        """Generate evaluation cases for enterprises."""
        # Distressed (Z-Score < 1.8)
        distressed_enterprises = [e for e in self.test_enterprises if e.get("altman_z_score", 0) < 1.8]
        healthy_enterprises = [e for e in self.test_enterprises if e.get("altman_z_score", 0) > 3.0]
        legal_risk_enterprises = [e for e in self.test_enterprises if e.get("legal_lawsuits_active", 0) >= 3]
        
        distressed_ids = [e["enterprise_id"] for e in distressed_enterprises]
        healthy_ids = [e["enterprise_id"] for e in healthy_enterprises]
        legal_risk_ids = [e["enterprise_id"] for e in legal_risk_enterprises]
        
        # Broad Cases
        for template in ENTERPRISE_QUERY_TEMPLATES["distress"]:
            if "{industry}" in template:
                industries = {e.get("industry_code") for e in distressed_enterprises if e.get("industry_code")}
                for ind in list(industries)[:3]:
                    ind_ids = [e["enterprise_id"] for e in distressed_enterprises if e.get("industry_code") == ind]
                    if ind_ids:
                        self.eval_cases.append(self._create_case(
                            query=template.format(industry=ind),
                            expected_ids=ind_ids,
                            collection="enterprises_v2",
                            case_type="retrieval",
                            difficulty="medium",
                            reasoning=f"Distressed enterprises in {ind}"
                        ))
            else:
               self.eval_cases.append(self._create_case(
                    query=template,
                    expected_ids=distressed_ids,
                    collection="enterprises_v2",
                    case_type="retrieval",
                    difficulty="easy",
                    reasoning="Broad query for distressed enterprises"
                ))
                
        for template in ENTERPRISE_QUERY_TEMPLATES["healthy"]:
               self.eval_cases.append(self._create_case(
                    query=template.format(industry="General") if "{industry}" in template else template,
                    expected_ids=healthy_ids,
                    collection="enterprises_v2",
                    case_type="retrieval",
                    difficulty="easy",
                    reasoning="Broad query for healthy enterprises"
                ))
                
        for template in ENTERPRISE_QUERY_TEMPLATES["legal_risk"]:
               self.eval_cases.append(self._create_case(
                    query=template,
                    expected_ids=legal_risk_ids,
                    collection="enterprises_v2",
                    case_type="retrieval",
                    difficulty="medium",
                    reasoning="Query for enterprises with legal risk"
                ))
                
    def generate_multi_hop_cases(self):
        """Generate complex multi-condition queries."""
        # Distressed + Legal Risk
        complex_distress = [
            e for e in self.test_enterprises 
            if e.get("altman_z_score", 0) < 1.8 and e.get("legal_lawsuits_active", 0) >= 2
        ]
        complex_distress_ids = [e["enterprise_id"] for e in complex_distress]
        
        if complex_distress_ids:
            query = f"Find companies in financial distress with significant legal exposure"
            self.eval_cases.append(self._create_case(
                query=query,
                expected_ids=complex_distress_ids,
                collection="enterprises_v2",
                case_type="retrieval",
                difficulty="hard",
                reasoning=f"Multi-hop: Low Z-Score AND >2 lawsuits"
            ))
            
        # High burn + No VC (Bootstrapped risk)
        no_vc_burn = [
            s for s in self.test_startups
            if s.get("burn_multiple", 0) > 3.0 and not s.get("vc_backing", False)
        ]
        no_vc_burn_ids = [s["startup_id"] for s in no_vc_burn]
        
        if no_vc_burn_ids:
            query = f"Find bootstrapped startups with cash flow problems"
            self.eval_cases.append(self._create_case(
                query=query,
                expected_ids=no_vc_burn_ids,
                collection="startups_v2",
                case_type="retrieval",
                difficulty="hard",
                reasoning=f"Multi-hop: No VC AND high burn multiple"
            ))
    
    def generate_fairness_cases(self):
        """Generate fairness test cases (same profile → same decision)."""
        # Find pairs of similar clients
        for i, c1 in enumerate(self.test_clients):
            for c2 in self.test_clients[i+1:]:
                # If they have similar DTI and missed payments, outcome should be similar
                dti_diff = abs(c1["debt_to_income_ratio"] - c2["debt_to_income_ratio"])
                payments_diff = abs(c1["missed_payments_last_12m"] - c2["missed_payments_last_12m"])
                
                if dti_diff < 0.05 and payments_diff == 0:
                    self.eval_cases.append(self._create_case(
                        query=f"Compare treatment of {c1['client_id']} vs {c2['client_id']}",
                        expected_ids=[c1["client_id"], c2["client_id"]],
                        collection="clients_v2",
                        case_type="fairness",
                        difficulty="hard",
                        agent="fairness_agent",
                        reasoning=f"Similar profiles (DTI diff: {dti_diff:.2f}, payments diff: {payments_diff}) should get consistent treatment"
                    ))
    
    def generate_all(self):
        """Generate all evaluation cases."""
        self.load_data()
        
        print("\nGenerating evaluation cases...")
        self.generate_client_cases()
        self.generate_startup_cases()
        self.generate_enterprise_cases()
        self.generate_multi_hop_cases()
        self.generate_fairness_cases()
        
        # Summary
        by_type = {}
        by_difficulty = {}
        by_collection = {}
        negative_count = 0
        
        for case in self.eval_cases:
            by_type[case["case_type"]] = by_type.get(case["case_type"], 0) + 1
            by_difficulty[case["difficulty"]] = by_difficulty.get(case["difficulty"], 0) + 1
            by_collection[case["collection"]] = by_collection.get(case["collection"], 0) + 1
            if case["is_negative"]:
                negative_count += 1
        
        print(f"\n✓ Generated {len(self.eval_cases)} evaluation cases")
        print(f"\nBy Type:")
        for t, count in by_type.items():
            print(f"  - {t}: {count}")
        print(f"\nBy Difficulty:")
        for d, count in by_difficulty.items():
            print(f"  - {d}: {count}")
        print(f"\nBy Collection:")
        for c, count in by_collection.items():
            print(f"  - {c}: {count}")
        print(f"\nNegative Examples: {negative_count}")
        
        # Save
        with open(OUTPUT_FILE, "w") as f:
            json.dump(self.eval_cases, f, indent=2)
        print(f"\n✓ Saved to {OUTPUT_FILE}")


def main():
    generator = EvaluationGenerator()
    generator.generate_all()


if __name__ == "__main__":
    main()
