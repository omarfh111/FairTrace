"""
LLM Module - Centralized LLM with LangSmith tracing for cost monitoring.
Uses langchain-openai for automatic token tracking and cost calculation.
"""

import os
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import (
    OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE,
    LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT
)

# Set environment variables for LangSmith tracing
if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    print(f"✓ LangSmith tracing enabled (project: {LANGCHAIN_PROJECT})")


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """
    Get a cached ChatOpenAI instance with LangSmith tracing.
    All calls through this LLM are automatically traced and costs are tracked.
    """
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
        model_kwargs={"response_format": {"type": "json_object"}}
    )


def get_llm_no_json() -> ChatOpenAI:
    """Get LLM without JSON response format."""
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


def call_llm_json(system_prompt: str, user_message: str, metadata: dict = None) -> str:
    """
    Call the LLM with system and user prompts, returning JSON response.
    All calls are traced in LangSmith with metadata for cost tracking.
    
    Args:
        system_prompt: The system prompt
        user_message: The user message
        metadata: Optional metadata to attach to the trace
        
    Returns:
        The LLM response content as a string (JSON format)
    """
    llm = get_llm()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    # Add metadata to the run if provided
    config = {}
    if metadata:
        config["metadata"] = metadata
        config["run_name"] = metadata.get("agent_name", "LLM Call")
    
    response = llm.invoke(messages, config=config)
    
    return response.content


def call_agent(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    application_type: str = None
) -> str:
    """
    Call an agent with automatic LangSmith tracing.
    The agent name is used for tracking and grouping in LangSmith.
    
    Args:
        agent_name: Name of the agent (e.g., "Financial Agent")
        system_prompt: The system prompt
        user_message: The user message
        application_type: Optional type of application being analyzed
        
    Returns:
        The LLM response content as a string (JSON format)
    """
    metadata = {
        "agent_name": agent_name,
        "application_type": application_type or "unknown",
        "model": LLM_MODEL
    }
    
    return call_llm_json(system_prompt, user_message, metadata)


# =============================================================================
# COST ESTIMATION (for display purposes)
# =============================================================================
# gpt-4o-mini pricing (as of 2024)
COST_PER_1M_INPUT = 0.15  # $0.15 per 1M input tokens
COST_PER_1M_OUTPUT = 0.60  # $0.60 per 1M output tokens


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for given token counts."""
    input_cost = (input_tokens / 1_000_000) * COST_PER_1M_INPUT
    output_cost = (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT
    return input_cost + output_cost


def format_cost(cost: float) -> str:
    """Format cost as a readable string."""
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"
