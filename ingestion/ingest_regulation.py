"""
Banking Regulation PDF Ingestion Pipeline

Ingests the reg_bancaire.pdf (568 pages) into Qdrant using:
- PyMuPDF (fitz) for PDF text extraction
- Chonkie for intelligent semantic chunking (text + tables)
- Ollama for dense embeddings
- FastEmbed for sparse embeddings

Usage:
    python ingestion/ingest_regulation.py
    python ingestion/ingest_regulation.py --dry-run   # Preview without uploading
    python ingestion/ingest_regulation.py --resume    # Resume interrupted ingestion

Requirements:
    - QDRANT_URL and QDRANT_API_KEY in .env file
    - Ollama running with mxbai-embed-large model
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF
import ollama
from chonkie import RecursiveChunker, TokenChunker
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException
from tqdm import tqdm

load_dotenv()

# --- Configuration ---
DATA_DIR = Path(__file__).parent.parent / "data"
PDF_FILE = DATA_DIR / "reg_bancaire.pdf"
COLLECTION_NAME = "regulations_v4"  # New collection with Qwen3 embeddings

# Dense Embedding (Ollama - local)
DENSE_MODEL = "qwen3-embedding:0.6b"  # 32K context, better multilingual
DENSE_DIM = 1024

# Sparse Embedding (FastEmbed BM42)
SPARSE_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"

# Chunking configuration - IMPROVED for regulatory content
CHUNK_SIZE = 768  # Larger chunks now that we have 32K context
MIN_CHARACTERS_PER_CHUNK = 200  # Higher minimum
MAX_EMBED_CHARS = 8000  # Safe limit for qwen3-embedding (32K tokens available)

# Target chunk size in characters for optimal retrieval
TARGET_CHUNK_CHARS = 600  # ~150 words, ~2-3 sentences
MAX_CHUNK_CHARS = 1200   # Upper limit

BATCH_SIZE = 25
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("Please set QDRANT_URL and QDRANT_API_KEY in your .env file")

print("Loading sparse embedding model...")
sparse_encoder = SparseTextEmbedding(model_name=SPARSE_MODEL)
print("✓ Sparse model loaded")

print("Initializing Chonkie SemanticChunker...")
try:
    from chonkie import SemanticChunker
    chunker = SemanticChunker(
        embedding_model="minishlab/potion-base-8M",  # Fast local embeddings
        chunk_size=CHUNK_SIZE,
        threshold=0.5,  # Similarity threshold for semantic boundaries
    )
    print("✓ Semantic chunker initialized")
except Exception as e:
    print(f"⚠️ SemanticChunker failed ({e}), falling back to RecursiveChunker")
    chunker = RecursiveChunker(
        chunk_size=CHUNK_SIZE,
        min_characters_per_chunk=MIN_CHARACTERS_PER_CHUNK,
    )
    print("✓ Fallback RecursiveChunker initialized")


# =============================================================================
# PDF EXTRACTION
# =============================================================================
def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """
    Extract text from PDF with page-level metadata.
    
    Returns list of dicts with:
        - page_number: int
        - text: str
        - has_tables: bool (detected by heuristics)
    """
    print(f"\nOpening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    pages = []
    
    for page_num in tqdm(range(len(doc)), desc="Extracting pages"):
        page = doc[page_num]
        text = page.get_text("text")
        
        # Heuristic: detect tables by looking for tab-separated or aligned content
        has_tables = bool(re.search(r'\t{2,}|\s{4,}\d', text))
        
        # Clean up text
        text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse multiple newlines
        text = text.strip()
        
        if text:  # Only include non-empty pages
            pages.append({
                "page_number": page_num + 1,  # 1-indexed
                "text": text,
                "has_tables": has_tables
            })
    
    doc.close()
    print(f"✓ Extracted {len(pages)} pages with content")
    return pages


def extract_article_reference(text: str) -> str | None:
    """
    Extract article/section reference from text.
    Improved patterns for Tunisian banking regulations.
    """
    patterns = [
        r'(Article\s+\d+[\.-]?\d*)',
        r'(Art\.\s*\d+[\.-]?\d*)',
        r'(Section\s+\d+[\.\d]*)',
        r'(Chapitre\s+\d+)',
        r'(Titre\s+[IVX]+)',
        r'(Circulaire\s+(?:aux\s+banques\s+)?n[°o]?\s*\d{2,4}[\-/]\d+)',
        r'(Note\s+(?:aux\s+(?:banques|établissements)\s+)?n[°o]?\s*\d+)',
        r'(Décret\s+n[°o]?\s*\d{4}[\-/]\d+)',
        r'(Loi\s+n[°o]?\s*\d{4}[\-/]\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_section_title(text: str) -> str | None:
    """
    Extract section title from the first line if it looks like a heading.
    """
    lines = text.strip().split('\n')
    if not lines:
        return None
    
    first_line = lines[0].strip()
    
    # Check if first line looks like a heading (short, possibly uppercase, no period at end)
    if (len(first_line) < 150 and 
        not first_line.endswith('.') and
        (first_line.isupper() or re.match(r'^(Article|Section|Chapitre|Titre)', first_line, re.IGNORECASE))):
        return first_line
    
    return None


# =============================================================================
# CHUNKING WITH CHONKIE
# =============================================================================
def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Chunk all pages using semantic chunking for better regulatory content segmentation.
    
    Returns list of chunks with metadata:
        - chunk_id: unique identifier
        - content: chunk text
        - page_number: source page
        - article_ref: extracted article reference
        - section_title: parent section heading
        - chunk_type: "text" or "table"
    """
    all_chunks = []
    chunk_counter = 0
    current_article_ref = None  # Track current article for context propagation
    current_section = None
    
    print(f"\nChunking {len(pages)} pages with semantic chunker...")
    
    for page in tqdm(pages, desc="Chunking"):
        page_num = page["page_number"]
        text = page["text"]
        has_tables = page["has_tables"]
        
        # Pre-process: add paragraph breaks at article boundaries
        text = re.sub(r'(Article\s+\d+)', r'\n\n\1', text)
        text = re.sub(r'(Circulaire\s+(?:aux\s+banques\s+)?n[°o]?)', r'\n\n\1', text)
        
        # Use Chonkie to chunk the page text
        try:
            chunks = chunker.chunk(text)
        except Exception as e:
            print(f"\n⚠️ Chunking error on page {page_num}: {e}")
            # Fallback: split by paragraphs
            paragraphs = text.split('\n\n')
            chunks = [type('Chunk', (), {'text': p.strip()}) for p in paragraphs if p.strip()]
        
        for chunk in chunks:
            chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
            chunk_text = chunk_text.strip()
            
            # Skip very short chunks
            if len(chunk_text) < MIN_CHARACTERS_PER_CHUNK:
                continue
            
            chunk_counter += 1
            
            # Generate unique chunk ID based on content hash
            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            chunk_id = f"REG-P{page_num:04d}-{chunk_counter:06d}-{content_hash}"
            
            # Extract metadata with context propagation
            article_ref = extract_article_reference(chunk_text)
            if article_ref:
                current_article_ref = article_ref
            
            section_title = extract_section_title(chunk_text)
            if section_title:
                current_section = section_title
            
            # Determine chunk type
            chunk_type = "table" if has_tables and re.search(r'\t|\|', chunk_text) else "text"
            
            all_chunks.append({
                "chunk_id": chunk_id,
                "content": chunk_text,
                "page_number": page_num,
                "article_ref": article_ref or current_article_ref,  # Use current if none found
                "section_title": section_title or current_section,
                "chunk_type": chunk_type,
                "char_count": len(chunk_text),
            })
    
    print(f"\n✓ Created {len(all_chunks)} chunks")
    
    # Stats
    char_lengths = [c["char_count"] for c in all_chunks]
    table_chunks = sum(1 for c in all_chunks if c["chunk_type"] == "table")
    with_article = sum(1 for c in all_chunks if c["article_ref"])
    
    print(f"  - Avg chunk size: {sum(char_lengths)/len(char_lengths):.0f} chars")
    print(f"  - Min: {min(char_lengths)}, Max: {max(char_lengths)} chars")
    print(f"  - Text chunks: {len(all_chunks) - table_chunks}")
    print(f"  - Table chunks: {table_chunks}")
    print(f"  - With article reference: {with_article} ({with_article/len(all_chunks):.0%})")
    
    return all_chunks


# =============================================================================
# EMBEDDING FUNCTIONS
# =============================================================================
def embed_dense(text: str) -> list[float]:
    """
    Generate dense embedding using local Ollama model.
    Truncates text to MAX_EMBED_CHARS to avoid context length errors.
    """
    # Always truncate to avoid exceeding model context length
    # mxbai-embed-large has 512 token limit (~1500 chars for French text)
    text = text[:MAX_EMBED_CHARS].strip()
    
    if not text:
        # Return zero vector for empty text
        return [0.0] * DENSE_DIM
    
    try:
        response = ollama.embed(model=DENSE_MODEL, input=text)
        return response["embeddings"][0]
    except Exception as e:
        print(f"\n⚠️ Embedding error: {e}")
        # Return zero vector on error
        return [0.0] * DENSE_DIM


def embed_sparse(text: str) -> tuple[list[int], list[float]]:
    """Generate sparse embedding using FastEmbed BM42."""
    embeddings = list(sparse_encoder.embed([text]))[0]
    indices = embeddings.indices.tolist()
    values = embeddings.values.tolist()
    return indices, values


# =============================================================================
# QDRANT COLLECTION CREATION
# =============================================================================
def create_regulations_collection(client: QdrantClient):
    """Create the regulations collection with dense + sparse vectors."""
    
    if client.collection_exists(COLLECTION_NAME):
        print(f"○ Collection exists: {COLLECTION_NAME}")
        return
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "content": models.VectorParams(
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
    
    # Create payload indexes for filtering
    indexed_fields = [
        ("page_number", models.PayloadSchemaType.INTEGER),
        ("article_ref", models.PayloadSchemaType.KEYWORD),
        ("section_title", models.PayloadSchemaType.KEYWORD),
        ("chunk_type", models.PayloadSchemaType.KEYWORD),
    ]
    
    for field_name, field_schema in indexed_fields:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=field_schema
        )
    
    print(f"✓ Created collection: {COLLECTION_NAME} (content + keywords vectors)")


# =============================================================================
# RETRY HELPER
# =============================================================================
def upsert_with_retry(client: QdrantClient, points: list, attempt: int = 1):
    """Upsert with retry logic and exponential backoff."""
    try:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
    except (ResponseHandlingException, Exception) as e:
        if attempt <= MAX_RETRIES:
            wait_time = RETRY_DELAY * (2 ** (attempt - 1))
            print(f"\n⚠️ Upload failed, retry {attempt}/{MAX_RETRIES} in {wait_time}s: {str(e)[:50]}...")
            time.sleep(wait_time)
            upsert_with_retry(client, points, attempt + 1)
        else:
            print(f"\n❌ Failed after {MAX_RETRIES} retries: {str(e)[:100]}")
            raise


# =============================================================================
# INGESTION
# =============================================================================
def ingest_chunks(
    client: QdrantClient,
    chunks: list[dict],
    resume: bool = False,
    dry_run: bool = False
):
    """Ingest chunks with dense + sparse vectors."""
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No data will be uploaded")
        print(f"  Would ingest {len(chunks)} chunks into {COLLECTION_NAME}")
        
        # Show sample chunks
        print("\n📄 Sample chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  --- Chunk {i+1} ---")
            print(f"  ID: {chunk['chunk_id']}")
            print(f"  Page: {chunk['page_number']}")
            print(f"  Article: {chunk['article_ref'] or 'N/A'}")
            print(f"  Type: {chunk['chunk_type']}")
            print(f"  Content preview: {chunk['content'][:150]}...")
        return
    
    # Check current count for resume
    current_count = client.count(COLLECTION_NAME).count
    
    if resume and current_count > 0:
        if current_count >= len(chunks):
            print(f"\n✓ {COLLECTION_NAME} already complete ({current_count} points)")
            return
        print(f"\n⏩ Resuming: {current_count}/{len(chunks)} already ingested")
        chunks = chunks[current_count:]
        start_id = current_count + 1
    else:
        start_id = 1
    
    print(f"\nIngesting {len(chunks)} chunks into {COLLECTION_NAME}...")
    
    points = []
    for i, chunk in enumerate(tqdm(chunks, desc=f"Processing chunks")):
        # Generate embeddings
        content_vec = embed_dense(chunk["content"])
        sparse_indices, sparse_values = embed_sparse(chunk["content"])
        
        point = models.PointStruct(
            id=start_id + i,
            vector={
                "content": content_vec,
                "keywords": models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                )
            },
            payload={
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "article_ref": chunk["article_ref"],
                "section_title": chunk["section_title"],
                "chunk_type": chunk["chunk_type"],
                "char_count": chunk["char_count"],
                "source": "reg_bancaire.pdf"
            }
        )
        points.append(point)
        
        if len(points) >= BATCH_SIZE:
            upsert_with_retry(client, points)
            points = []
    
    if points:
        upsert_with_retry(client, points)
    
    final_count = client.count(COLLECTION_NAME).count
    print(f"✓ Ingested {len(chunks)} chunks (total: {final_count})")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Ingest banking regulation PDF to Qdrant")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted ingestion")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Banking Regulation PDF Ingestion Pipeline")
    print("=" * 60)
    
    # Check PDF exists
    if not PDF_FILE.exists():
        print(f"\n❌ ERROR: PDF not found at {PDF_FILE}")
        print("Please ensure reg_bancaire.pdf is in the data/ directory.")
        return
    
    print(f"\n📄 PDF: {PDF_FILE}")
    print(f"📦 Target collection: {COLLECTION_NAME}")
    
    # Step 1: Extract pages from PDF
    pages = extract_pdf_pages(PDF_FILE)
    
    # Step 2: Chunk pages with Chonkie
    chunks = chunk_pages(pages)
    
    if args.dry_run:
        # Just show preview
        ingest_chunks(None, chunks, dry_run=True)
        return
    
    # Step 3: Connect to Qdrant
    print(f"\nConnecting to Qdrant: {QDRANT_URL[:40]}...")
    qdrant = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=120
    )
    print("✓ Connected to Qdrant Cloud")
    
    # Step 4: Create collection
    print("\n--- Creating Collection ---")
    create_regulations_collection(qdrant)
    
    # Step 5: Ingest chunks
    print("\n--- Ingesting Chunks ---")
    if args.resume:
        print("🔄 RESUME MODE: Skipping already-ingested chunks")
    
    ingest_chunks(qdrant, chunks, resume=args.resume)
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Total points: {qdrant.count(COLLECTION_NAME).count}")
    print(f"  Vectors: 'content' (dense) + 'keywords' (sparse)")
    print("\nRun a test query:")
    print(f"  python -c \"from tools.qdrant_retriever import hybrid_search; print(hybrid_search('{COLLECTION_NAME}', 'Article 5', limit=3))\"")


if __name__ == "__main__":
    main()
