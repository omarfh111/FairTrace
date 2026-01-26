"""
Chat Routes - Regulation Chatbot API Endpoints

Endpoints:
- POST /chat/regulation      - Send message, get response
- GET  /chat/regulation/suggestions - Get contextual suggestions
- DELETE /chat/regulation/{conversation_id} - Clear conversation history
"""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatCitation,
)

# Import regulation agent
try:
    from agents.regulation_agent import get_regulation_agent, RegulationAgent
    REGULATION_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ RegulationAgent not available: {e}")
    REGULATION_AGENT_AVAILABLE = False

router = APIRouter(prefix="/chat", tags=["chat"])

# Store conversation agents by ID for multi-turn support
_conversation_agents: dict[str, RegulationAgent] = {}


def _get_or_create_agent(conversation_id: Optional[str]) -> tuple[str, RegulationAgent]:
    """Get existing agent for conversation or create new one."""
    if not REGULATION_AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Regulation Agent is not available"
        )
    
    if conversation_id and conversation_id in _conversation_agents:
        return conversation_id, _conversation_agents[conversation_id]
    
    # Create new conversation
    new_id = conversation_id or str(uuid.uuid4())[:8]
    
    # Import here to avoid circular imports
    from agents.regulation_agent import RegulationAgent
    agent = RegulationAgent()
    _conversation_agents[new_id] = agent
    
    # Cleanup old conversations (keep max 100)
    if len(_conversation_agents) > 100:
        oldest_keys = list(_conversation_agents.keys())[:50]
        for key in oldest_keys:
            del _conversation_agents[key]
    
    return new_id, agent


@router.post("/regulation", response_model=ChatResponse)
async def chat_regulation(request: ChatRequest) -> ChatResponse:
    """
    Chat with the Banking Regulation Agent.
    
    Send a question about Tunisian banking regulations (BCT) and receive
    a citation-aware response with references to specific articles and pages.
    
    Supports multi-turn conversation via conversation_id.
    """
    start_time = time.time()
    
    try:
        conversation_id, agent = _get_or_create_agent(request.conversation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent: {str(e)}"
        )
    
    try:
        # Get response from agent
        result = agent.chat(request.message)
        
        # Convert citations to proper format
        citations = []
        for cit in result.get("citations", []):
            try:
                citations.append(ChatCitation(
                    article=cit.get("article"),
                    page=cit.get("page", 0),
                    excerpt=cit.get("excerpt", "")[:300]  # Limit excerpt length
                ))
            except Exception:
                pass  # Skip malformed citations
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            answer=result.get("answer", "Désolé, je n'ai pas pu générer une réponse."),
            citations=citations,
            confidence=result.get("confidence", "MEDIUM"),
            source_pages=result.get("source_pages", []),
            follow_up_questions=result.get("follow_up_questions", [])[:3],  # Max 3 suggestions
            conversation_id=conversation_id,
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )


@router.get("/regulation/suggestions")
async def get_suggestions(conversation_id: Optional[str] = None) -> dict:
    """
    Get contextual question suggestions.
    
    Returns suggestions based on current conversation context,
    or default suggestions if no active conversation.
    """
    if not REGULATION_AGENT_AVAILABLE:
        # Return default suggestions even if agent not available
        return {
            "suggestions": [
                "Quelles sont les obligations des banques en matière de conformité?",
                "Qu'est-ce que le ratio de solvabilité bancaire?",
                "Comment fonctionne le contrôle interne dans les banques?",
            ]
        }
    
    if conversation_id and conversation_id in _conversation_agents:
        agent = _conversation_agents[conversation_id]
        suggestions = agent.get_suggestions()
    else:
        # Default suggestions
        from agents.regulation_agent import RegulationAgent
        agent = RegulationAgent()
        suggestions = agent.get_suggestions()
    
    return {"suggestions": suggestions}


@router.delete("/regulation/{conversation_id}")
async def clear_conversation(conversation_id: str) -> dict:
    """
    Clear conversation history.
    
    Removes the conversation agent and its history from memory.
    """
    if conversation_id in _conversation_agents:
        del _conversation_agents[conversation_id]
        return {"status": "cleared", "conversation_id": conversation_id}
    
    return {"status": "not_found", "conversation_id": conversation_id}


@router.get("/regulation/health")
async def chat_health() -> dict:
    """Check health of the regulation chat service."""
    return {
        "status": "healthy" if REGULATION_AGENT_AVAILABLE else "unavailable",
        "agent_available": REGULATION_AGENT_AVAILABLE,
        "active_conversations": len(_conversation_agents)
    }
