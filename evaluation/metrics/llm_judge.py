"""
LLM-as-Judge Module

Uses Qwen2.5:7b via Ollama to evaluate retrieval relevance (fully local).
Instead of checking exact ID matches, the LLM judges if retrieved 
documents are relevant to the query.

Metrics:
- Relevance Score: 0-1 score for each retrieved document
- Average Relevance: Mean relevance at K
- Binary Relevance: % of results above threshold
"""

import os
import json
from typing import Literal

import ollama
from dotenv import load_dotenv

load_dotenv()

# Use Qwen2.5:7b via Ollama (fully local, no API costs)
JUDGE_MODEL = "qwen2.5:7b-instruct-q4_K_M"
JUDGE_TEMPERATURE = 0.0  # Deterministic judgments


def get_judge_llm_response(system_prompt: str, user_message: str) -> str:
    """Call the local Qwen LLM judge via Ollama."""
    response = ollama.chat(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        options={"temperature": JUDGE_TEMPERATURE},
        format="json"  # Force JSON output
    )
    return response["message"]["content"]


RELEVANCE_PROMPT = """You are an expert evaluator for a credit decision retrieval system.

Your task is to judge whether retrieved documents are RELEVANT to the query.

A document is RELEVANT if:
1. It contains information that would help answer the query
2. The entity profile matches the search criteria
3. The document would be useful for making a credit decision related to the query

Score each document from 0 to 1:
- 1.0 = Highly relevant, directly answers the query
- 0.7-0.9 = Relevant, useful for the query
- 0.4-0.6 = Partially relevant, some useful info
- 0.1-0.3 = Marginally relevant
- 0.0 = Not relevant at all

Output JSON:
{
    "scores": [
        {"doc_index": 0, "score": 0.8, "reason": "..."},
        {"doc_index": 1, "score": 0.3, "reason": "..."}
    ],
    "overall_relevance": 0.55
}"""


def format_document_for_judge(doc: dict, index: int) -> str:
    """Format a retrieved document for the LLM judge."""
    payload = doc.get("payload", {})
    score = doc.get("score", 0)
    
    # Determine entity type
    if "client_id" in payload:
        entity_type = "Client"
        entity_id = payload["client_id"]
        key_info = f"""
  - Age: {payload.get('age', 'N/A')}
  - Contract: {payload.get('contract_type', 'N/A')}
  - Income: ${payload.get('income_annual', 0):,.0f}
  - DTI Ratio: {payload.get('debt_to_income_ratio', 0):.1%}
  - Missed Payments: {payload.get('missed_payments_last_12m', 0)}
  - Outcome: {payload.get('outcome', 'N/A')}"""
    elif "startup_id" in payload:
        entity_type = "Startup"
        entity_id = payload["startup_id"]
        key_info = f"""
  - Sector: {payload.get('sector', 'N/A')}
  - ARR: ${payload.get('arr_current', 0):,.0f}
  - Burn Multiple: {payload.get('burn_multiple', 0):.1f}x
  - Runway: {payload.get('runway_months', 0):.0f} months
  - VC Backed: {payload.get('vc_backing', False)}
  - Outcome: {payload.get('outcome', 'N/A')}"""
    elif "enterprise_id" in payload:
        entity_type = "Enterprise"
        entity_id = payload["enterprise_id"]
        key_info = f"""
  - Industry: {payload.get('industry_code', 'N/A')}
  - Z-Score: {payload.get('altman_z_score', 0):.2f}
  - Lawsuits: {payload.get('legal_lawsuits_active', 0)}
  - Outcome: {payload.get('outcome', 'N/A')}"""
    else:
        entity_type = "Unknown"
        entity_id = str(doc.get("id", index))
        key_info = f"  - Payload: {json.dumps(payload)[:200]}"
    
    return f"""[Document {index}] {entity_type} {entity_id} (Similarity: {score:.2f})
{key_info}"""


def judge_relevance(
    query: str,
    retrieved_docs: list[dict],
    max_docs: int = 5
) -> dict:
    """
    Use LLM to judge relevance of retrieved documents.
    
    Args:
        query: The search query
        retrieved_docs: List of retrieved documents from Qdrant
        max_docs: Maximum documents to judge (for cost control)
    
    Returns:
        Dict with scores per document and overall relevance
    """
    if not retrieved_docs:
        return {
            "scores": [],
            "overall_relevance": 0.0,
            "binary_relevance": 0.0,
            "error": None
        }
    
    # Limit docs for cost
    docs_to_judge = retrieved_docs[:max_docs]
    
    # Format documents
    docs_text = "\n\n".join(
        format_document_for_judge(doc, i) 
        for i, doc in enumerate(docs_to_judge)
    )
    
    # Build prompt
    user_message = f"""Query: "{query}"

Retrieved Documents:
{docs_text}

Judge the relevance of each document to the query. Output JSON."""
    
    try:
        response_text = get_judge_llm_response(RELEVANCE_PROMPT, user_message)
        result = json.loads(response_text)
        
        # Calculate binary relevance (% above 0.5 threshold)
        scores = [s["score"] for s in result.get("scores", [])]
        binary_relevance = sum(1 for s in scores if s >= 0.5) / len(scores) if scores else 0.0
        
        return {
            "scores": result.get("scores", []),
            "overall_relevance": result.get("overall_relevance", 0.0),
            "binary_relevance": binary_relevance,
            "error": None
        }
        
    except Exception as e:
        return {
            "scores": [],
            "overall_relevance": 0.0,
            "binary_relevance": 0.0,
            "error": str(e)
        }


def judge_faithfulness(
    query: str,
    retrieved_docs: list[dict],
    agent_reasoning: str
) -> dict:
    """
    Judge if agent reasoning is grounded in the retrieved evidence.
    
    Returns faithfulness score 0-1.
    """
    if not retrieved_docs or not agent_reasoning:
        return {"faithfulness": 0.0, "error": "Missing docs or reasoning"}
    
    # Format evidence
    evidence_text = "\n\n".join(
        format_document_for_judge(doc, i) 
        for i, doc in enumerate(retrieved_docs[:5])
    )
    
    prompt = f"""You are evaluating whether an AI agent's reasoning is FAITHFUL to the evidence.

Faithfulness means:
1. Claims in the reasoning are supported by the retrieved documents
2. No hallucinations or made-up facts
3. Conclusions logically follow from the evidence

Query: "{query}"

Retrieved Evidence:
{evidence_text}

Agent Reasoning:
{agent_reasoning}

Score faithfulness from 0 to 1:
- 1.0 = Completely faithful, all claims grounded in evidence
- 0.7-0.9 = Mostly faithful, minor unsupported claims
- 0.4-0.6 = Partially faithful, some unsupported claims
- 0.0-0.3 = Unfaithful, major hallucinations

Output JSON:
{{"faithfulness": 0.8, "unsupported_claims": ["..."], "well_grounded_claims": ["..."]}}"""
    
    try:
        system_prompt = "You are an expert evaluator for AI reasoning quality."
        response_text = get_judge_llm_response(system_prompt, prompt)
        result = json.loads(response_text)
        return {
            "faithfulness": result.get("faithfulness", 0.0),
            "unsupported_claims": result.get("unsupported_claims", []),
            "well_grounded_claims": result.get("well_grounded_claims", []),
            "error": None
        }
        
    except Exception as e:
        return {"faithfulness": 0.0, "error": str(e)}


class LLMJudgeEvaluator:
    """Aggregates LLM judge scores across multiple test cases."""
    
    def __init__(self):
        self.relevance_results = []
        self.faithfulness_results = []
    
    def add_relevance_result(
        self,
        query: str,
        relevance_result: dict,
        metadata: dict | None = None
    ):
        """Add a relevance evaluation result."""
        self.relevance_results.append({
            "query": query,
            "result": relevance_result,
            "metadata": metadata or {}
        })
    
    def add_faithfulness_result(
        self,
        query: str,
        faithfulness_result: dict,
        metadata: dict | None = None
    ):
        """Add a faithfulness evaluation result."""
        self.faithfulness_results.append({
            "query": query,
            "result": faithfulness_result,
            "metadata": metadata or {}
        })
    
    def compute_metrics(self) -> dict:
        """Compute aggregate metrics."""
        metrics = {}
        
        # Relevance metrics
        if self.relevance_results:
            overall_scores = [
                r["result"]["overall_relevance"] 
                for r in self.relevance_results 
                if r["result"].get("overall_relevance") is not None
            ]
            binary_scores = [
                r["result"]["binary_relevance"] 
                for r in self.relevance_results 
                if r["result"].get("binary_relevance") is not None
            ]
            
            metrics["mean_relevance"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0
            metrics["mean_binary_relevance"] = sum(binary_scores) / len(binary_scores) if binary_scores else 0
            metrics["relevance_cases"] = len(self.relevance_results)
        
        # Faithfulness metrics
        if self.faithfulness_results:
            faith_scores = [
                r["result"]["faithfulness"] 
                for r in self.faithfulness_results 
                if r["result"].get("faithfulness") is not None
            ]
            
            metrics["mean_faithfulness"] = sum(faith_scores) / len(faith_scores) if faith_scores else 0
            metrics["faithfulness_cases"] = len(self.faithfulness_results)
        
        return metrics
