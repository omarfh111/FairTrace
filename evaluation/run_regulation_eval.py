"""
Regulation Agent Evaluation Runner

Evaluates the regulation RAG system using:
1. Retrieval metrics (Recall@K, MRR)
2. LLM-as-Judge for answer quality (using Llama 3.1 8B via Ollama)

The LLM judge evaluates:
- Faithfulness: Answer is grounded in retrieved context
- Relevance: Answer addresses the question
- Completeness: Answer covers all aspects of the question
- Citation accuracy: Citations match the content

Usage:
    python evaluation/run_regulation_eval.py
    python evaluation/run_regulation_eval.py --limit 20
    python evaluation/run_regulation_eval.py --retrieval-only   # Skip LLM judge
    python evaluation/run_regulation_eval.py --rerank           # Enable reranking
    python evaluation/run_regulation_eval.py --output results.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Paths
EVAL_DIR = Path(__file__).parent
DATASET_FILE = EVAL_DIR / "regulation_golden_qa.json"
RESULTS_DIR = EVAL_DIR / "metrics"
RESULTS_DIR.mkdir(exist_ok=True)

# LLM Judge model (≤8B, runs locally via Ollama)
JUDGE_MODEL = "qwen2.5:7b"  # Llama 3.1 8B - excellent for evaluation tasks


# =============================================================================
# LLM JUDGE PROMPTS
# =============================================================================
JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for a banking regulation RAG system.

Your task is to evaluate an AI-generated answer against a ground truth answer.

Evaluate on these dimensions (1-5 scale):

1. **FAITHFULNESS** (1-5): Is the generated answer grounded in the retrieved context? No hallucinations?
2. **RELEVANCE** (1-5): Does the answer address the question directly?
3. **COMPLETENESS** (1-5): Does the answer cover all key points from the ground truth?
4. **CITATION_ACCURACY** (1-5): Are page/article citations correct and present?

Respond in JSON format:
{
    "faithfulness": {"score": 1-5, "reason": "brief explanation"},
    "relevance": {"score": 1-5, "reason": "brief explanation"},
    "completeness": {"score": 1-5, "reason": "brief explanation"},
    "citation_accuracy": {"score": 1-5, "reason": "brief explanation"},
    "overall_score": 1-5,
    "verdict": "PASS|PARTIAL|FAIL"
}

Scoring guide:
- 5: Excellent, matches or exceeds ground truth
- 4: Good, minor omissions
- 3: Acceptable, some important details missing
- 2: Poor, significant issues
- 1: Unacceptable, wrong or hallucinated"""


def judge_answer_with_llm(
    question: str,
    ground_truth: str,
    generated_answer: str,
    retrieved_context: str,
    model: str = JUDGE_MODEL
) -> dict:
    """
    Use local Ollama LLM to judge answer quality.
    
    Args:
        question: The original question
        ground_truth: The expected answer
        generated_answer: The RAG system's answer
        retrieved_context: The context retrieved by the system
        model: Ollama model name
    
    Returns:
        Evaluation scores dict
    """
    import ollama
    
    user_prompt = f"""# Question
{question}

# Ground Truth Answer
{ground_truth}

# Generated Answer (to evaluate)
{generated_answer}

# Retrieved Context (used to generate answer)
{retrieved_context[:3000]}

Evaluate the generated answer against the ground truth. Respond in JSON."""

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            format="json",
            options={"temperature": 0.0}  # Deterministic evaluation
        )
        
        return json.loads(response["message"]["content"])
        
    except Exception as e:
        print(f"⚠️ Judge error: {e}")
        return {
            "error": str(e),
            "overall_score": 0,
            "verdict": "ERROR"
        }


# =============================================================================
# RETRIEVAL METRICS
# =============================================================================
def calculate_recall_at_k(
    expected_pages: list[int],
    retrieved_pages: list[int],
    k: int
) -> float:
    """
    Calculate Recall@K - what fraction of expected pages are in top K retrieved.
    """
    if not expected_pages:
        return 1.0  # No expected pages = trivially satisfied
    
    top_k = set(retrieved_pages[:k])
    expected = set(expected_pages)
    
    hits = len(expected.intersection(top_k))
    return hits / len(expected)


def calculate_mrr(
    expected_pages: list[int],
    retrieved_pages: list[int]
) -> float:
    """
    Calculate Mean Reciprocal Rank - position of first relevant result.
    """
    if not expected_pages:
        return 1.0
    
    expected = set(expected_pages)
    
    for i, page in enumerate(retrieved_pages):
        if page in expected:
            return 1.0 / (i + 1)
    
    return 0.0  # No match found


# =============================================================================
# RAG SYSTEM INTERFACE
# =============================================================================
def run_rag_query(question: str, rerank: bool = False) -> dict:
    """
    Run a query through the regulation agent and get response + retrieval info.
    
    Args:
        question: The question to ask
        rerank: If True, use mxbai reranker for two-stage retrieval
    
    Returns:
        {
            "answer": str,
            "retrieved_pages": list[int],
            "retrieved_context": str,
            "latency_ms": int
        }
    """
    from agents.regulation_agent import get_regulation_agent
    
    agent = get_regulation_agent()
    
    start = time.time()
    
    # Get evidence (retrieval) with optional reranking
    evidence, queries_tried, attempts = agent.search_with_retry(question, rerank=rerank)
    
    # Extract retrieved pages
    retrieved_pages = []
    context_parts = []
    for e in evidence:
        page = e.get("payload", {}).get("page_number")
        if page:
            retrieved_pages.append(page)
        content = e.get("payload", {}).get("content", "")
        context_parts.append(content)
    
    # Generate answer
    response = agent.analyze(question, evidence, retrieval_attempts=attempts)
    
    latency_ms = int((time.time() - start) * 1000)
    
    return {
        "answer": response.get("answer", ""),
        "retrieved_pages": retrieved_pages,
        "retrieved_context": "\n---\n".join(context_parts),
        "latency_ms": latency_ms,
        "retrieval_attempts": attempts,
        "confidence": response.get("confidence", "UNKNOWN"),
        "reranked": rerank,
    }


# =============================================================================
# EVALUATION RUNNER
# =============================================================================
def run_evaluation(
    dataset_path: Path = DATASET_FILE,
    limit: int | None = None,
    retrieval_only: bool = False,
    rerank: bool = False,
    output_path: Path | None = None
) -> dict:
    """
    Run full evaluation on the dataset.
    
    Args:
        dataset_path: Path to the evaluation dataset JSON
        limit: Optional limit on number of queries
        retrieval_only: If True, skip LLM judge evaluation
        rerank: If True, use mxbai reranker for two-stage retrieval
        output_path: Optional output file path
    
    Returns:
        Aggregated metrics dict
    """
    # Load dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    if limit:
        dataset = dataset[:limit]
    
    print(f"📊 Evaluating {len(dataset)} Q&A pairs...")
    
    # Results storage
    results = []
    
    # Aggregate metrics
    recall_at_5_scores = []
    recall_at_10_scores = []
    mrr_scores = []
    judge_scores = []
    latencies = []
    
    # Per query-type metrics
    by_type = {}
    
    for i, qa in enumerate(dataset):
        question = qa["question"]
        ground_truth = qa["answer"]
        expected_pages = [c.get("page") for c in qa.get("citations", []) if c.get("page")]
        query_type = qa.get("query_type", "unknown")
        difficulty = qa.get("difficulty", "unknown")
        
        print(f"\n[{i+1}/{len(dataset)}] {query_type} | {difficulty}")
        print(f"   Q: {question[:80]}...")
        
        # Run RAG query
        rag_result = run_rag_query(question, rerank=rerank)
        
        # Calculate retrieval metrics
        retrieved_pages = rag_result["retrieved_pages"]
        
        r_at_5 = calculate_recall_at_k(expected_pages, retrieved_pages, k=5)
        r_at_10 = calculate_recall_at_k(expected_pages, retrieved_pages, k=10)
        mrr = calculate_mrr(expected_pages, retrieved_pages)
        
        recall_at_5_scores.append(r_at_5)
        recall_at_10_scores.append(r_at_10)
        mrr_scores.append(mrr)
        latencies.append(rag_result["latency_ms"])
        
        print(f"   Recall@5: {r_at_5:.2f} | Recall@10: {r_at_10:.2f} | MRR: {mrr:.2f}")
        
        # LLM Judge evaluation (unless retrieval-only)
        judge_result = {}
        if not retrieval_only:
            judge_result = judge_answer_with_llm(
                question=question,
                ground_truth=ground_truth,
                generated_answer=rag_result["answer"],
                retrieved_context=rag_result["retrieved_context"]
            )
            
            overall = judge_result.get("overall_score", 0)
            verdict = judge_result.get("verdict", "?")
            judge_scores.append(overall)
            
            print(f"   Judge: {overall}/5 ({verdict})")
        
        # Store result
        result = {
            "question": question,
            "query_type": query_type,
            "difficulty": difficulty,
            "expected_pages": expected_pages,
            "retrieved_pages": retrieved_pages,
            "recall_at_5": r_at_5,
            "recall_at_10": r_at_10,
            "mrr": mrr,
            "latency_ms": rag_result["latency_ms"],
            "rag_confidence": rag_result["confidence"],
            "ground_truth": ground_truth,
            "generated_answer": rag_result["answer"],
            "judge": judge_result
        }
        results.append(result)
        
        # Track by type
        if query_type not in by_type:
            by_type[query_type] = {"recall_at_5": [], "recall_at_10": [], "mrr": [], "judge": []}
        by_type[query_type]["recall_at_5"].append(r_at_5)
        by_type[query_type]["recall_at_10"].append(r_at_10)
        by_type[query_type]["mrr"].append(mrr)
        if judge_result.get("overall_score"):
            by_type[query_type]["judge"].append(judge_result["overall_score"])
    
    # Aggregate metrics
    def safe_mean(lst):
        return sum(lst) / len(lst) if lst else 0.0
    
    metrics = {
        "total_queries": len(dataset),
        "overall": {
            "recall_at_5": safe_mean(recall_at_5_scores),
            "recall_at_10": safe_mean(recall_at_10_scores),
            "mrr": safe_mean(mrr_scores),
            "avg_latency_ms": safe_mean(latencies),
        },
        "by_query_type": {
            qtype: {
                "count": len(data["recall_at_5"]),
                "recall_at_5": safe_mean(data["recall_at_5"]),
                "recall_at_10": safe_mean(data["recall_at_10"]),
                "mrr": safe_mean(data["mrr"]),
            }
            for qtype, data in by_type.items()
        },
        "results": results
    }
    
    if not retrieval_only and judge_scores:
        metrics["overall"]["judge_score"] = safe_mean(judge_scores)
        metrics["overall"]["pass_rate"] = len([r for r in results if r.get("judge", {}).get("verdict") == "PASS"]) / len(results)
        
        for qtype, data in by_type.items():
            if data["judge"]:
                metrics["by_query_type"][qtype]["judge_score"] = safe_mean(data["judge"])
    
    # Save results
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rerank_suffix = "_rerank" if rerank else ""
        output_path = RESULTS_DIR / f"regulation_eval_{timestamp}{rerank_suffix}.json"
    
    # Add rerank flag to metrics
    metrics["rerank_enabled"] = rerank
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Results saved to {output_path}")
    
    return metrics


def print_summary(metrics: dict):
    """Print a formatted summary of evaluation results."""
    print("\n" + "=" * 60)
    print("REGULATION AGENT EVALUATION SUMMARY")
    print("=" * 60)
    
    overall = metrics["overall"]
    
    print(f"\n📊 Overall Metrics ({metrics['total_queries']} queries)")
    print(f"   Recall@5:  {overall['recall_at_5']:.3f}")
    print(f"   Recall@10: {overall['recall_at_10']:.3f}")
    print(f"   MRR:       {overall['mrr']:.3f}")
    print(f"   Avg Latency: {overall['avg_latency_ms']:.0f}ms")
    
    if "judge_score" in overall:
        print(f"\n🧑‍⚖️ LLM Judge (Llama 3.1 8B)")
        print(f"   Avg Score: {overall['judge_score']:.2f}/5")
        print(f"   Pass Rate: {overall['pass_rate']:.1%}")
    
    print("\n📈 By Query Type:")
    for qtype, data in metrics["by_query_type"].items():
        judge_str = f" | Judge: {data['judge_score']:.1f}/5" if "judge_score" in data else ""
        print(f"   {qtype} (n={data['count']}): R@5={data['recall_at_5']:.2f} | MRR={data['mrr']:.2f}{judge_str}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if overall["mrr"] < 0.5:
        print("   ⚠️ Low MRR indicates relevant docs not appearing in top results")
        print("      → Consider GraphRAG for structural queries")
    
    if overall["recall_at_5"] < 0.6:
        print("   ⚠️ Low Recall@5 means missing expected documents")
        print("      → Review chunking strategy or increase retrieval limit")
    
    # Check per-type performance
    for qtype, data in metrics["by_query_type"].items():
        if data["mrr"] < 0.3:
            print(f"   ⚠️ '{qtype}' queries underperforming (MRR={data['mrr']:.2f})")
            if qtype in ["cross_reference", "multi_hop"]:
                print(f"      → This type would benefit most from GraphRAG")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Run regulation agent evaluation")
    parser.add_argument("--dataset", type=str, default=str(DATASET_FILE), help="Path to evaluation dataset")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries to evaluate")
    parser.add_argument("--retrieval-only", action="store_true", help="Skip LLM judge evaluation")
    parser.add_argument("--rerank", action="store_true", help="Enable mxbai reranker for two-stage retrieval")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    output_path = Path(args.output) if args.output else None
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        print("Run: python evaluation/generate_regulation_eval.py first")
        return
    
    print("=" * 60)
    print("Regulation Agent Evaluation")
    print("=" * 60)
    print(f"📁 Dataset: {dataset_path}")
    print(f"🤖 Judge Model: {JUDGE_MODEL}")
    print(f"📊 Mode: {'Retrieval Only' if args.retrieval_only else 'Full (Retrieval + LLM Judge)'}")
    print(f"🔀 Rerank: {'Enabled (mxbai-rerank)' if args.rerank else 'Disabled'}")
    
    # Run evaluation
    metrics = run_evaluation(
        dataset_path=dataset_path,
        limit=args.limit,
        retrieval_only=args.retrieval_only,
        rerank=args.rerank,
        output_path=output_path
    )
    
    # Print summary
    print_summary(metrics)


if __name__ == "__main__":
    main()
