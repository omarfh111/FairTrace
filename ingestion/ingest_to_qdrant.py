"""
Credit Decision Memory - Qdrant Ingestion Pipeline (V2 - Production Grade)

Features:
- Named Vectors: 'structured' (financial metrics) + 'narrative' (text descriptions)
- Sparse Vectors: SPLADE for keyword matching
- Hybrid Search Ready: RRF fusion at query time
- Retry logic with exponential backoff
- Resume capability (skips already ingested data)
- Increased timeout for cloud uploads

Usage:
    python ingestion/ingest_to_qdrant.py
    python ingestion/ingest_to_qdrant.py --resume   # Resume interrupted ingestion

Requirements:
    - QDRANT_URL and QDRANT_API_KEY in .env file
    - Ollama running with mxbai-embed-large model
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import ollama
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException
from tqdm import tqdm

load_dotenv()

# --- Configuration ---
DATA_DIR = Path(__file__).parent.parent / "data_generation" / "output"

# Dense Embedding (Ollama - local)
DENSE_MODEL = "mxbai-embed-large"
DENSE_DIM = 1024

# Sparse Embedding (FastEmbed SPLADE - local)
SPARSE_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"

BATCH_SIZE = 25  # Reduced for stability
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("Please set QDRANT_URL and QDRANT_API_KEY in your .env file")

print("Loading sparse embedding model...")
sparse_encoder = SparseTextEmbedding(model_name=SPARSE_MODEL)
print("✓ Sparse model loaded")


# =============================================================================
# EMBEDDING FUNCTIONS
# =============================================================================
def embed_dense(text: str) -> list[float]:
    """Generate dense embedding using local Ollama model."""
    response = ollama.embed(model=DENSE_MODEL, input=text)
    return response["embeddings"][0]


def embed_sparse(text: str) -> tuple[list[int], list[float]]:
    """Generate sparse embedding using FastEmbed SPLADE."""
    embeddings = list(sparse_encoder.embed([text]))[0]
    indices = embeddings.indices.tolist()
    values = embeddings.values.tolist()
    return indices, values


# =============================================================================
# TEXT SERIALIZATION - STRUCTURED (Numbers Only)
# =============================================================================
def client_structured_text(record: dict) -> str:
    """Convert client financial metrics to structured text."""
    payslip = record.get("payslip_structure", {})
    return f"""Financial Profile:
Income: €{record['income_annual']:,.0f} annual
Net Monthly: €{payslip.get('net_monthly', 0):,.0f}
Basic Salary: €{payslip.get('basic_part', 0):,.0f}
Variable Pay: €{payslip.get('variable_part', 0):,.0f}
Debt-to-Income: {record['debt_to_income_ratio']*100:.1f}%
Missed Payments: {record['missed_payments_last_12m']}
Age: {record['age']} years
Job Tenure: {record['job_tenure_years']} years"""


def startup_structured_text(record: dict) -> str:
    """Convert startup financial metrics to structured text."""
    return f"""Financial Profile:
ARR: ${record['arr_current']:,.0f}
ARR Growth: {record['arr_growth_yoy']*100:.0f}%
Burn Rate: ${record['burn_rate_monthly']:,.0f}/month
Runway: {record['runway_months']:.1f} months
CAC/LTV Ratio: {record['cac_ltv_ratio']:.2f}
Churn Rate: {record['churn_rate_monthly']*100:.2f}%
Burn Multiple: {record['burn_multiple']:.2f}
Founder Experience: {record['founder_experience_years']} years"""


def enterprise_structured_text(record: dict) -> str:
    """Convert enterprise financial metrics to structured text."""
    bilan = record.get("financials_bilan", {})
    assets = bilan.get("assets", {})
    liabilities = bilan.get("liabilities", {})
    
    return f"""Financial Profile:
Revenue: €{record['revenue_annual']:,.0f}
Profit Margin: {record['net_profit_margin']*100:.1f}%
Total Assets: €{assets.get('total_assets', 0):,.0f}
Current Assets: €{assets.get('current_assets', 0):,.0f}
Total Liabilities: €{liabilities.get('total_liabilities', 0):,.0f}
Current Ratio: {record['current_ratio']:.2f}
Quick Ratio: {record['quick_ratio']:.2f}
Debt-to-Equity: {record['debt_to_equity']:.2f}
Interest Coverage: {record['interest_coverage_ratio']:.2f}
Altman Z-Score: {record['altman_z_score']:.2f}"""


# =============================================================================
# TEXT SERIALIZATION - NARRATIVE (Text Only)
# =============================================================================
def client_narrative_text(record: dict) -> str:
    """Convert client narrative fields to text."""
    return f"""Employment: {record.get('contract_type', 'Unknown')} contract
Loan Purpose: {record['loan_purpose']}
Credit History: {record.get('credit_history', 'No history available')}
Outcome: {record['outcome']}"""


def startup_narrative_text(record: dict) -> str:
    """Convert startup narrative fields to text."""
    return f"""Sector: {record['sector']}
VC Backed: {'Yes, venture capital backed' if record['vc_backing'] else 'Bootstrapped, no VC funding'}
Pitch: {record.get('pitch_narrative', 'No pitch available')}
Outcome: {record['outcome']}"""


def enterprise_narrative_text(record: dict) -> str:
    """Convert enterprise narrative fields to text."""
    ceo = record.get("ceo_profile", {})
    z_zone = 'Safe Zone' if record['altman_z_score'] > 3 else 'Grey Zone' if record['altman_z_score'] > 1.8 else 'Distress Zone'
    
    return f"""Industry: {record['industry_code']}
CEO: {ceo.get('name', 'Unknown')} with {ceo.get('experience_years', 0)} years experience
CEO Background: {ceo.get('resume_summary', 'No background available')}
CEO Track Record: {ceo.get('track_record', 'Unknown')}
Altman Zone: {z_zone}
ESG Risk: {record['esg_risk_score']:.1f}/100
Active Lawsuits: {record['legal_lawsuits_active']}
Risk Assessment: {record.get('annual_report_risk_section', 'No assessment available')}
Outcome: {record['outcome']}"""


# =============================================================================
# FULL TEXT FOR SPARSE (Keywords)
# =============================================================================
def client_full_text(record: dict) -> str:
    """Full text for sparse keyword matching."""
    return f"{record.get('contract_type', '')} {record['loan_purpose']} {record['outcome']} {record.get('credit_history', '')}"


def startup_full_text(record: dict) -> str:
    """Full text for sparse keyword matching."""
    vc = "VC backed venture capital" if record['vc_backing'] else "bootstrapped no VC"
    return f"{record['sector']} {vc} {record['outcome']} {record.get('pitch_narrative', '')}"


def enterprise_full_text(record: dict) -> str:
    """Full text for sparse keyword matching."""
    ceo = record.get("ceo_profile", {})
    return f"{record['industry_code']} {ceo.get('name', '')} {ceo.get('track_record', '')} {record['outcome']} {record.get('annual_report_risk_section', '')}"


# =============================================================================
# COLLECTION CREATION (Named Vectors + Sparse)
# =============================================================================
def create_collection_with_named_vectors(client: QdrantClient, name: str, indexed_fields: list[tuple[str, str]]):
    """Create a collection with named vectors (structured + narrative) and sparse vector."""
    
    if client.collection_exists(name):
        print(f"○ Collection exists: {name}")
        return
    
    client.create_collection(
        collection_name=name,
        vectors_config={
            "structured": models.VectorParams(
                size=DENSE_DIM,
                distance=models.Distance.COSINE
            ),
            "narrative": models.VectorParams(
                size=DENSE_DIM,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "keywords": models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        }
    )
    
    for field_name, field_type in indexed_fields:
        schema = {
            "keyword": models.PayloadSchemaType.KEYWORD,
            "float": models.PayloadSchemaType.FLOAT,
            "integer": models.PayloadSchemaType.INTEGER,
            "bool": models.PayloadSchemaType.BOOL
        }.get(field_type, models.PayloadSchemaType.KEYWORD)
        
        client.create_payload_index(
            collection_name=name,
            field_name=field_name,
            field_schema=schema
        )
    
    print(f"✓ Created collection: {name} (structured + narrative + keywords)")


def create_all_collections(client: QdrantClient):
    """Create all collections with proper configuration."""
    
    create_collection_with_named_vectors(
        client, "clients_v2",
        indexed_fields=[
            ("outcome", "keyword"),
            ("contract_type", "keyword"),
            ("split", "keyword"),
            ("debt_to_income_ratio", "float"),
            ("missed_payments_last_12m", "integer")
        ]
    )
    
    create_collection_with_named_vectors(
        client, "startups_v2",
        indexed_fields=[
            ("outcome", "keyword"),
            ("sector", "keyword"),
            ("split", "keyword"),
            ("vc_backing", "bool"),
            ("runway_months", "float"),
            ("burn_multiple", "float")
        ]
    )
    
    create_collection_with_named_vectors(
        client, "enterprises_v2",
        indexed_fields=[
            ("outcome", "keyword"),
            ("industry_code", "keyword"),
            ("split", "keyword"),
            ("altman_z_score", "float"),
            ("legal_lawsuits_active", "integer")
        ]
    )


# =============================================================================
# RETRY HELPER
# =============================================================================
def upsert_with_retry(client: QdrantClient, collection_name: str, points: list, attempt: int = 1):
    """Upsert with retry logic and exponential backoff."""
    try:
        client.upsert(collection_name=collection_name, points=points)
    except (ResponseHandlingException, Exception) as e:
        if attempt <= MAX_RETRIES:
            wait_time = RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
            print(f"\n⚠️ Upload failed, retry {attempt}/{MAX_RETRIES} in {wait_time}s: {str(e)[:50]}...")
            time.sleep(wait_time)
            upsert_with_retry(client, collection_name, points, attempt + 1)
        else:
            print(f"\n❌ Failed after {MAX_RETRIES} retries: {str(e)[:100]}")
            raise


# =============================================================================
# INGESTION WITH RESUME
# =============================================================================
def ingest_collection(
    client: QdrantClient,
    collection_name: str,
    records: list[dict],
    structured_fn,
    narrative_fn,
    keywords_fn,
    resume: bool = False
):
    """Ingest records with named vectors + sparse vectors. Supports resume."""
    
    # Check current count for resume
    current_count = client.count(collection_name).count
    
    if resume and current_count > 0:
        if current_count >= len(records):
            print(f"\n✓ {collection_name} already complete ({current_count} points)")
            return
        print(f"\n⏩ Resuming {collection_name}: {current_count}/{len(records)} already ingested")
        records = records[current_count:]
        start_id = current_count + 1
    else:
        start_id = 1
    
    print(f"\nIngesting {len(records)} records into {collection_name}...")
    
    points = []
    for i, record in enumerate(tqdm(records, desc=f"Processing {collection_name}")):
        structured_text = structured_fn(record)
        narrative_text = narrative_fn(record)
        keywords_text = keywords_fn(record)
        
        structured_vec = embed_dense(structured_text)
        narrative_vec = embed_dense(narrative_text)
        sparse_indices, sparse_values = embed_sparse(keywords_text)
        
        point = models.PointStruct(
            id=start_id + i,
            vector={
                "structured": structured_vec,
                "narrative": narrative_vec,
                "keywords": models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                )
            },
            payload=record
        )
        points.append(point)
        
        if len(points) >= BATCH_SIZE:
            upsert_with_retry(client, collection_name, points)
            points = []
    
    if points:
        upsert_with_retry(client, collection_name, points)
    
    final_count = client.count(collection_name).count
    print(f"✓ Ingested {len(records)} records into {collection_name} (total: {final_count})")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Ingest data to Qdrant")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted ingestion")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Credit Decision Memory - Qdrant Ingestion (V2 - Hybrid)")
    print("=" * 60)
    
    print(f"\nConnecting to Qdrant: {QDRANT_URL[:40]}...")
    # Increased timeout: 120 seconds
    qdrant = QdrantClient(
        url=QDRANT_URL, 
        api_key=QDRANT_API_KEY,
        timeout=120  # 120 seconds instead of default 10
    )
    print("✓ Connected to Qdrant Cloud")
    
    print("\n--- Creating Collections (Named Vectors + Sparse) ---")
    create_all_collections(qdrant)
    
    print("\n--- Loading Data ---")
    clients_path = DATA_DIR / "clients.json"
    startups_path = DATA_DIR / "startups.json"
    enterprises_path = DATA_DIR / "enterprises.json"
    
    if not clients_path.exists():
        print(f"ERROR: Data not found at {DATA_DIR}")
        print("Run 'python data_generation/generate_data.py' first.")
        return
    
    with open(clients_path) as f:
        clients = json.load(f)
    with open(startups_path) as f:
        startups = json.load(f)
    with open(enterprises_path) as f:
        enterprises = json.load(f)
    
    print(f"  Loaded {len(clients)} clients")
    print(f"  Loaded {len(startups)} startups")
    print(f"  Loaded {len(enterprises)} enterprises")
    
    if args.resume:
        print("\n🔄 RESUME MODE: Skipping already-ingested data")
    
    print("\n--- Ingesting Data (Named + Sparse Vectors) ---")
    ingest_collection(
        qdrant, "clients_v2", clients,
        client_structured_text, client_narrative_text, client_full_text,
        resume=args.resume
    )
    ingest_collection(
        qdrant, "startups_v2", startups,
        startup_structured_text, startup_narrative_text, startup_full_text,
        resume=args.resume
    )
    ingest_collection(
        qdrant, "enterprises_v2", enterprises,
        enterprise_structured_text, enterprise_narrative_text, enterprise_full_text,
        resume=args.resume
    )
    
    print("\n" + "=" * 60)
    print("✓ INGESTION COMPLETE (Hybrid Search Ready)")
    print("=" * 60)
    print(f"  clients_v2: {qdrant.count('clients_v2').count} points")
    print(f"  startups_v2: {qdrant.count('startups_v2').count} points")
    print(f"  enterprises_v2: {qdrant.count('enterprises_v2').count} points")
    print("\nEach point has 3 vectors: 'structured', 'narrative', 'keywords'")


if __name__ == "__main__":
    main()
