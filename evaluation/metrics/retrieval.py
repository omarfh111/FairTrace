"""
Retrieval Metrics Module

Calculates standard IR metrics:
- Recall@K: Fraction of relevant documents retrieved in top-K
- Precision@K: Fraction of top-K that are relevant
- MRR: Mean Reciprocal Rank
- NDCG@K: Normalized Discounted Cumulative Gain
"""

import numpy as np
from typing import Literal


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    """
    Calculate Recall@K.
    
    Args:
        retrieved_ids: List of document IDs from search (ordered by rank)
        expected_ids: List of relevant document IDs (ground truth)
        k: Number of top results to consider
    
    Returns:
        Fraction of expected_ids found in top-k retrieved_ids
    """
    if not expected_ids:
        return 1.0  # No expected docs = perfect recall
    
    top_k = set(retrieved_ids[:k])
    expected = set(expected_ids)
    
    hits = len(top_k & expected)
    return hits / len(expected)


def precision_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    """
    Calculate Precision@K.
    
    Args:
        retrieved_ids: List of document IDs from search (ordered by rank)
        expected_ids: List of relevant document IDs (ground truth)
        k: Number of top results to consider
    
    Returns:
        Fraction of top-k that are relevant
    """
    if k == 0:
        return 0.0
    
    top_k = retrieved_ids[:k]
    expected = set(expected_ids)
    
    hits = sum(1 for doc_id in top_k if doc_id in expected)
    return hits / k


def reciprocal_rank(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """
    Calculate Reciprocal Rank (for MRR calculation).
    
    Returns 1/rank of first relevant document, or 0 if none found.
    """
    expected = set(expected_ids)
    
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in expected:
            return 1.0 / rank
    
    return 0.0


def mean_reciprocal_rank(results: list[tuple[list[str], list[str]]]) -> float:
    """
    Calculate Mean Reciprocal Rank across multiple queries.
    
    Args:
        results: List of (retrieved_ids, expected_ids) tuples
    
    Returns:
        Average reciprocal rank
    """
    if not results:
        return 0.0
    
    rr_sum = sum(reciprocal_rank(retrieved, expected) for retrieved, expected in results)
    return rr_sum / len(results)


def ndcg_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain @ K.
    
    Gives higher scores when relevant docs appear earlier in results.
    """
    expected = set(expected_ids)
    
    # DCG: sum of relevance / log2(rank + 1)
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved_ids[:k], start=1):
        if doc_id in expected:
            dcg += 1.0 / np.log2(rank + 1)
    
    # Ideal DCG: if all relevant docs were at top
    ideal_dcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(expected), k)))
    
    if ideal_dcg == 0:
        return 1.0  # No relevant docs = perfect by default
    
    return dcg / ideal_dcg


def negative_precision(
    retrieved_ids: list[str], 
    negative_ids: list[str], 
    k: int
) -> float:
    """
    Calculate precision for negative examples.
    
    Returns the fraction of top-k that correctly EXCLUDE the negative IDs.
    Higher is better (we want negatives to NOT appear).
    """
    if k == 0:
        return 1.0
    
    top_k = set(retrieved_ids[:k])
    negative = set(negative_ids)
    
    # Count how many negatives incorrectly appeared
    false_positives = len(top_k & negative)
    
    # Return 1 - (false_positive_rate)
    return 1.0 - (false_positives / k)


class RetrievalEvaluator:
    """Aggregates retrieval metrics across multiple test cases."""
    
    def __init__(self):
        self.results = []
        self.negative_results = []
    
    def add_result(
        self, 
        query: str,
        retrieved_ids: list[str], 
        expected_ids: list[str],
        is_negative: bool = False,
        metadata: dict | None = None
    ):
        """Add a single evaluation result."""
        result = {
            "query": query,
            "retrieved_ids": retrieved_ids,
            "expected_ids": expected_ids,
            "is_negative": is_negative,
            "metadata": metadata or {}
        }
        
        if is_negative:
            self.negative_results.append(result)
        else:
            self.results.append(result)
    
    def compute_metrics(self, k_values: list[int] = [5, 10]) -> dict:
        """Compute all metrics."""
        metrics = {}
        
        # Positive cases
        for k in k_values:
            recalls = [
                recall_at_k(r["retrieved_ids"], r["expected_ids"], k) 
                for r in self.results
            ]
            precisions = [
                precision_at_k(r["retrieved_ids"], r["expected_ids"], k) 
                for r in self.results
            ]
            ndcgs = [
                ndcg_at_k(r["retrieved_ids"], r["expected_ids"], k) 
                for r in self.results
            ]
            
            metrics[f"recall@{k}"] = np.mean(recalls) if recalls else 0.0
            metrics[f"precision@{k}"] = np.mean(precisions) if precisions else 0.0
            metrics[f"ndcg@{k}"] = np.mean(ndcgs) if ndcgs else 0.0
        
        # MRR
        if self.results:
            rr_pairs = [(r["retrieved_ids"], r["expected_ids"]) for r in self.results]
            metrics["mrr"] = mean_reciprocal_rank(rr_pairs)
        else:
            metrics["mrr"] = 0.0
        
        # Negative precision
        if self.negative_results:
            neg_precisions = [
                negative_precision(r["retrieved_ids"], r["expected_ids"], 10) 
                for r in self.negative_results
            ]
            metrics["negative_exclusion_rate"] = np.mean(neg_precisions)
        
        # Counts
        metrics["total_positive_cases"] = len(self.results)
        metrics["total_negative_cases"] = len(self.negative_results)
        
        return metrics
    
    def compute_metrics_by_group(
        self, 
        group_key: str, 
        k_values: list[int] = [5, 10]
    ) -> dict[str, dict]:
        """Compute metrics grouped by a metadata key (e.g., 'difficulty', 'collection')."""
        groups = {}
        
        for result in self.results + self.negative_results:
            group = result["metadata"].get(group_key, "unknown")
            if group not in groups:
                groups[group] = RetrievalEvaluator()
            
            groups[group].add_result(
                query=result["query"],
                retrieved_ids=result["retrieved_ids"],
                expected_ids=result["expected_ids"],
                is_negative=result["is_negative"],
                metadata=result["metadata"]
            )
        
        return {group: evaluator.compute_metrics(k_values) for group, evaluator in groups.items()}
