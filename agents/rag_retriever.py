"""
RAG Retriever - Module de récupération hybride depuis Qdrant.
Utilise des vecteurs denses (Ollama) et sparse (SPLADE) pour la recherche.
"""

import ollama
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import (
    QDRANT_URL, QDRANT_API_KEY,
    DENSE_MODEL, SPARSE_MODEL,
    COLLECTIONS, TOP_K_SIMILAR, HYBRID_ALPHA
)

# Initialize sparse encoder (loaded once)
_sparse_encoder = None


def get_sparse_encoder():
    """Lazy load sparse encoder."""
    global _sparse_encoder
    if _sparse_encoder is None:
        _sparse_encoder = SparseTextEmbedding(model_name=SPARSE_MODEL)
    return _sparse_encoder


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client with extended timeout."""
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=60
    )


def embed_dense(text: str) -> list[float]:
    """Generate dense embedding using Ollama."""
    response = ollama.embed(model=DENSE_MODEL, input=text)
    return response["embeddings"][0]


def embed_sparse(text: str) -> tuple[list[int], list[float]]:
    """Generate sparse embedding using FastEmbed SPLADE."""
    encoder = get_sparse_encoder()
    embeddings = list(encoder.embed([text]))[0]
    return embeddings.indices.tolist(), embeddings.values.tolist()


# =============================================================================
# TEXT SERIALIZATION FOR QUERIES
# =============================================================================
def client_to_structured_query(data: dict) -> str:
    """Convert client data to structured query text."""
    return f"""Financial Profile:
Income: €{data.get('income_annual', 0):,.0f} annual
Debt-to-Income: {data.get('debt_to_income_ratio', 0)*100:.1f}%
Missed Payments: {data.get('missed_payments_last_12m', 0)}
Age: {data.get('age', 0)} years
Job Tenure: {data.get('job_tenure_years', 0)} years"""


def client_to_narrative_query(data: dict) -> str:
    """Convert client data to narrative query text."""
    return f"""Employment: {data.get('contract_type', 'Unknown')} contract
Loan Purpose: {data.get('loan_purpose', 'Unknown')}
Credit History: {data.get('credit_history', 'No history available')}"""


def startup_to_structured_query(data: dict) -> str:
    """Convert startup data to structured query text."""
    return f"""Financial Profile:
ARR: ${data.get('arr_current', 0):,.0f}
ARR Growth: {data.get('arr_growth_yoy', 0)*100:.0f}%
Burn Rate: ${data.get('burn_rate_monthly', 0):,.0f}/month
Runway: {data.get('runway_months', 0):.1f} months
Burn Multiple: {data.get('burn_multiple', 0):.2f}
Founder Experience: {data.get('founder_experience_years', 0)} years"""


def startup_to_narrative_query(data: dict) -> str:
    """Convert startup data to narrative query text."""
    vc = "Yes, venture capital backed" if data.get('vc_backing') else "Bootstrapped, no VC funding"
    return f"""Sector: {data.get('sector', 'Unknown')}
VC Backed: {vc}
Pitch: {data.get('pitch_narrative', 'No pitch available')}"""


def enterprise_to_structured_query(data: dict) -> str:
    """Convert enterprise data to structured query text."""
    return f"""Financial Profile:
Revenue: €{data.get('revenue_annual', 0):,.0f}
Profit Margin: {data.get('net_profit_margin', 0)*100:.1f}%
Current Ratio: {data.get('current_ratio', 0):.2f}
Quick Ratio: {data.get('quick_ratio', 0):.2f}
Debt-to-Equity: {data.get('debt_to_equity', 0):.2f}
Altman Z-Score: {data.get('altman_z_score', 0):.2f}"""


def enterprise_to_narrative_query(data: dict) -> str:
    """Convert enterprise data to narrative query text."""
    return f"""Industry: {data.get('industry_code', 'Unknown')}
CEO: {data.get('ceo_name', 'Unknown')} with {data.get('ceo_experience_years', 0)} years experience
CEO Track Record: {data.get('ceo_track_record', 'Unknown')}
Risk Assessment: {data.get('annual_report_risk_section', 'No assessment available')}"""


# =============================================================================
# HYBRID SEARCH
# =============================================================================
def hybrid_search(
    collection_name: str,
    structured_query: str,
    narrative_query: str,
    top_k: int = TOP_K_SIMILAR,
    filters: dict = None
) -> list[dict]:
    """
    Perform hybrid search combining structured + narrative + sparse vectors.
    Uses Reciprocal Rank Fusion (RRF) for result merging.
    """
    client = get_qdrant_client()
    
    # Generate embeddings
    structured_vec = embed_dense(structured_query)
    narrative_vec = embed_dense(narrative_query)
    
    # Combine queries for sparse
    combined_text = f"{structured_query} {narrative_query}"
    sparse_indices, sparse_values = embed_sparse(combined_text)
    
    # Build filter if provided
    query_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(models.FieldCondition(
                    key=key,
                    match=models.MatchAny(any=value)
                ))
            else:
                conditions.append(models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                ))
        query_filter = models.Filter(must=conditions)
    
    # Perform prefetch queries for RRF fusion
    results = client.query_points(
        collection_name=collection_name,
        prefetch=[
            models.Prefetch(
                query=structured_vec,
                using="structured",
                limit=top_k * 2
            ),
            models.Prefetch(
                query=narrative_vec,
                using="narrative",
                limit=top_k * 2
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                ),
                using="keywords",
                limit=top_k * 2
            )
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=query_filter,
        limit=top_k,
        with_payload=True
    )
    
    # Format results
    similar_cases = []
    for point in results.points:
        similar_cases.append({
            "id": point.id,
            "score": point.score,
            "payload": point.payload
        })
    
    return similar_cases


def retrieve_similar_cases(
    application_type: str,
    application_data: dict,
    top_k: int = TOP_K_SIMILAR
) -> list[dict]:
    """
    Main retrieval function - dispatches to correct collection and query builder.
    """
    if application_type == "client":
        collection = COLLECTIONS["clients"]
        structured_query = client_to_structured_query(application_data)
        narrative_query = client_to_narrative_query(application_data)
    elif application_type == "startup":
        collection = COLLECTIONS["startups"]
        structured_query = startup_to_structured_query(application_data)
        narrative_query = startup_to_narrative_query(application_data)
    elif application_type == "enterprise":
        collection = COLLECTIONS["enterprises"]
        structured_query = enterprise_to_structured_query(application_data)
        narrative_query = enterprise_to_narrative_query(application_data)
    else:
        raise ValueError(f"Unknown application type: {application_type}")
    
    return hybrid_search(
        collection_name=collection,
        structured_query=structured_query,
        narrative_query=narrative_query,
        top_k=top_k
    )


def retrieve_by_outcome(
    application_type: str,
    application_data: dict,
    outcome: str,
    top_k: int = 3
) -> list[dict]:
    """
    Retrieve similar cases filtered by specific outcome.
    Useful for finding similar APPROVED or REJECTED cases.
    """
    if application_type == "client":
        collection = COLLECTIONS["clients"]
        structured_query = client_to_structured_query(application_data)
        narrative_query = client_to_narrative_query(application_data)
    elif application_type == "startup":
        collection = COLLECTIONS["startups"]
        structured_query = startup_to_structured_query(application_data)
        narrative_query = startup_to_narrative_query(application_data)
    elif application_type == "enterprise":
        collection = COLLECTIONS["enterprises"]
        structured_query = enterprise_to_structured_query(application_data)
        narrative_query = enterprise_to_narrative_query(application_data)
    else:
        raise ValueError(f"Unknown application type: {application_type}")
    
    return hybrid_search(
        collection_name=collection,
        structured_query=structured_query,
        narrative_query=narrative_query,
        top_k=top_k,
        filters={"outcome": outcome}
    )


# =============================================================================
# TEST CONNECTION
# =============================================================================
def test_connection():
    """Test Qdrant connection and collections."""
    client = get_qdrant_client()
    print("✓ Connected to Qdrant")
    
    for name, collection in COLLECTIONS.items():
        try:
            count = client.count(collection).count
            print(f"  {collection}: {count} points")
        except Exception as e:
            print(f"  {collection}: ERROR - {e}")
    
    return True


if __name__ == "__main__":
    test_connection()
