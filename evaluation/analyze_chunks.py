"""
Chunking Strategy Diagnostic Tool

Analyzes the quality of chunks in Qdrant to determine if the chunking strategy
is production-grade.

Metrics evaluated:
1. Chunk size distribution (tokens, characters)
2. Semantic coherence (does chunk contain complete thoughts?)
3. Boundary quality (are chunks cut mid-sentence?)
4. Context preservation (do chunks have enough context?)
5. Article/section coverage (are regulatory structures preserved?)

Usage:
    python evaluation/analyze_chunks.py
    python evaluation/analyze_chunks.py --sample 100
    python evaluation/analyze_chunks.py --verbose
"""

import argparse
import json
import os
import sys
import random
import re
from pathlib import Path
from collections import Counter
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

# Paths
EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "metrics"
RESULTS_DIR.mkdir(exist_ok=True)

# Thresholds for production-grade chunking
THRESHOLDS = {
    "min_chunk_chars": 100,          # Chunks should have at least 100 chars
    "max_chunk_chars": 2000,         # Chunks shouldn't exceed 2000 chars  
    "ideal_chunk_chars_min": 300,    # Ideal range: 300-1000 chars
    "ideal_chunk_chars_max": 1000,
    "max_truncation_rate": 0.15,     # Max 15% of chunks cut mid-sentence
    "min_article_coverage": 0.70,    # At least 70% chunks should have article refs
    "max_orphan_rate": 0.10,         # Max 10% chunks with no context
}


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url or not api_key:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")
    return QdrantClient(url=url, api_key=api_key, timeout=120)


def sample_chunks(client: QdrantClient, collection: str, sample_size: int) -> list[dict]:
    """Sample random chunks from collection."""
    # Get total count
    info = client.get_collection(collection)
    total = info.points_count
    
    print(f"Collection '{collection}' has {total:,} chunks")
    
    # Scroll through and sample
    all_points = []
    offset = None
    batch_size = 100
    
    print(f"Sampling {sample_size} chunks...")
    
    while len(all_points) < min(sample_size * 2, total):
        result = client.scroll(
            collection_name=collection,
            limit=batch_size,
            offset=offset,
            with_payload=True
        )
        points, offset = result
        all_points.extend(points)
        
        if offset is None:
            break
    
    # Random sample
    if len(all_points) > sample_size:
        sampled = random.sample(all_points, sample_size)
    else:
        sampled = all_points
    
    return [{"id": p.id, "payload": p.payload} for p in sampled]


def analyze_chunk_sizes(chunks: list[dict]) -> dict:
    """Analyze chunk size distribution."""
    char_lengths = []
    word_counts = []
    
    for chunk in chunks:
        content = chunk["payload"].get("content", "")
        char_lengths.append(len(content))
        word_counts.append(len(content.split()))
    
    char_lengths.sort()
    
    return {
        "total_chunks": len(chunks),
        "char_length": {
            "min": min(char_lengths),
            "max": max(char_lengths),
            "mean": sum(char_lengths) / len(char_lengths),
            "median": char_lengths[len(char_lengths) // 2],
            "p10": char_lengths[len(char_lengths) // 10],
            "p90": char_lengths[int(len(char_lengths) * 0.9)],
        },
        "word_count": {
            "min": min(word_counts),
            "max": max(word_counts),
            "mean": sum(word_counts) / len(word_counts),
        },
        "too_short": sum(1 for c in char_lengths if c < THRESHOLDS["min_chunk_chars"]),
        "too_long": sum(1 for c in char_lengths if c > THRESHOLDS["max_chunk_chars"]),
        "in_ideal_range": sum(1 for c in char_lengths 
                             if THRESHOLDS["ideal_chunk_chars_min"] <= c <= THRESHOLDS["ideal_chunk_chars_max"]),
    }


def analyze_boundary_quality(chunks: list[dict]) -> dict:
    """Check if chunks are cut mid-sentence."""
    truncated_start = 0
    truncated_end = 0
    clean_boundaries = 0
    
    sentence_end_pattern = re.compile(r'[.!?:;]\s*$')
    sentence_start_pattern = re.compile(r'^[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ]')  # Starts with capital
    
    for chunk in chunks:
        content = chunk["payload"].get("content", "").strip()
        
        if not content:
            continue
        
        # Check start
        starts_clean = bool(sentence_start_pattern.match(content)) or content.startswith("[") or content.startswith("Article")
        
        # Check end
        ends_clean = bool(sentence_end_pattern.search(content))
        
        if not starts_clean:
            truncated_start += 1
        if not ends_clean:
            truncated_end += 1
        if starts_clean and ends_clean:
            clean_boundaries += 1
    
    total = len(chunks)
    
    return {
        "truncated_start": truncated_start,
        "truncated_start_rate": truncated_start / total if total else 0,
        "truncated_end": truncated_end,
        "truncated_end_rate": truncated_end / total if total else 0,
        "clean_boundaries": clean_boundaries,
        "clean_boundary_rate": clean_boundaries / total if total else 0,
    }


def analyze_article_coverage(chunks: list[dict]) -> dict:
    """Check if chunks preserve article/section references."""
    article_patterns = [
        r'Article\s+\d+',
        r'Art\.\s*\d+',
        r'Section\s+\d+',
        r'Chapitre\s+\d+',
        r'Titre\s+[IVX]+',
        r'Circulaire\s+n[°o]\s*\d+',
    ]
    
    has_article_ref = 0
    has_structural_marker = 0
    orphan_chunks = 0
    
    article_types = Counter()
    
    for chunk in chunks:
        content = chunk["payload"].get("content", "")
        article_ref = chunk["payload"].get("article_ref")
        
        if article_ref:
            has_article_ref += 1
        
        # Check for structural markers in content
        has_marker = False
        for pattern in article_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_marker = True
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    article_types[pattern.split("\\")[0]] += 1
                break
        
        if has_marker:
            has_structural_marker += 1
        
        # Orphan: no article ref and no markers
        if not article_ref and not has_marker and len(content) < 200:
            orphan_chunks += 1
    
    total = len(chunks)
    
    return {
        "has_article_ref": has_article_ref,
        "article_ref_rate": has_article_ref / total if total else 0,
        "has_structural_marker": has_structural_marker,
        "structural_marker_rate": has_structural_marker / total if total else 0,
        "orphan_chunks": orphan_chunks,
        "orphan_rate": orphan_chunks / total if total else 0,
        "article_types": dict(article_types),
    }


def analyze_semantic_coherence(chunks: list[dict]) -> dict:
    """Analyze semantic coherence of chunks."""
    # Heuristics for semantic coherence:
    # - Multiple topics in one chunk (bad)
    # - Chunk covers single concept (good)
    
    multi_topic_chunks = 0
    definition_chunks = 0
    list_chunks = 0
    
    for chunk in chunks:
        content = chunk["payload"].get("content", "")
        
        # Detect multiple articles in one chunk (bad splitting)
        article_mentions = len(re.findall(r'Article\s+\d+', content, re.IGNORECASE))
        if article_mentions > 2:
            multi_topic_chunks += 1
        
        # Detect definition-like content
        if re.search(r'(signifie|désigne|s\'entend|est défini)', content, re.IGNORECASE):
            definition_chunks += 1
        
        # Detect list content
        if content.count('\n-') > 2 or content.count('\n•') > 2:
            list_chunks += 1
    
    total = len(chunks)
    
    return {
        "multi_topic_chunks": multi_topic_chunks,
        "multi_topic_rate": multi_topic_chunks / total if total else 0,
        "definition_chunks": definition_chunks,
        "list_chunks": list_chunks,
    }


def calculate_production_score(analysis: dict) -> dict:
    """Calculate overall production-readiness score."""
    scores = []
    issues = []
    
    # Size distribution score
    ideal_rate = analysis["size"]["in_ideal_range"] / analysis["size"]["total_chunks"]
    size_score = min(1.0, ideal_rate / 0.6)  # 60% in ideal range = 1.0
    scores.append(("size_distribution", size_score))
    if ideal_rate < 0.5:
        issues.append(f"Only {ideal_rate:.0%} chunks in ideal size range (300-1000 chars)")
    
    # Too short chunks penalty
    too_short_rate = analysis["size"]["too_short"] / analysis["size"]["total_chunks"]
    if too_short_rate > 0.1:
        issues.append(f"{too_short_rate:.0%} chunks are too short (<100 chars)")
    
    # Boundary quality score
    boundary_score = analysis["boundaries"]["clean_boundary_rate"]
    scores.append(("boundary_quality", boundary_score))
    if analysis["boundaries"]["truncated_end_rate"] > THRESHOLDS["max_truncation_rate"]:
        issues.append(f"{analysis['boundaries']['truncated_end_rate']:.0%} chunks cut mid-sentence")
    
    # Article coverage score
    article_score = analysis["articles"]["article_ref_rate"]
    scores.append(("article_coverage", article_score))
    if article_score < THRESHOLDS["min_article_coverage"]:
        issues.append(f"Only {article_score:.0%} chunks have article references")
    
    # Orphan rate score
    orphan_rate = analysis["articles"]["orphan_rate"]
    orphan_score = max(0, 1 - orphan_rate / THRESHOLDS["max_orphan_rate"])
    scores.append(("context_preservation", orphan_score))
    if orphan_rate > THRESHOLDS["max_orphan_rate"]:
        issues.append(f"{orphan_rate:.0%} chunks are orphaned (no context)")
    
    # Semantic coherence score
    multi_topic_rate = analysis["coherence"]["multi_topic_rate"]
    coherence_score = max(0, 1 - multi_topic_rate / 0.2)  # 20% multi-topic = 0.0
    scores.append(("semantic_coherence", coherence_score))
    if multi_topic_rate > 0.1:
        issues.append(f"{multi_topic_rate:.0%} chunks contain multiple articles (poor splitting)")
    
    # Overall score (weighted average)
    weights = {
        "size_distribution": 0.2,
        "boundary_quality": 0.25,
        "article_coverage": 0.2,
        "context_preservation": 0.15,
        "semantic_coherence": 0.2,
    }
    
    overall = sum(score * weights[name] for name, score in scores)
    
    # Determine grade
    if overall >= 0.85:
        grade = "A (Production Ready)"
    elif overall >= 0.70:
        grade = "B (Near Production)"
    elif overall >= 0.55:
        grade = "C (Needs Improvement)"
    elif overall >= 0.40:
        grade = "D (Significant Issues)"
    else:
        grade = "F (Not Production Ready)"
    
    return {
        "overall_score": overall,
        "grade": grade,
        "component_scores": dict(scores),
        "issues": issues,
        "is_production_ready": overall >= 0.70,
    }


def print_report(analysis: dict, verbose: bool = False):
    """Print formatted analysis report."""
    print("\n" + "=" * 70)
    print("CHUNKING STRATEGY DIAGNOSTIC REPORT")
    print("=" * 70)
    
    print(f"\n📊 Sample Size: {analysis['size']['total_chunks']} chunks")
    
    # Size Distribution
    print("\n📏 CHUNK SIZE DISTRIBUTION")
    print("-" * 40)
    size = analysis["size"]
    print(f"   Characters: min={size['char_length']['min']}, max={size['char_length']['max']}, mean={size['char_length']['mean']:.0f}")
    print(f"   Words: min={size['word_count']['min']}, max={size['word_count']['max']}, mean={size['word_count']['mean']:.0f}")
    print(f"   Too short (<100 chars): {size['too_short']} ({size['too_short']/size['total_chunks']:.1%})")
    print(f"   Too long (>2000 chars): {size['too_long']} ({size['too_long']/size['total_chunks']:.1%})")
    print(f"   In ideal range (300-1000): {size['in_ideal_range']} ({size['in_ideal_range']/size['total_chunks']:.1%})")
    
    # Boundary Quality
    print("\n✂️ BOUNDARY QUALITY")
    print("-" * 40)
    bounds = analysis["boundaries"]
    print(f"   Clean boundaries: {bounds['clean_boundaries']} ({bounds['clean_boundary_rate']:.1%})")
    print(f"   Truncated start: {bounds['truncated_start']} ({bounds['truncated_start_rate']:.1%})")
    print(f"   Truncated end: {bounds['truncated_end']} ({bounds['truncated_end_rate']:.1%})")
    
    # Article Coverage
    print("\n📚 ARTICLE COVERAGE")
    print("-" * 40)
    articles = analysis["articles"]
    print(f"   Has article reference: {articles['has_article_ref']} ({articles['article_ref_rate']:.1%})")
    print(f"   Has structural marker: {articles['has_structural_marker']} ({articles['structural_marker_rate']:.1%})")
    print(f"   Orphan chunks: {articles['orphan_chunks']} ({articles['orphan_rate']:.1%})")
    
    # Semantic Coherence
    print("\n🧠 SEMANTIC COHERENCE")
    print("-" * 40)
    coherence = analysis["coherence"]
    print(f"   Multi-topic chunks: {coherence['multi_topic_chunks']} ({coherence['multi_topic_rate']:.1%})")
    print(f"   Definition chunks: {coherence['definition_chunks']}")
    print(f"   List-style chunks: {coherence['list_chunks']}")
    
    # Production Score
    print("\n" + "=" * 70)
    print("PRODUCTION READINESS SCORE")
    print("=" * 70)
    score = analysis["score"]
    print(f"\n   🎯 Overall Score: {score['overall_score']:.2f}/1.00")
    print(f"   📊 Grade: {score['grade']}")
    print(f"\n   Component Scores:")
    for name, val in score["component_scores"].items():
        bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
        print(f"      {name:25s} [{bar}] {val:.2f}")
    
    if score["issues"]:
        print("\n   ⚠️ Issues Found:")
        for issue in score["issues"]:
            print(f"      • {issue}")
    
    if score["is_production_ready"]:
        print("\n   ✅ VERDICT: Chunking strategy is PRODUCTION READY")
    else:
        print("\n   ❌ VERDICT: Chunking strategy NEEDS IMPROVEMENT")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if size["too_short"] / size["total_chunks"] > 0.1:
        print("   • Increase MIN_CHARACTERS_PER_CHUNK to filter tiny chunks")
    if bounds["truncated_end_rate"] > 0.15:
        print("   • Use sentence-aware chunking to avoid mid-sentence splits")
    if articles["article_ref_rate"] < 0.7:
        print("   • Improve article reference extraction in metadata")
    if coherence["multi_topic_rate"] > 0.1:
        print("   • Reduce CHUNK_SIZE to avoid mixing multiple articles")
    if articles["orphan_rate"] > 0.1:
        print("   • Add parent context (section title) to orphan chunks")


def main():
    parser = argparse.ArgumentParser(description="Analyze chunking strategy quality")
    parser.add_argument("--collection", type=str, default="regulations_v4", help="Collection name")
    parser.add_argument("--sample", type=int, default=200, help="Number of chunks to sample")
    parser.add_argument("--verbose", action="store_true", help="Show sample chunks")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()
    
    print("=" * 70)
    print("Chunking Strategy Diagnostic")
    print("=" * 70)
    
    # Connect to Qdrant
    client = get_qdrant_client()
    
    # Sample chunks
    chunks = sample_chunks(client, args.collection, args.sample)
    
    if not chunks:
        print("❌ No chunks found in collection")
        return
    
    # Run analyses
    print("\nAnalyzing chunk quality...")
    
    analysis = {
        "size": analyze_chunk_sizes(chunks),
        "boundaries": analyze_boundary_quality(chunks),
        "articles": analyze_article_coverage(chunks),
        "coherence": analyze_semantic_coherence(chunks),
    }
    
    analysis["score"] = calculate_production_score(analysis)
    
    # Print report
    print_report(analysis, verbose=args.verbose)
    
    # Save if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n📁 Results saved to: {output_path}")


if __name__ == "__main__":
    main()
