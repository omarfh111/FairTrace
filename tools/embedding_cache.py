"""
Semantic Embedding & Search Result Cache with Redis

Features:
- Text-hash exact match lookup (O(1), no embedding needed)
- Cosine similarity-based semantic lookup (threshold: 0.82)
- Search result caching (skip Qdrant for similar queries)
- Redis storage for persistence across restarts
- LangSmith traceable for observability

Usage:
    from tools.embedding_cache import (
        get_or_compute_embedding,
        get_cached_search_results,
        cache_search_results
    )
    
    # Smart embedding with cache
    vector, was_hit = get_or_compute_embedding("Find defaults with high DTI", embed_fn)
    
    # Search result caching
    cached = get_cached_search_results(query, collection, filters, weights)
    if cached:
        return cached
    results = run_qdrant_search(...)
    cache_search_results(query, collection, filters, weights, results)
"""

import json
import os
import hashlib
from typing import Optional, Callable, Any

import numpy as np
import redis
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

# Configuration
CACHE_SIMILARITY_THRESHOLD = 0.82  # Cosine similarity threshold
CACHE_TTL_SECONDS = 86400 * 7  # 7 days (vector data doesn't change)
EMBEDDING_CACHE_PREFIX = "fairtrace:embed:"
SEARCH_CACHE_PREFIX = "fairtrace:search:"

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=False  # Handle bytes manually for vectors
        )
    return _redis_client


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def _vector_to_bytes(vector: list[float]) -> bytes:
    """Convert vector to bytes for Redis storage."""
    return np.array(vector, dtype=np.float32).tobytes()


def _bytes_to_vector(data: bytes) -> list[float]:
    """Convert bytes back to vector."""
    return np.frombuffer(data, dtype=np.float32).tolist()


def _get_text_hash(text: str) -> str:
    """Generate deterministic hash from text."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _get_embedding_cache_key(text: str) -> str:
    """Generate cache key from text hash."""
    return f"{EMBEDDING_CACHE_PREFIX}{_get_text_hash(text)}"


def _get_search_cache_key(query: str, collection: str, filters: dict | None, weights: dict | None) -> str:
    """Generate cache key for search results."""
    key_data = {
        "q": query,
        "c": collection,
        "f": filters or {},
        "w": weights or {}
    }
    key_hash = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:24]
    return f"{SEARCH_CACHE_PREFIX}{key_hash}"


# =============================================================================
# EMBEDDING CACHE - Smart lookup (exact match first, then semantic)
# =============================================================================

@traceable(name="embedding_cache_lookup", run_type="retriever")
def get_or_compute_embedding(
    query_text: str,
    embed_fn: Callable[[str], list[float]],
    threshold: float = CACHE_SIMILARITY_THRESHOLD
) -> tuple[list[float], bool]:
    """
    Smart embedding cache with exact match + semantic fallback.
    
    Flow:
    1. Check exact text match (O(1) hash lookup) - NO embedding needed
    2. If miss, compute embedding
    3. Check semantic similarity against cached embeddings
    4. If similar found (≥0.82), return cached for consistency
    5. Otherwise store new embedding and return
    
    Args:
        query_text: The query to embed
        embed_fn: Function to compute embedding (e.g., ollama.embed)
        threshold: Cosine similarity threshold (default: 0.82)
    
    Returns:
        tuple of (embedding vector, was_cache_hit)
    """
    try:
        client = get_redis_client()
        cache_key = _get_embedding_cache_key(query_text)
        
        # Step 1: Exact text match (O(1), no embedding needed!)
        cached_data = client.hgetall(cache_key)
        if cached_data and b"vector" in cached_data:
            cached_vector = _bytes_to_vector(cached_data[b"vector"])
            return cached_vector, True  # Cache hit!
        
        # Step 2: Cache miss - compute embedding
        vector = embed_fn(query_text)
        
        # Step 3: Check semantic similarity against all cached embeddings
        keys = client.keys(f"{EMBEDDING_CACHE_PREFIX}*")
        best_match = None
        best_similarity = 0.0
        
        for key in keys[:100]:  # Limit scan to 100 entries for performance
            entry = client.hgetall(key)
            if not entry or b"vector" not in entry:
                continue
            
            cached_vector = _bytes_to_vector(entry[b"vector"])
            similarity = cosine_similarity(vector, cached_vector)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cached_vector
        
        # Step 4: If semantically similar, return cached for consistency
        if best_match and best_similarity >= threshold:
            return best_match, True
        
        # Step 5: Store new embedding
        client.hset(cache_key, mapping={
            "text": query_text.encode("utf-8"),
            "vector": _vector_to_bytes(vector)
        })
        client.expire(cache_key, CACHE_TTL_SECONDS)
        
        return vector, False
        
    except redis.ConnectionError:
        # Redis not available - compute without caching
        return embed_fn(query_text), False
    except Exception as e:
        print(f"Embedding cache error: {e}")
        return embed_fn(query_text), False


# =============================================================================
# SEARCH RESULT CACHE - Skip Qdrant entirely for similar queries
# =============================================================================

@traceable(name="search_cache_lookup", run_type="retriever")
def get_cached_search_results(
    query_text: str,
    collection: str,
    filters: dict | None = None,
    weights: dict | None = None,
    query_vector: list[float] | None = None,
    threshold: float = CACHE_SIMILARITY_THRESHOLD
) -> Optional[dict]:
    """
    Check if similar search results are cached.
    
    Args:
        query_text: The search query
        collection: Qdrant collection name
        filters: Applied filters
        weights: Hybrid search weights
        query_vector: Pre-computed query embedding (for semantic matching)
        threshold: Similarity threshold for semantic matching
    
    Returns:
        Cached search results dict if hit, None if miss
    """
    try:
        client = get_redis_client()
        cache_key = _get_search_cache_key(query_text, collection, filters, weights)
        
        # Check exact match first (using hgetall since we store as hash)
        cached_data = client.hgetall(cache_key)
        if cached_data and b"results" in cached_data:
            cached_collection = cached_data.get(b"collection", b"").decode("utf-8")
            if cached_collection == collection:
                return json.loads(cached_data[b"results"].decode("utf-8"))
        
        # Semantic match (if vector provided)
        if query_vector:
            keys = client.keys(f"{SEARCH_CACHE_PREFIX}*")
            for key in keys[:50]:  # Limit scan
                if key == cache_key.encode():  # Skip already checked key
                    continue
                try:
                    entry = client.hgetall(key)
                    if not entry:
                        continue
                    
                    if b"vector" in entry and b"results" in entry:
                        cached_vector = _bytes_to_vector(entry[b"vector"])
                        similarity = cosine_similarity(query_vector, cached_vector)
                        
                        if similarity >= threshold:
                            # Check collection matches
                            cached_collection = entry.get(b"collection", b"").decode("utf-8")
                            if cached_collection == collection:
                                return json.loads(entry[b"results"].decode("utf-8"))
                except redis.ResponseError:
                    # Skip keys with wrong type
                    continue
        
        return None
        
    except redis.ConnectionError:
        return None
    except Exception as e:
        print(f"Search cache lookup error: {e}")
        return None


@traceable(name="search_cache_store", run_type="chain")
def cache_search_results(
    query_text: str,
    collection: str,
    filters: dict | None,
    weights: dict | None,
    results: dict,
    query_vector: list[float] | None = None
) -> bool:
    """
    Store search results in Redis cache.
    
    Args:
        query_text: The search query
        collection: Qdrant collection name  
        filters: Applied filters
        weights: Hybrid search weights
        results: Search results to cache
        query_vector: Query embedding (for semantic matching)
    
    Returns:
        True if stored successfully
    """
    try:
        client = get_redis_client()
        cache_key = _get_search_cache_key(query_text, collection, filters, weights)
        
        if query_vector:
            # Store with vector for semantic matching
            client.hset(cache_key, mapping={
                "query": query_text.encode("utf-8"),
                "collection": collection.encode("utf-8"),
                "vector": _vector_to_bytes(query_vector),
                "results": json.dumps(results).encode("utf-8")
            })
        else:
            # Store as simple key-value
            client.set(cache_key, json.dumps(results).encode("utf-8"))
        
        client.expire(cache_key, CACHE_TTL_SECONDS)
        return True
        
    except redis.ConnectionError:
        return False
    except Exception as e:
        print(f"Search cache store error: {e}")
        return False


# =============================================================================
# LEGACY FUNCTIONS (for backwards compatibility)
# =============================================================================

def get_cached_embedding(
    query_text: str, 
    query_vector: list[float],
    threshold: float = CACHE_SIMILARITY_THRESHOLD
) -> Optional[dict]:
    """Legacy function - use get_or_compute_embedding instead."""
    try:
        client = get_redis_client()
        keys = client.keys(f"{EMBEDDING_CACHE_PREFIX}*")
        
        if not keys:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        for key in keys:
            cached_data = client.hgetall(key)
            if not cached_data or b"vector" not in cached_data:
                continue
            
            cached_vector = _bytes_to_vector(cached_data[b"vector"])
            similarity = cosine_similarity(query_vector, cached_vector)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    "vector": cached_vector,
                    "similarity": similarity,
                    "original_text": cached_data.get(b"text", b"").decode("utf-8")
                }
        
        if best_match and best_match["similarity"] >= threshold:
            return best_match
        
        return None
        
    except Exception:
        return None


def cache_embedding(text: str, vector: list[float]) -> bool:
    """Legacy function - store embedding in cache."""
    try:
        client = get_redis_client()
        key = _get_embedding_cache_key(text)
        
        client.hset(key, mapping={
            "text": text.encode("utf-8"),
            "vector": _vector_to_bytes(vector)
        })
        client.expire(key, CACHE_TTL_SECONDS)
        return True
        
    except Exception:
        return False


def clear_cache() -> int:
    """Clear all cached embeddings and search results."""
    try:
        client = get_redis_client()
        embed_keys = client.keys(f"{EMBEDDING_CACHE_PREFIX}*")
        search_keys = client.keys(f"{SEARCH_CACHE_PREFIX}*")
        all_keys = embed_keys + search_keys
        if all_keys:
            return client.delete(*all_keys)
        return 0
    except Exception:
        return 0


def get_cache_stats() -> dict:
    """Get cache statistics."""
    try:
        client = get_redis_client()
        embed_keys = client.keys(f"{EMBEDDING_CACHE_PREFIX}*")
        search_keys = client.keys(f"{SEARCH_CACHE_PREFIX}*")
        return {
            "embedding_entries": len(embed_keys),
            "search_entries": len(search_keys),
            "total_entries": len(embed_keys) + len(search_keys),
            "redis_connected": True
        }
    except redis.ConnectionError:
        return {
            "embedding_entries": 0,
            "search_entries": 0,
            "total_entries": 0,
            "redis_connected": False
        }
