"""
Base Agent - Abstract interface for all Credit Decision Agents

All agents follow the same pattern:
1. Receive an application
2. Search Qdrant for relevant evidence
3. Analyze the evidence
4. Return a structured verdict
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

load_dotenv()

# Model configuration
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3  # Low temperature for consistent decisions

# Initialize LangChain ChatOpenAI (integrates with LangSmith)
llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=os.getenv("OPENAI_API_KEY")
)

llm_json = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=os.getenv("OPENAI_API_KEY"),
    model_kwargs={"response_format": {"type": "json_object"}}
)


class BaseAgent(ABC):
    """Abstract base class for all credit decision agents."""
    
    def __init__(self, name: str, role_description: str):
        self.name = name
        self.role_description = role_description
        self.llm = llm
        self.llm_json = llm_json
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def search_evidence(self, application: dict) -> list[dict]:
        """Search Qdrant for relevant evidence. Returns list of results."""
        pass
    
    @abstractmethod
    def analyze(self, application: dict, evidence: list[dict]) -> dict:
        """Analyze the application with evidence and return a verdict."""
        pass
    
    def run(self, application: dict) -> dict:
        """
        Main entry point: search for evidence, analyze, and return verdict.
        """
        # Step 1: Search for relevant evidence
        evidence = self.search_evidence(application)
        
        # Step 2: Analyze and generate verdict
        verdict = self.analyze(application, evidence)
        
        return verdict
    
    def _call_llm(self, messages: list[dict]) -> str:
        """Call LLM with messages."""
        langchain_messages = [
            SystemMessage(content=m["content"]) if m["role"] == "system" 
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        # Add run_name for LangSmith tracing
        config = RunnableConfig(run_name=f"{self.name}_reasoning")
        response = self.llm.invoke(langchain_messages, config=config)
        return response.content
    
    def _call_llm_json(self, messages: list[dict]) -> str:
        """Call LLM with JSON response format."""
        langchain_messages = [
            SystemMessage(content=m["content"]) if m["role"] == "system" 
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        # Add run_name for LangSmith tracing
        config = RunnableConfig(run_name=f"{self.name}_verdict")
        response = self.llm_json.invoke(langchain_messages, config=config)
        return response.content
    
    def _format_application(self, application: dict) -> str:
        """Format an application for LLM consumption."""
        lines = ["Application Details:"]
        for key, value in application.items():
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for k, v in value.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    def _format_evidence(self, evidence: list[dict]) -> str:
        """Format evidence for LLM consumption."""
        if not evidence:
            return "No similar historical cases found."
        
        lines = ["Historical Evidence:"]
        for i, e in enumerate(evidence, 1):
            payload = e.get("payload", {})
            score = e.get("score", 0)
            
            # Determine entity type and ID
            if "client_id" in payload:
                entity = f"Client {payload['client_id']}"
            elif "startup_id" in payload:
                entity = f"Startup {payload['startup_id']}"
            elif "enterprise_id" in payload:
                entity = f"Enterprise {payload['enterprise_id']}"
            else:
                entity = f"Entity {e.get('id', i)}"
            
            lines.append(f"\n{i}. {entity} (Similarity: {score:.2f})")
            lines.append(f"   Outcome: {payload.get('outcome', 'Unknown')}")
            
            # Add key metrics based on entity type
            if "debt_to_income_ratio" in payload:
                lines.append(f"   DTI: {payload['debt_to_income_ratio']:.1%}")
                lines.append(f"   Missed Payments: {payload.get('missed_payments_last_12m', 0)}")
            elif "burn_multiple" in payload:
                lines.append(f"   Burn Multiple: {payload['burn_multiple']:.1f}x")
                lines.append(f"   Runway: {payload['runway_months']:.0f} months")
            elif "altman_z_score" in payload:
                lines.append(f"   Z-Score: {payload['altman_z_score']:.2f}")
                lines.append(f"   Lawsuits: {payload.get('legal_lawsuits_active', 0)}")
        
        return "\n".join(lines)
