"""
Regulation Agent Evaluation Dataset Generator

Generates high-quality Q&A pairs for evaluating the banking regulation RAG system.
Uses GPT-4o for generation to ensure quality, avoiding wasted inference on poor data.

Features:
- Stratified sampling from PDF chunks to cover full document
- Query type categorization (single-lookup, cross-reference, multi-hop, etc.)
- Human-readable ground truth with page/article citations
- Difficulty gradation

Usage:
    python evaluation/generate_regulation_eval.py
    python evaluation/generate_regulation_eval.py --dry-run     # Preview without LLM calls
    python evaluation/generate_regulation_eval.py --limit 20    # Generate fewer pairs for testing
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

# Paths
EVAL_DIR = Path(__file__).parent
OUTPUT_FILE = EVAL_DIR / "regulation_golden_qa.json"

# Qdrant connection for sampling chunks
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "regulations_v4"

# OpenAI for generation
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GENERATION_MODEL = "gpt-4o-mini"  # Cost-effective, with strict quality validation

# Target distribution (scaled for 30 pairs default)
TARGET_DISTRIBUTION = {
    "single_lookup": 20,       # "What does Article X say about Y?"
    "definition": 15,          # "What is the definition of X?"
    "cross_reference": 15,     # "Which articles reference X?"
    "multi_hop": 15,           # "What are ALL requirements for X?"
    "procedural": 10,          # "How does process X work?"
    "comparative": 5,          # "How does X differ from Y?"
    "temporal": 5,             # "When was X modified?"
}


# =============================================================================
# CHUNK SAMPLING
# =============================================================================
def get_sample_chunks(limit: int = 200) -> list[dict]:
    """
    Sample diverse chunks from Qdrant regulations collection.
    Stratifies by page number to ensure coverage across document.
    """
    from qdrant_client import QdrantClient
    
    print(f"Connecting to Qdrant: {QDRANT_URL[:40]}...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    
    # Get total count
    total_count = qdrant.count(COLLECTION_NAME).count
    print(f"✓ Collection has {total_count} chunks")
    
    # Scroll through collection to get representative samples
    chunks = []
    offset = None
    
    while len(chunks) < limit:
        results, offset = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            limit=50,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        for point in results:
            payload = point.payload
            chunks.append({
                "id": point.id,
                "chunk_id": payload.get("chunk_id", ""),
                "content": payload.get("content", ""),
                "page_number": payload.get("page_number", 0),
                "article_ref": payload.get("article_ref"),
                "section_title": payload.get("section_title"),
                "chunk_type": payload.get("chunk_type", "text"),
            })
        
        if offset is None:
            break
    
    print(f"✓ Retrieved {len(chunks)} chunks")
    
    # Stratified sampling by page ranges
    # Divide document into sections and sample from each
    page_ranges = [
        (1, 100),
        (101, 200),
        (201, 300),
        (301, 400),
        (401, 500),
        (501, 600),
    ]
    
    sampled = []
    # Need ~3x chunks for generation failures + validation rejections
    per_range = max(15, (limit * 4) // len(page_ranges))
    
    for start, end in page_ranges:
        range_chunks = [c for c in chunks if start <= c["page_number"] <= end]
        # Prioritize chunks with article references
        with_article = [c for c in range_chunks if c.get("article_ref")]
        without_article = [c for c in range_chunks if not c.get("article_ref")]
        
        # Take 70% from chunks with articles, 30% without
        n_with = min(int(per_range * 0.7), len(with_article))
        n_without = min(per_range - n_with, len(without_article))
        
        sampled.extend(random.sample(with_article, n_with) if n_with > 0 else [])
        sampled.extend(random.sample(without_article, n_without) if n_without > 0 else [])
    
    random.shuffle(sampled)
    final_sample = sampled[:limit * 4]  # 4x for generation failures
    print(f"✓ Stratified sample: {len(final_sample)} chunks covering {len(page_ranges)} page ranges")
    
    return final_sample


# =============================================================================
# Q&A GENERATION PROMPTS
# =============================================================================
SYSTEM_PROMPT = """Tu es un expert en réglementation bancaire tunisienne (BCT).

Ta tâche est de générer des paires Question-Réponse de haute qualité pour évaluer un système RAG.

Règles STRICTES:
1. La question doit être NATURELLE - comme un vrai utilisateur la poserait
2. La réponse doit être ENTIÈREMENT basée sur le texte fourni - pas d'hallucination
3. Inclure les CITATIONS précises: numéro de page, article, section
4. Varier le style de question (formel, conversationnel, technique)
5. Si le texte ne permet pas de générer une bonne question, retourner null

Format JSON requis:
{
    "question": "La question naturelle en français",
    "answer": "La réponse détaillée avec citations [Page X, Article Y]",
    "citations": [
        {"page": 42, "article": "Article 5", "excerpt": "Texte pertinent..."}
    ],
    "query_type": "single_lookup|definition|cross_reference|multi_hop|procedural|comparative|temporal",
    "difficulty": "easy|medium|hard",
    "reasoning": "Pourquoi cette paire est utile pour l'évaluation"
}

Si impossible de générer une bonne question, retourne: {"skip": true, "reason": "..."}"""


def generate_qa_for_chunk(
    chunk: dict,
    target_type: str,
    existing_questions: set[str]
) -> dict | None:
    """
    Generate a Q&A pair for a single chunk using GPT-4o.
    
    Args:
        chunk: The regulation chunk with content and metadata
        target_type: The type of query to generate
        existing_questions: Set of already generated questions to avoid duplicates
    
    Returns:
        Generated Q&A dict or None if generation failed/skipped
    """
    type_instructions = {
        "single_lookup": "Génère une question sur un POINT SPÉCIFIQUE mentionné dans le texte (définition, règle, exigence).",
        "definition": "Génère une question demandant la DÉFINITION d'un terme technique ou concept mentionné.",
        "cross_reference": "Génère une question sur les LIENS avec d'autres articles/sections (si mentionnés dans le texte).",
        "multi_hop": "Génère une question COMPLEXE nécessitant de synthétiser plusieurs informations.",
        "procedural": "Génère une question sur une PROCÉDURE ou un PROCESSUS décrit.",
        "comparative": "Génère une question COMPARANT deux concepts ou exigences (si applicable).",
        "temporal": "Génère une question sur les DÉLAIS, dates ou modifications temporelles (si applicable).",
    }
    
    user_prompt = f"""Texte source (Page {chunk['page_number']}):
---
{chunk['content'][:2000]}
---

Métadonnées:
- Article: {chunk.get('article_ref') or 'Non spécifié'}
- Section: {chunk.get('section_title') or 'Non spécifiée'}
- Type: {chunk.get('chunk_type', 'text')}

Instructions spécifiques:
{type_instructions.get(target_type, type_instructions['single_lookup'])}

Questions déjà générées (ÉVITER les doublons):
{list(existing_questions)[-5:]}

Génère UNE paire Question-Réponse de type '{target_type}' en JSON."""

    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,  # Some creativity for diverse questions
            max_tokens=1000,
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Check if skipped
        if result.get("skip"):
            return None
        
        # Validate required fields
        if not result.get("question") or not result.get("answer"):
            return None
        
        # Check for duplicate question
        if result["question"] in existing_questions:
            return None
        
        # Add source metadata
        result["source_chunk_id"] = chunk["chunk_id"]
        result["source_page"] = chunk["page_number"]
        result["source_article"] = chunk.get("article_ref")
        
        return result
        
    except Exception as e:
        print(f"⚠️ Generation error: {e}")
        return None


# =============================================================================
# BATCH GENERATION WITH QUALITY CHECKS
# =============================================================================
def generate_evaluation_dataset(
    target_count: int = 80,
    dry_run: bool = False
) -> list[dict]:
    """
    Generate the full evaluation dataset with stratified query types.
    """
    # Calculate per-type targets
    total_weight = sum(TARGET_DISTRIBUTION.values())
    type_targets = {
        qtype: max(1, int((weight / total_weight) * target_count))
        for qtype, weight in TARGET_DISTRIBUTION.items()
    }
    
    print(f"\n📊 Target distribution ({target_count} total):")
    for qtype, target in type_targets.items():
        print(f"   {qtype}: {target}")
    
    # Get sample chunks
    chunks = get_sample_chunks(limit=target_count * 3)  # 3x for failures
    
    if dry_run:
        print("\n🔍 DRY RUN - Sample chunks:")
        for chunk in chunks[:5]:
            print(f"\n  Page {chunk['page_number']} | {chunk.get('article_ref', 'No article')}")
            print(f"  {chunk['content'][:200]}...")
        return []
    
    # Generate Q&A pairs
    generated = []
    existing_questions = set()
    type_counts = {qtype: 0 for qtype in TARGET_DISTRIBUTION}
    
    print(f"\n🤖 Generating Q&A pairs using {GENERATION_MODEL}...")
    
    # Shuffle chunks and iterate
    random.shuffle(chunks)
    chunk_index = 0
    
    with tqdm(total=target_count, desc="Generating") as pbar:
        while len(generated) < target_count and chunk_index < len(chunks):
            chunk = chunks[chunk_index]
            chunk_index += 1
            
            # Determine which type to generate (pick underrepresented)
            needed_types = [
                qtype for qtype, count in type_counts.items()
                if count < type_targets[qtype]
            ]
            
            if not needed_types:
                break
            
            target_type = random.choice(needed_types)
            
            # Generate
            qa = generate_qa_for_chunk(chunk, target_type, existing_questions)
            
            if qa:
                qa["query_type"] = target_type  # Ensure type is set
                generated.append(qa)
                existing_questions.add(qa["question"])
                type_counts[target_type] = type_counts.get(target_type, 0) + 1
                pbar.update(1)
    
    # Summary
    print(f"\n✓ Generated {len(generated)} Q&A pairs")
    print("\nActual distribution:")
    for qtype, count in type_counts.items():
        target = type_targets[qtype]
        status = "✓" if count >= target else "⚠️"
        print(f"  {status} {qtype}: {count}/{target}")
    
    return generated


def validate_dataset(dataset: list[dict]) -> list[dict]:
    """
    Post-generation validation and cleanup with STRICT quality checks.
    Critical for GPT-4o-mini to ensure we don't waste evaluation on poor data.
    """
    valid = []
    rejected_reasons = {}
    
    for qa in dataset:
        # Check required fields
        if not qa.get("question") or not qa.get("answer"):
            rejected_reasons["missing_fields"] = rejected_reasons.get("missing_fields", 0) + 1
            continue
        
        question = qa["question"]
        answer = qa["answer"]
        
        # STRICT: Answer must be substantive (at least 100 chars for regulatory content)
        if len(answer) < 100:
            rejected_reasons["short_answer"] = rejected_reasons.get("short_answer", 0) + 1
            continue
        
        # STRICT: Question must be meaningful (at least 30 chars)
        if len(question) < 30:
            rejected_reasons["short_question"] = rejected_reasons.get("short_question", 0) + 1
            continue
        
        # STRICT: Must have citations (regulatory content needs references)
        citations = qa.get("citations", [])
        if not citations or len(citations) == 0:
            rejected_reasons["no_citations"] = rejected_reasons.get("no_citations", 0) + 1
            continue
        
        # STRICT: Answer must contain a page or article reference
        if "page" not in answer.lower() and "article" not in answer.lower():
            rejected_reasons["no_refs_in_answer"] = rejected_reasons.get("no_refs_in_answer", 0) + 1
            continue
        
        # STRICT: Question should not be too generic
        generic_starts = ["what is", "qu'est-ce que", "define", "explain"]
        is_too_generic = any(question.lower().startswith(g) for g in generic_starts) and len(question) < 50
        if is_too_generic:
            rejected_reasons["too_generic"] = rejected_reasons.get("too_generic", 0) + 1
            continue
        
        valid.append(qa)
    
    print(f"✓ Validated: {len(valid)}/{len(dataset)} pairs passed")
    if rejected_reasons:
        print(f"  Rejected reasons: {rejected_reasons}")
    return valid


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Generate regulation evaluation dataset")
    parser.add_argument("--limit", type=int, default=30, help="Number of Q&A pairs to generate")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Output file path")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Regulation Agent Evaluation Dataset Generator")
    print("=" * 60)
    
    # Generate dataset
    dataset = generate_evaluation_dataset(
        target_count=args.limit,
        dry_run=args.dry_run
    )
    
    if args.dry_run:
        print("\n✓ Dry run complete")
        return
    
    # Validate
    dataset = validate_dataset(dataset)
    
    # Save
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved {len(dataset)} Q&A pairs to {output_path}")
    
    # Show samples
    print("\n📄 Sample Q&A pairs:")
    for i, qa in enumerate(dataset[:3]):
        print(f"\n--- Sample {i+1} ({qa.get('query_type', 'unknown')}, {qa.get('difficulty', 'unknown')}) ---")
        print(f"Q: {qa['question']}")
        print(f"A: {qa['answer'][:200]}...")


if __name__ == "__main__":
    main()
