"""
Narrative Agent - The Storyteller

This on-demand agent extracts and synthesizes stories from historical cases.
It provides:
- Narrative insights from similar cases
- Pattern recognition across historical data
- Human-readable summaries of case histories
- Lessons learned from past decisions

The agent is called AFTER the initial decision to provide deeper context
and storytelling around the retrieved evidence.
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
    hybrid_search,
    embed_query,
)


class NarrativeAgent(BaseAgent):
    """The Storyteller - extracts insights and narratives from historical cases."""
    
    def __init__(self):
        super().__init__(
            name="NarrativeAgent",
            role_description="Extract and synthesize narratives from historical cases"
        )
    
    @property
    def system_prompt(self) -> str:
        return """You are the Narrative Agent (The Storyteller) in a credit decision system.

Your role is to extract MEANINGFUL STORIES and PATTERNS from historical cases to provide
context and insights for credit decisions. You focus on:
1. Finding compelling narratives in similar historical cases
2. Identifying patterns and trends across multiple cases
3. Extracting lessons learned from both successes and failures
4. Presenting information in an engaging, human-readable way

You must provide a structured response with:
- narrative_summary: A compelling overall narrative about similar cases
- key_patterns: Important patterns observed across cases
- success_stories: Brief stories of similar cases that succeeded
- cautionary_tales: Brief stories of similar cases that failed
- industry_context: Relevant industry/sector insights
- lessons_learned: Key takeaways from historical data

Output your analysis as JSON matching this schema:
{
    "narrative_summary": "string - 2-3 paragraph compelling overview",
    "key_patterns": [
        {
            "pattern": "string - the observed pattern",
            "frequency": "COMMON|OCCASIONAL|RARE",
            "significance": "HIGH|MEDIUM|LOW"
        }
    ],
    "success_stories": [
        {
            "title": "string - brief title",
            "summary": "string - 2-3 sentence story",
            "key_factor": "string - what made them succeed"
        }
    ],
    "cautionary_tales": [
        {
            "title": "string - brief title",
            "summary": "string - 2-3 sentence story",
            "key_lesson": "string - what went wrong"
        }
    ],
    "industry_context": "string - broader context about the sector/industry",
    "lessons_learned": ["string - key takeaways"],
    "confidence": "LOW|MEDIUM|HIGH"
}

Be insightful and tell stories that illuminate the decision. Make the data come alive."""

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

    @traceable(name="NarrativeAgent.search_evidence", run_type="retriever")
    def search_evidence(self, application: dict) -> list[dict]:
        """Search for cases with rich narrative potential."""
        collection = self._determine_collection(application)
        
        # Build a broad narrative query
        if collection == "clients_v2":
            query = f"borrower story history financial journey income {application.get('income_annual', 0)} debt payment patterns"
        elif collection == "startups_v2":
            sector = application.get('sector', 'technology')
            query = f"startup {sector} journey growth story funding challenges success failure pivot"
        else:
            industry = application.get('industry_code', 'general')
            query = f"enterprise {industry} company story history growth challenges legal financial"
        
        # Narrative search - prioritizes rich text content
        narrative_response = search_by_narrative(
            collection=collection,
            query_text=query,
            limit=10
        )
        narrative_results = narrative_response.get("results", [])
        
        # Also do a hybrid search to get diverse cases
        hybrid_response = hybrid_search(
            collection=collection,
            query_text=query,
            limit=5
        )
        hybrid_results = hybrid_response.get("results", [])
        
        # Combine and deduplicate
        seen_ids = set()
        all_results = []
        for r in narrative_results + hybrid_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_results.append(r)
        
        return all_results[:12]

    @traceable(name="NarrativeAgent.analyze", run_type="chain")
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Extract narratives and insights from the evidence."""
        app_text = self._format_application(application)
        
        # Group evidence by outcome for narrative building
        grouped = self._group_by_outcome(evidence)
        narrative_text = self._format_narrative_evidence(evidence, grouped)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Extract narratives and insights from these historical cases:

Current Application:
{app_text}

Historical Cases:
{narrative_text}

Summary:
- Total cases analyzed: {len(evidence)}
- Approved/Funded: {len(grouped.get('success', []))}
- Rejected/Failed: {len(grouped.get('failure', []))}
- Conditional/Other: {len(grouped.get('other', []))}

Create a compelling narrative analysis with patterns, stories, and lessons as JSON."""}
        ]
        
        config = RunnableConfig(run_name="NarrativeAgent_storytelling")
        response = self._call_llm_json_with_config(messages, config)
        
        try:
            result = json.loads(response)
            result["agent_name"] = self.name
            result["cases_analyzed"] = len(evidence)
            result["outcome_distribution"] = {
                "success": len(grouped.get('success', [])),
                "failure": len(grouped.get('failure', [])),
                "other": len(grouped.get('other', []))
            }
        except json.JSONDecodeError:
            result = {
                "agent_name": self.name,
                "narrative_summary": response,
                "key_patterns": [],
                "success_stories": [],
                "cautionary_tales": [],
                "industry_context": "Unable to extract industry context.",
                "lessons_learned": ["Analysis parsing failed - raw response preserved in summary"],
                "confidence": "LOW",
                "cases_analyzed": len(evidence),
                "outcome_distribution": {
                    "success": len(grouped.get('success', [])),
                    "failure": len(grouped.get('failure', [])),
                    "other": len(grouped.get('other', []))
                }
            }
        
        return result
    
    def _group_by_outcome(self, evidence: list[dict]) -> dict:
        """Group evidence by outcome category."""
        grouped = {"success": [], "failure": [], "other": []}
        
        success_outcomes = ["APPROVED", "FUNDED", "SUCCESS"]
        failure_outcomes = ["REJECTED", "DEFAULT", "BANKRUPT", "FAILED"]
        
        for e in evidence:
            outcome = e.get("payload", {}).get("outcome", "").upper()
            if outcome in success_outcomes:
                grouped["success"].append(e)
            elif outcome in failure_outcomes:
                grouped["failure"].append(e)
            else:
                grouped["other"].append(e)
        
        return grouped
    
    def _format_narrative_evidence(self, evidence: list[dict], grouped: dict) -> str:
        """Format evidence for narrative extraction."""
        lines = []
        
        # Success cases
        if grouped.get("success"):
            lines.append("=== SUCCESS CASES ===")
            for e in grouped["success"][:4]:
                lines.append(self._format_single_case(e))
                lines.append("")
        
        # Failure cases
        if grouped.get("failure"):
            lines.append("=== FAILURE CASES ===")
            for e in grouped["failure"][:4]:
                lines.append(self._format_single_case(e))
                lines.append("")
        
        # Other cases
        if grouped.get("other"):
            lines.append("=== OTHER CASES ===")
            for e in grouped["other"][:2]:
                lines.append(self._format_single_case(e))
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_single_case(self, evidence: dict) -> str:
        """Format a single case for narrative consumption."""
        payload = evidence.get("payload", {})
        score = evidence.get("score", 0)
        outcome = payload.get("outcome", "Unknown")
        narrative = payload.get("narrative", "No narrative available.")
        
        # Determine entity type and key info
        if "client_id" in payload:
            entity = f"Client {payload['client_id']}"
            details = f"Income: ${payload.get('income_annual', 0):,.0f}, DTI: {payload.get('debt_to_income_ratio', 0):.1%}"
        elif "startup_id" in payload:
            entity = f"Startup {payload['startup_id']}"
            details = f"Sector: {payload.get('sector', 'N/A')}, Burn: {payload.get('burn_multiple', 0):.1f}x"
        elif "enterprise_id" in payload:
            entity = f"Enterprise {payload['enterprise_id']}"
            details = f"Industry: {payload.get('industry_code', 'N/A')}, Z-Score: {payload.get('altman_z_score', 0):.2f}"
        else:
            entity = f"Entity (Similarity: {score:.2f})"
            details = ""
        
        return f"""[{entity}] Outcome: {outcome}
{details}
Narrative: {narrative[:500]}..."""
    
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

    @traceable(name="NarrativeAgent.run", run_type="chain")
    def run(self, application: dict, original_evidence: list[dict] = None) -> dict:
        """
        Generate narrative insights for an application.
        
        Args:
            application: The application data
            original_evidence: Optional - evidence from the main pipeline to augment
        """
        # Search for additional evidence
        evidence = self.search_evidence(application)
        
        # Merge with original evidence if provided
        if original_evidence:
            seen_ids = {e["id"] for e in evidence}
            for e in original_evidence:
                if e.get("id") not in seen_ids:
                    evidence.append(e)
        
        return self.analyze(application, evidence)


# Test
if __name__ == "__main__":
    agent = NarrativeAgent()
    
    test_app = {
        "sector": "FinTech",
        "arr_current": 800000,
        "arr_growth_yoy": 0.65,
        "burn_rate_monthly": 120000,
        "runway_months": 8,
        "burn_multiple": 4.2,
        "vc_backing": True
    }
    
    print("Testing Narrative Agent...")
    result = agent.run(test_app)
    print(json.dumps(result, indent=2, default=str))
