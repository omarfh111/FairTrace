"""
Regulation Agent - Banking Regulation Expert (Agentic Version)

This agent answers questions about banking regulations with:
1. Agentic retry loop with query reformulation
2. Quality assessment of retrieval results
3. Citation-aware responses with article references
4. Multi-turn conversation context

Uses the reg_bancaire.pdf (Tunisian Banking Regulation) as knowledge base.
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from tools.qdrant_retriever import (
    search_regulations,
    format_regulation_results,
    embed_query
)


# Agentic configuration
MAX_RETRIEVAL_ATTEMPTS = 3
MIN_RELEVANCE_SCORE = 0.03  # Minimum RRF score to consider relevant
MIN_RELEVANT_DOCS = 2  # Need at least 2 relevant docs


class RegulationAgent(BaseAgent):
    """Banking Regulation Expert - Agentic RAG with retry and reformulation."""
    
    def __init__(self):
        super().__init__(
            name="RegulationAgent",
            role_description="Expert in Tunisian banking regulations (Réglementation Bancaire BCT)"
        )
        self.conversation_history: list[dict] = []
        self.max_history = 5  # Keep last 5 exchanges for context
    
    @property
    def system_prompt(self) -> str:
        return """Tu es un expert en réglementation bancaire tunisienne (BCT - Banque Centrale de Tunisie).

Tu réponds aux questions sur la réglementation bancaire en te basant UNIQUEMENT sur les documents fournis.

Règles importantes:
1. Réponds toujours en français sauf si l'utilisateur pose sa question en anglais
2. Cite TOUJOURS les articles et pages sources entre crochets, ex: [Article 5, Page 42]
3. Si l'information n'est pas dans les documents, dis-le clairement
4. Structure tes réponses avec des titres et puces pour la clarté
5. Sois précis et concis, évite les répétitions

Format de réponse JSON:
{
    "answer": "Ta réponse détaillée avec citations [Article X, Page Y]",
    "citations": [
        {"article": "Article 5", "page": 42, "excerpt": "Texte pertinent..."},
        {"article": "Article 10", "page": 58, "excerpt": "Autre texte..."}
    ],
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "follow_up_questions": ["Question suggérée 1?", "Question suggérée 2?"]
}

Si aucune information pertinente n'est trouvée:
{
    "answer": "Je n'ai pas trouvé d'information sur ce sujet dans la réglementation bancaire.",
    "citations": [],
    "confidence": "LOW",
    "follow_up_questions": ["Questions alternatives suggérées..."]
}"""

    @property
    def reformulation_prompt(self) -> str:
        return """Tu es un assistant spécialisé dans la reformulation de requêtes de recherche.

L'utilisateur a posé une question sur la réglementation bancaire tunisienne, mais les résultats 
de recherche ne sont pas satisfaisants.

Ta tâche: Reformuler la question pour améliorer les résultats de recherche.

Stratégies de reformulation:
1. Utiliser des synonymes ou termes techniques bancaires
2. Décomposer la question en concepts clés
3. Ajouter le contexte réglementaire (BCT, loi bancaire, circulaire)
4. Traduire les termes anglais en français si nécessaire

Réponds UNIQUEMENT avec la nouvelle requête reformulée, sans explication.
Limite: 100 mots maximum."""
    
    def _assess_retrieval_quality(self, results: list[dict]) -> tuple[bool, str]:
        """
        Assess quality of retrieval results.
        
        Returns:
            (is_good_quality, reason)
        """
        if not results:
            return False, "no_results"
        
        # Count documents with good relevance scores
        relevant_docs = [r for r in results if r.get("score", 0) >= MIN_RELEVANCE_SCORE]
        
        if len(relevant_docs) < MIN_RELEVANT_DOCS:
            return False, f"low_relevance: only {len(relevant_docs)} relevant docs"
        
        # Check if top result has good score
        top_score = results[0].get("score", 0)
        if top_score < MIN_RELEVANCE_SCORE * 1.5:
            return False, f"weak_top_result: score={top_score:.3f}"
        
        return True, "good"
    
    def _reformulate_query(self, original_query: str, attempt: int, previous_queries: list[str]) -> str:
        """
        Use LLM to reformulate query for better retrieval.
        """
        strategies = [
            "Ajoute des termes techniques bancaires ou réglementaires.",
            "Simplifie la question en mots-clés essentiels.",
            "Reformule en utilisant des synonymes et le vocabulaire BCT."
        ]
        
        strategy = strategies[min(attempt - 1, len(strategies) - 1)]
        
        messages = [
            {"role": "system", "content": self.reformulation_prompt},
            {"role": "user", "content": f"""Question originale: {original_query}

Requêtes déjà essayées: {previous_queries}

Stratégie à appliquer: {strategy}

Donne une nouvelle formulation de la question:"""}
        ]
        
        try:
            reformulated = self._call_llm(messages).strip()
            # Clean up - remove quotes if present
            reformulated = reformulated.strip('"\'')
            # Limit length
            if len(reformulated) > 300:
                reformulated = reformulated[:300]
            return reformulated
        except Exception as e:
            # Fallback: just add context
            return f"réglementation bancaire BCT {original_query}"
    
    def search_evidence(self, query: str) -> list[dict]:
        """Search regulations collection for relevant chunks."""
        # Compute embeddings once
        dense_vec, sparse_idx, sparse_vals = embed_query(query)
        
        # Search for relevant regulation chunks
        response = search_regulations(
            query_text=query,
            limit=8,  # Get top 8 most relevant chunks
            dense_vector=dense_vec,
            sparse_indices=sparse_idx,
            sparse_values=sparse_vals
        )
        
        return response.get("results", [])
    
    def search_with_retry(self, query: str) -> tuple[list[dict], list[str], int]:
        """
        Agentic search with retry and query reformulation.
        
        Returns:
            (results, queries_tried, attempt_count)
        """
        queries_tried = [query]
        current_query = query
        
        for attempt in range(1, MAX_RETRIEVAL_ATTEMPTS + 1):
            # Search with current query
            results = self.search_evidence(current_query)
            
            # Assess quality
            is_good, reason = self._assess_retrieval_quality(results)
            
            if is_good:
                # Good results - return them
                return results, queries_tried, attempt
            
            # Bad results - try reformulation if we have attempts left
            if attempt < MAX_RETRIEVAL_ATTEMPTS:
                print(f"⚠️ Attempt {attempt}: {reason} - reformulating query...")
                current_query = self._reformulate_query(query, attempt, queries_tried)
                queries_tried.append(current_query)
                print(f"   New query: {current_query[:80]}...")
            else:
                # Last attempt - return what we have
                print(f"⚠️ Attempt {attempt}: {reason} - returning best results")
        
        return results, queries_tried, MAX_RETRIEVAL_ATTEMPTS
    
    def analyze(self, query: str, evidence: list[dict], retrieval_attempts: int = 1) -> dict:
        """Analyze query with evidence and generate citation-aware response."""
        # Format evidence for LLM
        evidence_text = self._format_regulation_evidence(evidence)
        
        # Build conversation context
        context = self._build_conversation_context()
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Documents de référence:

{evidence_text}

{context}Question actuelle: {query}

Réponds en JSON avec les citations appropriées."""}
        ]
        
        response = self._call_llm_json(messages)
        
        try:
            result = json.loads(response)
            result["agent_name"] = self.name
            result["sources_count"] = len(evidence)
            result["retrieval_attempts"] = retrieval_attempts
            
            # Extract unique pages for reference
            pages = list(set(
                e.get("payload", {}).get("page_number") 
                for e in evidence 
                if e.get("payload", {}).get("page_number")
            ))
            result["source_pages"] = sorted(pages)[:5]  # Top 5 pages
            
            # Adjust confidence based on retrieval quality
            if retrieval_attempts > 1:
                # Lower confidence if we needed retries
                if result.get("confidence") == "HIGH":
                    result["confidence"] = "MEDIUM"
            
        except json.JSONDecodeError:
            result = {
                "agent_name": self.name,
                "answer": response,
                "citations": [],
                "confidence": "MEDIUM",
                "follow_up_questions": [],
                "sources_count": len(evidence),
                "source_pages": [],
                "retrieval_attempts": retrieval_attempts
            }
        
        return result
    
    def chat(self, message: str, conversation_id: Optional[str] = None) -> dict:
        """
        Main chat interface with agentic retry loop.
        
        The agent will:
        1. Search for evidence
        2. Assess retrieval quality
        3. Reformulate query if results are poor (max 3 attempts)
        4. Generate citation-aware response
        
        Args:
            message: User's question
            conversation_id: Optional ID for conversation continuity
            
        Returns:
            Dict with answer, citations, suggestions, and retrieval metadata
        """
        # Agentic search with retry
        evidence, queries_tried, attempts = self.search_with_retry(message)
        
        # Generate response
        response = self.analyze(message, evidence, retrieval_attempts=attempts)
        
        # Add retrieval metadata
        response["queries_tried"] = queries_tried
        response["used_reformulation"] = len(queries_tried) > 1
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        self.conversation_history.append({
            "role": "assistant", 
            "content": response.get("answer", "")
        })
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        return response
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def _format_regulation_evidence(self, evidence: list[dict]) -> str:
        """Format regulation evidence for LLM consumption."""
        if not evidence:
            return "Aucun document pertinent trouvé."
        
        lines = []
        for i, e in enumerate(evidence, 1):
            payload = e.get("payload", {})
            page = payload.get("page_number", "?")
            article = payload.get("article_ref", "")
            section = payload.get("section_title", "")
            content = payload.get("content", "")
            score = e.get("score", 0)
            
            header = f"[Document {i}] Page {page}"
            if article:
                header += f" - {article}"
            if section:
                header += f" ({section})"
            header += f" [Pertinence: {score:.2f}]"
            
            lines.append(f"{header}\n{content}\n")
        
        return "\n---\n".join(lines)
    
    def _build_conversation_context(self) -> str:
        """Build context from conversation history."""
        if not self.conversation_history:
            return ""
        
        context_lines = ["Historique de la conversation:"]
        for msg in self.conversation_history[-4:]:  # Last 2 exchanges
            role = "Utilisateur" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines) + "\n\n"
    
    def get_suggestions(self) -> list[str]:
        """Get contextual question suggestions."""
        if not self.conversation_history:
            # Initial suggestions
            return [
                "Quelles sont les obligations des banques en matière de conformité?",
                "Qu'est-ce que le ratio de solvabilité bancaire?",
                "Quelles sont les règles de gouvernance bancaire?",
                "Comment fonctionne le contrôle interne dans les banques?",
                "Quelles sont les sanctions prévues par la BCT?"
            ]
        
        # Get suggestions from last response
        for msg in reversed(self.conversation_history):
            if msg["role"] == "assistant":
                # Try to parse as JSON to get follow_up_questions
                try:
                    parsed = json.loads(msg["content"])
                    if "follow_up_questions" in parsed:
                        return parsed["follow_up_questions"]
                except:
                    pass
                break
        
        # Default follow-up suggestions
        return [
            "Peux-tu préciser ce point?",
            "Quels sont les articles connexes?",
            "Y a-t-il des exceptions à cette règle?"
        ]


# Singleton instance for reuse
_regulation_agent: RegulationAgent | None = None


def get_regulation_agent() -> RegulationAgent:
    """Get or create RegulationAgent singleton."""
    global _regulation_agent
    if _regulation_agent is None:
        _regulation_agent = RegulationAgent()
    return _regulation_agent


# Test
if __name__ == "__main__":
    agent = RegulationAgent()
    
    print("Testing Agentic Regulation Agent...")
    print("=" * 60)
    
    # Test with a query that might need reformulation
    test_queries = [
        "Qu'est-ce que l'Article 5?",
        "What are the capital requirements?",  # English - should reformulate
        "comment fonctionne le KYC bancaire",  # Might need BCT context
    ]
    
    for query in test_queries[:1]:  # Just test first one
        print(f"\n📝 Query: {query}")
        result = agent.chat(query)
        
        print(f"\n✅ Answer: {result.get('answer', 'N/A')[:300]}...")
        print(f"📊 Retrieval attempts: {result.get('retrieval_attempts', 1)}")
        print(f"🔄 Used reformulation: {result.get('used_reformulation', False)}")
        print(f"📄 Queries tried: {result.get('queries_tried', [])}")
        print(f"📖 Source pages: {result.get('source_pages', [])}")
        print(f"⭐ Confidence: {result.get('confidence', 'N/A')}")

