"""
FairTrace Evaluation Runner

Production-grade evaluation pipeline for retrieval quality.

Usage:
    python evaluation/run_evaluation.py [--limit N] [--collection NAME]
    python evaluation/run_evaluation.py --llm-judge --limit 10  # Use LLM to judge relevance

Features:
- Runs retrieval tests against Qdrant
- Calculates Recall@K, Precision@K, MRR, NDCG
- LLM-as-Judge mode for semantic relevance scoring
- Generates JSON report with metrics by difficulty/collection
- Tracks latency per query
"""

import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Literal

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from evaluation.metrics import RetrievalEvaluator, judge_relevance, LLMJudgeEvaluator
from tools.qdrant_retriever import hybrid_search, embed_query

EVAL_DIR = Path(__file__).parent
GOLDEN_FILE = EVAL_DIR / "golden_qa.json"
REPORTS_DIR = EVAL_DIR / "reports"

# Query expansion model (Qwen 3b for speed)
QUERY_EXPAND_MODEL = "qwen2.5:3b-instruct-q8_0"


def expand_query(query: str) -> str:
    """
    Use LLM to expand/rewrite query for better retrieval.
    
    Generates alternative phrasings and related terms.
    """
    import ollama
    
    system_prompt = """You are a query expansion expert for a credit/finance retrieval system.

Given a search query, expand it by adding:
1. Synonyms and alternative phrasings
2. Related financial/credit terms
3. Specific criteria that match the intent

Output ONLY the expanded query, nothing else. Keep it concise (under 200 words)."""

    user_message = f"""Original query: {query}

Expanded query:"""
    
    try:
        response = ollama.chat(
            model=QUERY_EXPAND_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            options={"temperature": 0.3, "num_predict": 200}
        )
        expanded = response["message"]["content"].strip()
        return expanded if expanded else query
    except Exception as e:
        print(f"⚠️ Query expansion failed: {e}")
        return query  # Fall back to original


def load_golden_cases(
    limit: int | None = None,
    case_type: str | None = None,
    collection: str | None = None
) -> list[dict]:
    """Load evaluation cases from golden_qa.json."""
    with open(GOLDEN_FILE) as f:
        cases = json.load(f)
    
    # Filter by case type (retrieval, reasoning, decision, fairness)
    if case_type:
        cases = [c for c in cases if c["case_type"] == case_type]
    
    # Filter by collection
    if collection:
        cases = [c for c in cases if c["collection"] == collection]
    
    # Limit for quick testing
    if limit:
        cases = cases[:limit]
    
    return cases


def run_retrieval_test(
    query: str,
    collection: str,
    expected_ids: list[str],
    is_negative: bool = False,
    limit: int = 10,
    rerank: bool = False,
    use_parser: bool = False
) -> dict:
    """
    Run a single retrieval test.
    
    Returns dict with retrieved_ids, raw docs, latency, and whether expected docs were found.
    """
    filters = None
    if use_parser:
        from tools.query_parser import get_query_parser
        try:
            parser = get_query_parser()
            parse_result = parser.parse(query)
            # Only use if confidence/valid filters found? 
            # The parser returns collection and filters.
            # We should respect the parser's collection choice too if we wanted, 
            # but for this test we stick to the test case collection unless filter is specific.
            # Actually, let's just use the filters.
            filters = parse_result.get("filters")
        except Exception:
            pass # Fallback to standard search

    start = time.time()
    
    try:
        # Run hybrid search
        response = hybrid_search(
            collection=collection,
            query_text=query,
            limit=limit,
            weights={"structured": 0.4, "narrative": 0.4, "keywords": 0.2},
            rerank=rerank,
            rerank_top_k=50 if rerank else None,
            filters=filters
        )
        
        latency_ms = (time.time() - start) * 1000
        
        # Extract IDs and keep raw docs for LLM judge
        retrieved_ids = []
        raw_docs = response.get("results", [])
        
        for result in raw_docs:
            payload = result.get("payload", {})
            entity_id = (
                payload.get("client_id") or 
                payload.get("startup_id") or 
                payload.get("enterprise_id") or 
                str(result.get("id", ""))
            )
            retrieved_ids.append(entity_id)
        
        # Check if expected IDs were found
        expected_set = set(expected_ids)
        retrieved_set = set(retrieved_ids)
        
        if is_negative:
            # For negative cases, success = expected IDs NOT in results
            success = len(expected_set & retrieved_set) == 0
        else:
            # For positive cases, success = at least one expected ID in results
            success = len(expected_set & retrieved_set) > 0
        
        return {
            "success": success,
            "retrieved_ids": retrieved_ids,
            "raw_docs": raw_docs,  # For LLM judge
            "latency_ms": latency_ms,
            "cache_hit": response.get("cache_hit", False),
            "error": None
        }
        
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return {
            "success": False,
            "retrieved_ids": [],
            "raw_docs": [],
            "latency_ms": latency_ms,
            "cache_hit": False,
            "error": str(e)
        }


def run_evaluation(
    cases: list[dict],
    k_values: list[int] = [10, 25, 50],
    rerank: bool = False,
    use_parser: bool = False
) -> dict:
    """
    Run full evaluation pipeline.
    
    Returns comprehensive metrics report.
    """
    evaluator = RetrievalEvaluator()
    
    latencies = []
    errors = []
    cache_hits = 0
    
    mode_str = "🔄 reranking" if rerank else "🔍 standard"
    print(f"\n{mode_str} Running {len(cases)} retrieval tests...\n")
    
    debug_count = 0
    for case in tqdm(cases, desc="Evaluating"):
        result = run_retrieval_test(
            query=case["query"],
            collection=case["collection"],
            expected_ids=case["expected_ids"],
            is_negative=case.get("is_negative", False),
            limit=max(k_values) if k_values else 10,
            rerank=rerank,
            use_parser=use_parser
        )
        
        # Debug: Show first 3 cases
        if debug_count < 3:
            print(f"\n  [DEBUG Case {debug_count + 1}]")
            print(f"    Query: {case['query'][:50]}...")
            print(f"    Expected IDs: {case['expected_ids']}")
            print(f"    Retrieved IDs: {result['retrieved_ids'][:5]}")
            print(f"    Match: {set(case['expected_ids']) & set(result['retrieved_ids'])}")
            debug_count += 1
        
        evaluator.add_result(
            query=case["query"],
            retrieved_ids=result["retrieved_ids"],
            expected_ids=case["expected_ids"],
            is_negative=case.get("is_negative", False),
            metadata={
                "difficulty": case.get("difficulty", "unknown"),
                "collection": case["collection"],
                "case_type": case.get("case_type", "retrieval"),
                "agent": case.get("agent")
            }
        )
        
        latencies.append(result["latency_ms"])
        if result["cache_hit"]:
            cache_hits += 1
        if result["error"]:
            errors.append({"query": case["query"], "error": result["error"]})
    
    # Compute metrics
    overall_metrics = evaluator.compute_metrics(k_values)
    metrics_by_difficulty = evaluator.compute_metrics_by_group("difficulty", k_values)
    metrics_by_collection = evaluator.compute_metrics_by_group("collection", k_values)
    
    # Latency stats
    latency_stats = {
        "p50_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
        "mean_ms": sum(latencies) / len(latencies) if latencies else 0,
        "total_s": sum(latencies) / 1000
    }
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "cache_hit_rate": cache_hits / len(cases) if cases else 0,
        "error_count": len(errors),
        "metrics": {
            "overall": overall_metrics,
            "by_difficulty": metrics_by_difficulty,
            "by_collection": metrics_by_collection
        },
        "latency": latency_stats,
        "errors": errors[:10]  # First 10 errors only
    }
    
    return report


def run_llm_judge_evaluation(
    cases: list[dict],
    max_docs_per_query: int = 5,
    query_expand: bool = False,
    rerank: bool = False
) -> dict:
    """
    Run evaluation using LLM-as-Judge for relevance scoring.
    
    Uses Qwen2.5:7b via Ollama (fully local, no API costs).
    """
    judge_evaluator = LLMJudgeEvaluator()
    
    latencies = []
    llm_latencies = []
    errors = []
    cache_hits = 0
    expand_latencies = []
    
    print(f"\n🤖 Running {len(cases)} LLM-as-Judge evaluations...")
    print(f"   Model: qwen2.5:7b (local via Ollama)")
    if query_expand:
        print(f"   Query Expansion: enabled (qwen2.5:3b)")
    if rerank:
        print(f"   Reranking: enabled (mxbai-rerank-base-v2)")
    print()
    
    for case in tqdm(cases, desc="LLM Judging"):
        # Optional query expansion
        query = case["query"]
        if query_expand:
            expand_start = time.time()
            query = expand_query(query)
            expand_latencies.append((time.time() - expand_start) * 1000)
        
        # Run retrieval
        result = run_retrieval_test(
            query=query,
            collection=case["collection"],
            expected_ids=case["expected_ids"],
            is_negative=case.get("is_negative", False),
            limit=10,
            rerank=rerank
        )
        
        latencies.append(result["latency_ms"])
        if result["cache_hit"]:
            cache_hits += 1
        
        if result["error"]:
            errors.append({"query": case["query"], "error": result["error"]})
            continue
        
        # Run LLM judge
        llm_start = time.time()
        relevance_result = judge_relevance(
            query=case["query"],
            retrieved_docs=result["raw_docs"],
            max_docs=max_docs_per_query
        )
        llm_latencies.append((time.time() - llm_start) * 1000)
        
        if relevance_result.get("error"):
            errors.append({"query": case["query"], "error": relevance_result["error"]})
        
        judge_evaluator.add_relevance_result(
            query=case["query"],
            relevance_result=relevance_result,
            metadata={
                "difficulty": case.get("difficulty", "unknown"),
                "collection": case["collection"],
                "case_type": case.get("case_type", "retrieval")
            }
        )
    
    # Compute metrics
    llm_metrics = judge_evaluator.compute_metrics()
    
    # Latency stats
    latency_stats = {
        "retrieval_p50_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        "retrieval_mean_ms": sum(latencies) / len(latencies) if latencies else 0,
        "llm_judge_p50_ms": sorted(llm_latencies)[len(llm_latencies) // 2] if llm_latencies else 0,
        "llm_judge_mean_ms": sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0,
        "total_s": (sum(latencies) + sum(llm_latencies)) / 1000
    }
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "llm_judge",
        "total_cases": len(cases),
        "cache_hit_rate": cache_hits / len(cases) if cases else 0,
        "error_count": len(errors),
        "metrics": llm_metrics,
        "latency": latency_stats,
        "errors": errors[:10]
    }
    
    return report


def print_llm_judge_report(report: dict):
    """Pretty print the LLM judge evaluation report."""
    print("\n" + "=" * 60)
    print("🤖 FAIRTRACE LLM-AS-JUDGE REPORT")
    print("=" * 60)
    
    print(f"\n📅 Timestamp: {report['timestamp']}")
    print(f"📝 Total Cases: {report['total_cases']}")
    print(f"⚡ Cache Hit Rate: {report['cache_hit_rate']:.1%}")
    print(f"❌ Errors: {report['error_count']}")
    
    # LLM Judge metrics
    print("\n" + "-" * 40)
    print("🎯 LLM RELEVANCE METRICS")
    print("-" * 40)
    metrics = report["metrics"]
    print(f"  Mean Relevance:        {metrics.get('mean_relevance', 0):.3f}")
    print(f"  Binary Relevance (≥0.5): {metrics.get('mean_binary_relevance', 0):.1%}")
    print(f"  Cases Evaluated:       {metrics.get('relevance_cases', 0)}")
    
    # Latency
    print("\n" + "-" * 40)
    print("⏱️  LATENCY")
    print("-" * 40)
    lat = report["latency"]
    print(f"  Retrieval P50:  {lat.get('retrieval_p50_ms', 0):.0f}ms")
    print(f"  LLM Judge P50:  {lat.get('llm_judge_p50_ms', 0):.0f}ms")
    print(f"  Total Time:     {lat.get('total_s', 0):.1f}s")
    
    print("\n" + "=" * 60)


def print_report(report: dict):
    """Pretty print the evaluation report."""
    print("\n" + "=" * 60)
    print("📊 FAIRTRACE EVALUATION REPORT")
    print("=" * 60)
    
    print(f"\n📅 Timestamp: {report['timestamp']}")
    print(f"📝 Total Cases: {report['total_cases']}")
    print(f"⚡ Cache Hit Rate: {report['cache_hit_rate']:.1%}")
    print(f"❌ Errors: {report['error_count']}")
    
    # Overall metrics
    print("\n" + "-" * 40)
    print("📈 OVERALL METRICS")
    print("-" * 40)
    overall = report["metrics"]["overall"]
    print(f"  Recall@10:   {overall.get('recall@10', 0):.3f}")
    print(f"  Recall@25:   {overall.get('recall@25', 0):.3f}")
    print(f"  Recall@50:   {overall.get('recall@50', 0):.3f}")
    print(f"  Precision@10:{overall.get('precision@10', 0):.3f}")
    print(f"  MRR:         {overall.get('mrr', 0):.3f}")
    print(f"  NDCG@25:     {overall.get('ndcg@25', 0):.3f}")
    if "negative_exclusion_rate" in overall:
        print(f"  Neg. Excl.:  {overall['negative_exclusion_rate']:.3f}")
    
    # By difficulty
    print("\n" + "-" * 40)
    print("📊 BY DIFFICULTY")
    print("-" * 40)
    for difficulty, metrics in report["metrics"]["by_difficulty"].items():
        r5 = metrics.get('recall@5', 0)
        mrr = metrics.get('mrr', 0)
        n = metrics.get('total_positive_cases', 0) + metrics.get('total_negative_cases', 0)
        print(f"  {difficulty:10s}: Recall@5={r5:.3f}, MRR={mrr:.3f}, n={n}")
    
    # By collection
    print("\n" + "-" * 40)
    print("📊 BY COLLECTION")
    print("-" * 40)
    for collection, metrics in report["metrics"]["by_collection"].items():
        r5 = metrics.get('recall@5', 0)
        mrr = metrics.get('mrr', 0)
        n = metrics.get('total_positive_cases', 0) + metrics.get('total_negative_cases', 0)
        print(f"  {collection:15s}: Recall@5={r5:.3f}, MRR={mrr:.3f}, n={n}")
    
    # Latency
    print("\n" + "-" * 40)
    print("⏱️  LATENCY")
    print("-" * 40)
    lat = report["latency"]
    print(f"  P50:   {lat['p50_ms']:.0f}ms")
    print(f"  P95:   {lat['p95_ms']:.0f}ms")
    print(f"  P99:   {lat['p99_ms']:.0f}ms")
    print(f"  Mean:  {lat['mean_ms']:.0f}ms")
    print(f"  Total: {lat['total_s']:.1f}s")
    
    print("\n" + "=" * 60)


def save_report(report: dict):
    """Save report to JSON file."""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = REPORTS_DIR / f"report_{timestamp}.json"
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="FairTrace Evaluation Runner")
    parser.add_argument("--limit", type=int, help="Limit number of test cases")
    parser.add_argument("--collection", type=str, help="Filter by collection")
    parser.add_argument("--type", type=str, default="retrieval", help="Case type (retrieval, reasoning, decision, fairness)")
    parser.add_argument("--llm-judge", action="store_true", help="Use LLM-as-Judge for relevance scoring")
    parser.add_argument("--rerank", action="store_true", help="Use BGE reranker for two-stage retrieval")
    parser.add_argument("--query-expand", action="store_true", help="Use LLM query expansion (qwen2.5:3b)")
    parser.add_argument("--parse", action="store_true", help="Use Query Parser to extract metadata filters")
    parser.add_argument("--no-save", action="store_true", help="Don't save report to file")
    
    args = parser.parse_args()
    
    # Load test cases
    print(f"📂 Loading test cases from {GOLDEN_FILE}...")
    cases = load_golden_cases(
        limit=args.limit,
        case_type=args.type,
        collection=args.collection
    )
    print(f"✓ Loaded {len(cases)} cases")
    
    if not cases:
        print("❌ No test cases found!")
        return
    
    # Run evaluation
    if args.llm_judge:
        report = run_llm_judge_evaluation(
            cases, 
            query_expand=args.query_expand, 
            rerank=args.rerank
        )
        print_llm_judge_report(report)
    else:
        report = run_evaluation(cases, rerank=args.rerank, use_parser=args.parse)
        print_report(report)
    
    # Save report
    if not args.no_save:
        save_report(report)


if __name__ == "__main__":
    main()
