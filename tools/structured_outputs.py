"""
Structured Outputs - Pydantic Schemas for Agent Verdicts

Defines the structured output format for:
- Individual agent verdicts
- Final orchestrator decision
- Audit trail entries
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================
class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CONDITIONAL = "CONDITIONAL"
    ESCALATE = "ESCALATE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# EVIDENCE MODELS
# =============================================================================
class RetrievedEvidence(BaseModel):
    """A piece of evidence retrieved from Qdrant."""
    entity_id: str = Field(description="ID of the retrieved entity (e.g., CLI-00042)")
    entity_type: Literal["Client", "Startup", "Enterprise"]
    similarity_score: float = Field(ge=0, le=1, description="Cosine similarity score")
    outcome: str = Field(description="Historical outcome of this entity")
    key_metrics: dict = Field(description="Key metrics that influenced retrieval")
    relevance_explanation: str = Field(description="Why this evidence is relevant")


class EvidenceBundle(BaseModel):
    """Collection of evidence from a search."""
    query: str = Field(description="The search query used")
    vector_type: Literal["structured", "narrative", "keywords", "hybrid"]
    results: list[RetrievedEvidence] = Field(default_factory=list)
    search_latency_ms: float = Field(default=0)


# =============================================================================
# AGENT VERDICT MODELS
# =============================================================================
class AgentVerdict(BaseModel):
    """Base verdict from any agent."""
    agent_name: str = Field(description="Name of the agent (e.g., 'RiskAgent')")
    recommendation: Decision = Field(description="Agent's recommended decision")
    confidence: Confidence = Field(description="Confidence level in this verdict")
    risk_level: RiskLevel = Field(description="Assessed risk level")
    reasoning: str = Field(description="Detailed reasoning for this verdict")
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list, description="Main concerns raised")
    mitigating_factors: list[str] = Field(default_factory=list, description="Positive factors")


class RiskAgentVerdict(AgentVerdict):
    """Verdict from the Risk Agent (Prosecutor)."""
    agent_name: str = "RiskAgent"
    red_flags: list[str] = Field(default_factory=list, description="Specific red flags identified")
    similar_defaults: int = Field(default=0, description="Number of similar cases that defaulted")


class FairnessAgentVerdict(AgentVerdict):
    """Verdict from the Fairness Agent (Comparator)."""
    agent_name: str = "FairnessAgent"
    similar_approved: int = Field(default=0, description="Number of similar cases approved")
    consistency_score: float = Field(default=0, ge=0, le=1, description="How consistent is this with past decisions")
    potential_bias_flags: list[str] = Field(default_factory=list)


class TrajectoryAgentVerdict(AgentVerdict):
    """Verdict from the Trajectory Agent (Predictor)."""
    agent_name: str = "TrajectoryAgent"
    predicted_outcome: str = Field(description="Predicted future outcome")
    prediction_confidence: float = Field(ge=0, le=1)
    trajectory_pattern: str = Field(description="Identified trajectory pattern")
    time_to_default_months: int | None = Field(default=None, description="If predicting default, estimated months")


# =============================================================================
# ORCHESTRATOR DECISION
# =============================================================================
class OrchestratorDecision(BaseModel):
    """Final decision from the Orchestrator (The Judge)."""
    decision: Decision = Field(description="Final credit decision")
    confidence: Confidence = Field(description="Overall confidence")
    risk_level: RiskLevel = Field(description="Final assessed risk level")
    
    # Agent inputs
    risk_agent_verdict: RiskAgentVerdict | None = None
    fairness_agent_verdict: FairnessAgentVerdict | None = None
    trajectory_agent_verdict: TrajectoryAgentVerdict | None = None
    
    # Synthesis
    reasoning: str = Field(description="Synthesized reasoning from all agents")
    key_factors: list[str] = Field(description="Top factors influencing decision")
    conditions: list[str] = Field(default_factory=list, description="Conditions if CONDITIONAL")
    
    # Audit
    decision_id: str = Field(description="Unique ID for this decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = Field(default=0)


# =============================================================================
# AUDIT TRAIL
# =============================================================================
class AuditEntry(BaseModel):
    """Audit trail entry for compliance."""
    decision_id: str
    timestamp: datetime
    input_application: dict = Field(description="The input application data")
    
    # Process trace
    risk_search_results: int = Field(description="Number of results from risk search")
    fairness_search_results: int = Field(description="Number of results from fairness search")
    trajectory_search_results: int = Field(description="Number of results from trajectory search")
    
    # Verdicts
    agent_verdicts: dict[str, str] = Field(description="Summary of each agent's verdict")
    
    # Final
    final_decision: Decision
    final_reasoning: str
    
    # Metrics
    total_tokens_used: int = Field(default=0)
    total_latency_ms: float = Field(default=0)


# =============================================================================
# APPLICATION INPUT
# =============================================================================
class ClientApplication(BaseModel):
    """Input schema for a client loan application."""
    age: int = Field(ge=18, le=100)
    contract_type: Literal["CDI", "CDD", "Freelance", "Unemployed"]
    job_tenure_years: int = Field(ge=0)
    income_annual: float = Field(gt=0)
    debt_to_income_ratio: float = Field(ge=0, le=1)
    missed_payments_last_12m: int = Field(ge=0)
    credit_utilization_avg: float = Field(ge=0, le=1)
    loan_purpose: str
    loan_amount: float = Field(gt=0)


class StartupApplication(BaseModel):
    """Input schema for a startup funding application."""
    sector: str
    founder_experience_years: int = Field(ge=0)
    vc_backing: bool
    arr_current: float = Field(ge=0)
    arr_growth_yoy: float
    burn_rate_monthly: float = Field(ge=0)
    runway_months: float = Field(ge=0)
    funding_amount_requested: float = Field(gt=0)


class EnterpriseApplication(BaseModel):
    """Input schema for an enterprise credit application."""
    industry_code: str
    revenue_annual: float = Field(gt=0)
    net_profit_margin: float
    current_ratio: float = Field(ge=0)
    quick_ratio: float = Field(ge=0)
    debt_to_equity: float = Field(ge=0)
    altman_z_score: float
    legal_lawsuits_active: int = Field(ge=0)
    credit_amount_requested: float = Field(gt=0)
