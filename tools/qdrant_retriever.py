"""
Qdrant Retriever - Hybrid Search Wrapper with LangSmith Tracing

Features:
- Named Vector search (structured, narrative)
- Sparse Vector search (keywords)
- Hybrid fusion (RRF)
- Metadata filtering
- LangSmith tracing with timing metrics
- Redis semantic caching (threshold: 0.82)
- Embedding reuse across multiple searches
- Search result caching (skip Qdrant for similar queries)
"""

import os
import time
import concurrent.futures
from typing import Literal, Any

import ollama
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langsmith import traceable

# Caching disabled - set to False unconditionally
CACHE_AVAILABLE = False

load_dotenv()

# Configuration
DENSE_MODEL = "qwen3-embedding:0.6b"
DENSE_DIM = 1024
SPARSE_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"
SEMANTIC_CACHE_THRESHOLD = 0.82

# Initialize clients
_qdrant_client: QdrantClient | None = None
_sparse_encoder: SparseTextEmbedding | None = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if not url or not api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")
        _qdrant_client = QdrantClient(url=url, api_key=api_key, timeout=250)
    return _qdrant_client


def get_sparse_encoder() -> SparseTextEmbedding:
    """Get or create sparse encoder singleton."""
    global _sparse_encoder
    if _sparse_encoder is None:
        _sparse_encoder = SparseTextEmbedding(model_name=SPARSE_MODEL)
    return _sparse_encoder


def _embed_dense_raw(text: str) -> list[float]:
    """Generate dense embedding using Ollama (no cache)."""
    response = ollama.embed(model=DENSE_MODEL, input=text)
    return response["embeddings"][0]


@traceable(name="embed_dense", run_type="embedding")
def embed_dense(text: str) -> list[float]:
    """
    Generate dense embedding with smart semantic caching.
    
    Flow:
    1. Check exact text match in cache (O(1), no embedding needed!)
    2. If miss, compute embedding and check semantic similarity
    3. Return cached or new embedding
    """
    if not CACHE_AVAILABLE:
        return _embed_dense_raw(text)
    
    try:
        vector, was_hit = get_or_compute_embedding(text, _embed_dense_raw, SEMANTIC_CACHE_THRESHOLD)
        return vector
    except Exception:
        # Cache error - compute directly
        return _embed_dense_raw(text)


@traceable(name="embed_query", run_type="embedding")
def embed_query(text: str) -> tuple[list[float], list[int], list[float]]:
    """
    Compute both dense and sparse embeddings for a query.
    Use this to compute embeddings once and reuse across multiple searches.
    
    Returns:
        tuple of (dense_vector, sparse_indices, sparse_values)
    """
    dense_vector = embed_dense(text)
    sparse_indices, sparse_values = embed_sparse(text)
    return dense_vector, sparse_indices, sparse_values


@traceable(name="embed_sparse", run_type="embedding")
def embed_sparse(text: str) -> tuple[list[int], list[float]]:
    """Generate sparse embedding using FastEmbed."""
    start = time.time()
    encoder = get_sparse_encoder()
    embeddings = list(encoder.embed([text]))[0]
    latency_ms = (time.time() - start) * 1000
    return embeddings.indices.tolist(), embeddings.values.tolist()


# =============================================================================
# RERANKING WITH SENTENCE-TRANSFORMERS CROSSENCODER
# =============================================================================
# Uses ms-marco-MiniLM-L-6-v2 for fast, reliable reranking
from sentence_transformers import CrossEncoder

# Singleton for reranker model
_reranker_model: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    """Get or create reranker model singleton."""
    global _reranker_model
    if _reranker_model is None:
        print("Loading cross-encoder/ms-marco-MiniLM-L-6-v2 (first use)...")
        _reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        print("✓ Reranker loaded")
    return _reranker_model


def _format_doc_for_rerank(payload: dict) -> str:
    """Format document payload into text for reranking."""
    if "client_id" in payload:
        return f"Client: income €{payload.get('income_annual', 0):,.0f}, DTI {payload.get('debt_to_income_ratio', 0):.2f}, {payload.get('missed_payments_last_12m', 0)} missed payments, outcome: {payload.get('outcome', 'Unknown')}"
    elif "startup_id" in payload:
        return f"Startup: {payload.get('sector', '')} sector, ARR ${payload.get('arr_current', 0):,.0f}, runway {payload.get('runway_months', 0):.0f}mo, outcome: {payload.get('outcome', 'Unknown')}"
    elif "enterprise_id" in payload:
        return f"Enterprise: {payload.get('industry_code', '')} industry, revenue €{payload.get('revenue_annual', 0):,.0f}, Z-score {payload.get('altman_z_score', 0):.2f}, outcome: {payload.get('outcome', 'Unknown')}"
    elif "content" in payload:  # Regulation chunks
        article = payload.get('article_ref', '')
        page = payload.get('page_number', '')
        content = payload.get('content', '')[:500]
        return f"[Page {page}] {article}\n{content}"
    else:
        return str(payload)[:300]


@traceable(name="rerank_results", run_type="chain")
def rerank_results(
    query: str,
    results: list[dict],
    top_k: int = 10
) -> tuple[list[dict], float]:
    """
    Rerank search results using CrossEncoder.
    
    Uses ms-marco-MiniLM-L-6-v2 for fast, production-grade reranking.
    
    Args:
        query: The search query
        results: List of search results with 'payload' and 'score' keys
        top_k: Number of top results to return after reranking
        
    Returns:
        Tuple of (reranked_results, rerank_latency_ms)
    """
    if not results:
        return [], 0.0
    
    start = time.time()
    
    try:
        reranker = get_reranker()
        
        # Format documents for reranking
        documents = [_format_doc_for_rerank(r.get("payload", {})) for r in results]
        
        # Create query-document pairs for CrossEncoder
        pairs = [[query, doc] for doc in documents]
        
        # Score all pairs at once
        scores = reranker.predict(pairs)
        
        # Build scored results maintaining original result data
        scored_results = []
        for i, (result, score) in enumerate(zip(results, scores)):
            scored_results.append({
                **result,
                "original_score": result.get("score", 0),
                "rerank_score": float(score),
                "score": float(score)
            })
        
        # Sort by rerank score (descending)
        scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)
        
    except Exception as e:
        print(f"⚠️ Reranking failed: {e}, using original order")
        scored_results = results
    
    rerank_latency = (time.time() - start) * 1000
    
    return scored_results[:top_k], rerank_latency


# =============================================================================
# SEARCH FUNCTIONS WITH TRACING
# =============================================================================
@traceable(name="qdrant_search_structured", run_type="retriever")
def search_by_structured(
    collection: str,
    query_text: str,
    limit: int = 10,
    filters: dict | None = None
) -> dict:
    """Search using the 'structured' vector (financial metrics)."""
    start = time.time()
    
    client = get_qdrant_client()
    query_vector = embed_dense(query_text)
    
    query_filter = _build_filter(filters) if filters else None
    
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        using="structured",
        query_filter=query_filter,
        limit=limit,
        with_payload=True
    )
    
    latency_ms = (time.time() - start) * 1000
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    # Return with metadata for LangSmith
    return {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(latency_ms, 2),
        "collection": collection,
        "vector_type": "structured"
    }


@traceable(name="qdrant_search_narrative", run_type="retriever")
def search_by_narrative(
    collection: str,
    query_text: str,
    limit: int = 10,
    filters: dict | None = None
) -> dict:
    """Search using the 'narrative' vector (text descriptions)."""
    start = time.time()
    
    client = get_qdrant_client()
    query_vector = embed_dense(query_text)
    
    query_filter = _build_filter(filters) if filters else None
    
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        using="narrative",
        query_filter=query_filter,
        limit=limit,
        with_payload=True
    )
    
    latency_ms = (time.time() - start) * 1000
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    return {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(latency_ms, 2),
        "collection": collection,
        "vector_type": "narrative"
    }


@traceable(name="qdrant_search_keywords", run_type="retriever")
def search_by_keywords(
    collection: str,
    query_text: str,
    limit: int = 10,
    filters: dict | None = None
) -> dict:
    """Search using the 'keywords' sparse vector."""
    start = time.time()
    
    client = get_qdrant_client()
    indices, values = embed_sparse(query_text)
    
    query_filter = _build_filter(filters) if filters else None
    
    results = client.query_points(
        collection_name=collection,
        query=models.SparseVector(indices=indices, values=values),
        using="keywords",
        query_filter=query_filter,
        limit=limit,
        with_payload=True
    )
    
    latency_ms = (time.time() - start) * 1000
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    return {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(latency_ms, 2),
        "collection": collection,
        "vector_type": "keywords"
    }


@traceable(name="qdrant_hybrid_search", run_type="retriever")
def hybrid_search(
    collection: str,
    query_text: str,
    limit: int = 10,
    filters: dict | None = None,
    weights: dict[str, float] | None = None,
    dense_vector: list[float] | None = None,
    sparse_indices: list[int] | None = None,
    sparse_values: list[float] | None = None,
    rerank: bool = False,
    rerank_top_k: int | None = None
) -> dict:
    """
    Hybrid search using RRF fusion across all vector types.
    
    Args:
        collection: Collection name
        query_text: Search query
        limit: Number of results
        filters: Metadata filters
        weights: Vector weights, e.g., {"structured": 0.5, "narrative": 0.3, "keywords": 0.2}
        dense_vector: Pre-computed dense embedding (optional, avoids recomputation)
        sparse_indices: Pre-computed sparse indices (optional)
        sparse_values: Pre-computed sparse values (optional)
        rerank: If True, use BGE reranker for two-stage retrieval
        rerank_top_k: Initial results to retrieve before reranking (default: limit * 5)
    """
    start = time.time()
    
    # For reranking, retrieve more initially
    retrieval_limit = limit
    if rerank:
        retrieval_limit = rerank_top_k or (limit * 5)  # Retrieve 5x more for reranking
    
    # Default weights
    if weights is None:
        weights = {"structured": 0.4, "narrative": 0.4, "keywords": 0.2}
    
    # Check search result cache first
    if CACHE_AVAILABLE:
        cached_results = get_cached_search_results(
            query_text, collection, filters, weights,
            query_vector=dense_vector
        )
        if cached_results:
            cached_results["cache_hit"] = True
            return cached_results
    
    client = get_qdrant_client()
    
    # Generate embeddings only if not provided
    embed_start = time.time()
    
    # Run embeddings in parallel
    if dense_vector is None or (sparse_indices is None or sparse_values is None):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            if dense_vector is None:
                futures["dense"] = executor.submit(embed_dense, query_text)
            if sparse_indices is None or sparse_values is None:
                futures["sparse"] = executor.submit(embed_sparse, query_text)
            
            # Wait for results
            if "dense" in futures:
                dense_vector = futures["dense"].result()
            if "sparse" in futures:
                sparse_indices, sparse_values = futures["sparse"].result()
                
    embed_latency = (time.time() - embed_start) * 1000
    
    query_filter = _build_filter(filters) if filters else None
    
    # Build prefetch queries for each vector type
    prefetch = []
    
    if weights.get("structured", 0) > 0:
        prefetch.append(
            models.Prefetch(
                query=dense_vector,
                using="structured",
                limit=retrieval_limit * 2
            )
        )
    
    if weights.get("narrative", 0) > 0:
        prefetch.append(
            models.Prefetch(
                query=dense_vector,
                using="narrative",
                limit=retrieval_limit * 2
            )
        )
    
    if weights.get("keywords", 0) > 0:
        prefetch.append(
            models.Prefetch(
                query=models.SparseVector(indices=sparse_indices, values=sparse_values),
                using="keywords",
                limit=retrieval_limit * 2
            )
        )
    
    # Perform fusion search
    search_start = time.time()
    results = client.query_points(
        collection_name=collection,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=query_filter,
        limit=retrieval_limit,
        with_payload=True
    )
    search_latency = (time.time() - search_start) * 1000
    
    total_latency = (time.time() - start) * 1000
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    # Apply reranking if enabled
    rerank_latency = 0.0
    if rerank and formatted:
        formatted, rerank_latency = rerank_results(query_text, formatted, top_k=limit)
    
    total_latency = (time.time() - start) * 1000
    
    response = {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(total_latency, 2),
        "embed_latency_ms": round(embed_latency, 2),
        "search_latency_ms": round(search_latency, 2),
        "rerank_latency_ms": round(rerank_latency, 2) if rerank else None,
        "reranked": rerank,
        "collection": collection,
        "vector_type": "hybrid",
        "weights": weights,
        "filters_applied": filters is not None,
        "cache_hit": False
    }
    
    # Cache search results
    if CACHE_AVAILABLE:
        cache_search_results(
            query_text, collection, filters, weights,
            response, query_vector=dense_vector
        )
    
    return response


@traceable(name="qdrant_search_by_outcome", run_type="retriever")
def search_similar_outcomes(
    collection: str,
    query_text: str,
    outcome: str,
    limit: int = 5,
    dense_vector: list[float] | None = None,
    sparse_indices: list[int] | None = None,
    sparse_values: list[float] | None = None,
    filters: dict | None = None
) -> dict:
    """
    Find cases with a specific outcome that are similar to the query.
    
    Args:
        collection: Collection name
        query_text: Search query
        outcome: Required outcome value (e.g., 'DEFAULT', 'BANKRUPT')
        limit: Number of results
        dense_vector: Pre-computed dense embedding
        sparse_indices: Pre-computed sparse indices
        sparse_values: Pre-computed sparse values
        filters: Additional metadata filters (will be merged with outcome filter)
    """
    # Merge outcome into filters
    all_filters = {"outcome": outcome}
    if filters:
        all_filters.update(filters)
        
    return hybrid_search(
        collection=collection,
        query_text=query_text,
        limit=limit,
        filters=all_filters,
        dense_vector=dense_vector,
        sparse_indices=sparse_indices,
        sparse_values=sparse_values
    )


@traceable(name="qdrant_search_excluding_outcome", run_type="retriever")
def search_excluding_outcome(
    collection: str,
    query_text: str,
    exclude_outcome: str,
    limit: int = 5
) -> dict:
    """Find cases excluding a specific outcome."""
    start = time.time()
    
    client = get_qdrant_client()
    dense_vector = embed_dense(query_text)
    
    results = client.query_points(
        collection_name=collection,
        query=dense_vector,
        using="narrative",
        query_filter=models.Filter(
            must_not=[
                models.FieldCondition(
                    key="outcome",
                    match=models.MatchValue(value=exclude_outcome)
                )
            ]
        ),
        limit=limit,
        with_payload=True
    )
    
    latency_ms = (time.time() - start) * 1000
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    return {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(latency_ms, 2),
        "collection": collection,
        "excluded_outcome": exclude_outcome
    }


# =============================================================================
# REGULATION SEARCH (uses 'content' vector instead of 'structured'/'narrative')
# =============================================================================
@traceable(name="qdrant_search_regulations", run_type="retriever")
def search_regulations(
    query_text: str,
    limit: int = 10,
    filters: dict | None = None,
    article_ref: str | None = None,
    page_number: int | None = None,
    dense_vector: list[float] | None = None,
    sparse_indices: list[int] | None = None,
    sparse_values: list[float] | None = None,
    rerank: bool = False,
    rerank_top_k: int | None = None,
) -> dict:
    """
    Hybrid search for banking regulations (regulations_v3 collection).
    
    Uses RRF fusion of 'content' (dense) and 'keywords' (sparse) vectors.
    
    Args:
        query_text: Search query
        limit: Number of results
        filters: Additional metadata filters
        article_ref: Filter by specific article reference (e.g., "Article 52")
        page_number: Filter by specific page number
        dense_vector: Pre-computed dense embedding (optional)
        sparse_indices: Pre-computed sparse indices (optional)
        sparse_values: Pre-computed sparse values (optional)
        rerank: If True, use mxbai reranker for two-stage retrieval
        rerank_top_k: Initial results to retrieve before reranking (default: limit * 3)
        
    Returns:
        Dict with results, count, latency, and metadata
    """
    start = time.time()
    collection = "regulations_v4"
    
    # For reranking, retrieve more initially
    retrieval_limit = limit
    if rerank:
        retrieval_limit = rerank_top_k or (limit * 3)
    
    client = get_qdrant_client()
    
    # Build filters
    all_filters = filters.copy() if filters else {}
    if article_ref:
        all_filters["article_ref"] = article_ref
    if page_number:
        all_filters["page_number"] = page_number
    
    query_filter = _build_filter(all_filters) if all_filters else None
    
    # Generate embeddings if not provided
    embed_start = time.time()
    if dense_vector is None or sparse_indices is None or sparse_values is None:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            if dense_vector is None:
                futures["dense"] = executor.submit(embed_dense, query_text)
            if sparse_indices is None or sparse_values is None:
                futures["sparse"] = executor.submit(embed_sparse, query_text)
            
            if "dense" in futures:
                dense_vector = futures["dense"].result()
            if "sparse" in futures:
                sparse_indices, sparse_values = futures["sparse"].result()
    
    embed_latency = (time.time() - embed_start) * 1000
    
    # Build prefetch queries for regulation vectors
    prefetch = [
        models.Prefetch(
            query=dense_vector,
            using="content",  # Regulations use 'content' not 'structured'
            limit=retrieval_limit * 2
        ),
        models.Prefetch(
            query=models.SparseVector(indices=sparse_indices, values=sparse_values),
            using="keywords",
            limit=retrieval_limit * 2
        )
    ]
    
    # Perform fusion search
    search_start = time.time()
    results = client.query_points(
        collection_name=collection,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=query_filter,
        limit=retrieval_limit,
        with_payload=True
    )
    search_latency = (time.time() - search_start) * 1000
    
    formatted = [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    # Apply reranking if enabled
    rerank_latency = 0.0
    if rerank and formatted:
        formatted, rerank_latency = rerank_results(query_text, formatted, top_k=limit)
    
    total_latency = (time.time() - start) * 1000
    
    return {
        "results": formatted,
        "count": len(formatted),
        "latency_ms": round(total_latency, 2),
        "embed_latency_ms": round(embed_latency, 2),
        "search_latency_ms": round(search_latency, 2),
        "rerank_latency_ms": round(rerank_latency, 2) if rerank else None,
        "reranked": rerank,
        "collection": collection,
        "vector_type": "hybrid",
        "filters_applied": all_filters if all_filters else None
    }


def format_regulation_result(result: dict) -> str:
    """Format a regulation search result for LLM consumption."""
    payload = result["payload"]
    score = result["score"]
    
    article = payload.get("article_ref", "")
    section = payload.get("section_title", "")
    page = payload.get("page_number", "?")
    content = payload.get("content", "")[:500]
    
    header = f"[Page {page}]"
    if article:
        header += f" {article}"
    if section:
        header += f" - {section}"
    
    return f"{header} (Score: {score:.2f})\n{content}"


def format_regulation_results(results: list[dict]) -> str:
    """Format multiple regulation search results for LLM consumption."""
    if not results:
        return "No relevant regulations found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(f"{i}. {format_regulation_result(result)}")
    
    return "\n\n".join(formatted)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _build_filter(filters: dict) -> models.Filter:
    """Build Qdrant filter from dict."""
    conditions = []
    
    for key, value in filters.items():
        if isinstance(value, list):
            conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchAny(any=value)
                )
            )
        elif isinstance(value, dict):
            # Range filter or exact match
            if "eq" in value:
                eq_val = value["eq"]
                # MatchValue only supports int/str/bool
                if isinstance(eq_val, float):
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            range=models.Range(gte=eq_val, lte=eq_val)
                        )
                    )
                else:
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=eq_val)
                        )
                    )
                
                # If there are other range keys (gte, lte) alongside eq (unlikely but possible)
                range_args = {k: v for k, v in value.items() if k != "eq"}
                if range_args:
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            range=models.Range(**range_args)
                        )
                    )
            else:
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        range=models.Range(**value)
                    )
                )
        else:
            conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                )
            )
    
    return models.Filter(must=conditions)


def format_result_for_llm(result: dict) -> str:
    """Format a search result for LLM consumption."""
    payload = result["payload"]
    score = result["score"]
    
    # Determine entity type
    if "client_id" in payload:
        entity_id = payload["client_id"]
        entity_type = "Client"
        summary = f"Age: {payload['age']}, Contract: {payload.get('contract_type', 'Unknown')}, " \
                  f"DTI: {payload['debt_to_income_ratio']:.1%}, " \
                  f"Missed Payments: {payload['missed_payments_last_12m']}, " \
                  f"Outcome: {payload['outcome']}"
    elif "startup_id" in payload:
        entity_id = payload["startup_id"]
        entity_type = "Startup"
        summary = f"Sector: {payload['sector']}, ARR: ${payload['arr_current']:,.0f}, " \
                  f"Burn Multiple: {payload['burn_multiple']:.1f}x, " \
                  f"Runway: {payload['runway_months']:.0f} months, " \
                  f"Outcome: {payload['outcome']}"
    elif "enterprise_id" in payload:
        entity_id = payload["enterprise_id"]
        entity_type = "Enterprise"
        ceo = payload.get("ceo_profile", {})
        summary = f"Industry: {payload['industry_code']}, " \
                  f"Z-Score: {payload['altman_z_score']:.2f}, " \
                  f"CEO: {ceo.get('name', 'Unknown')}, " \
                  f"Lawsuits: {payload['legal_lawsuits_active']}, " \
                  f"Outcome: {payload['outcome']}"
    else:
        entity_id = str(result["id"])
        entity_type = "Unknown"
        summary = str(payload)
    
    return f"[{entity_type} {entity_id}] (Similarity: {score:.2f})\n{summary}"


def format_results_for_llm(results: list[dict]) -> str:
    """Format multiple search results for LLM consumption."""
    if not results:
        return "No similar cases found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(f"{i}. {format_result_for_llm(result)}")
    
    return "\n\n".join(formatted)
