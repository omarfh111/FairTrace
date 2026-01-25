"""
API Schemas - Pydantic Models for Request/Response

Defines type-safe request and response models for the FairTrace API.
"""

from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# APPLICATION SCHEMAS
# =============================================================================

class ClientApplication(BaseModel):
    """Individual loan application."""
    age: int = Field(..., ge=18, le=100, description="Applicant age")
    contract_type: Literal["CDI", "CDD", "Freelance"] = Field(..., description="Employment contract type")
    income_annual: float = Field(..., gt=0, description="Annual income in local currency")
    debt_to_income_ratio: float = Field(..., ge=0, le=1, description="Debt-to-income ratio (0-1)")
    missed_payments_last_12m: int = Field(0, ge=0, description="Number of missed payments in last 12 months")
    loan_purpose: Optional[str] = Field(None, description="Purpose of the loan")
    credit_score_internal: Optional[int] = Field(None, ge=300, le=850, description="Internal credit score")


class StartupApplication(BaseModel):
    """Startup funding application."""
    sector: str = Field(..., description="Business sector (e.g., SaaS, FinTech)")
    arr_current: float = Field(..., ge=0, description="Current Annual Recurring Revenue")
    arr_growth_yoy: float = Field(..., description="Year-over-year ARR growth rate")
    burn_rate_monthly: float = Field(..., ge=0, description="Monthly burn rate")
    runway_months: float = Field(..., ge=0, description="Remaining runway in months")
    burn_multiple: float = Field(..., description="Burn multiple (burn / net new ARR)")
    vc_backing: bool = Field(False, description="Whether startup has VC backing")
    funding_stage: Optional[str] = Field(None, description="Current funding stage")


class EnterpriseApplication(BaseModel):
    """Enterprise credit application."""
    industry_code: str = Field(..., description="Industry code/sector")
    revenue_annual: float = Field(..., gt=0, description="Annual revenue")
    altman_z_score: float = Field(..., description="Altman Z-Score for bankruptcy prediction")
    legal_lawsuits_active: int = Field(0, ge=0, description="Number of active lawsuits")
    ceo_prior_bankruptcies: int = Field(0, ge=0, description="CEO's prior bankruptcy filings")
    years_in_business: int = Field(..., ge=0, description="Years in operation")


class GenericApplication(BaseModel):
    """Generic application that can contain any fields."""
    data: dict = Field(..., description="Application data as key-value pairs")


# =============================================================================
# VERDICT SCHEMAS
# =============================================================================

class EvidenceItem(BaseModel):
    """A single piece of evidence used in the decision."""
    entity_id: str = Field(..., description="ID of the similar entity")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    outcome: str = Field(..., description="Historical outcome of this entity")
    key_factors: list[str] = Field(default_factory=list, description="Key factors for this match")


class AgentVerdict(BaseModel):
    """Verdict from a single agent."""
    agent_name: str = Field(..., description="Name of the agent")
    recommendation: Literal["APPROVE", "REJECT", "CONDITIONAL", "ESCALATE"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reasoning: str = Field(..., description="Detailed explanation")
    key_concerns: list[str] = Field(default_factory=list, description="List of concerns")
    mitigating_factors: list[str] = Field(default_factory=list, description="Positive factors")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Supporting evidence")


class FinalDecision(BaseModel):
    """Final synthesized decision from the orchestrator."""
    recommendation: Literal["APPROVE", "REJECT", "CONDITIONAL", "ESCALATE"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reasoning: str = Field(..., description="Explanation of the decision")
    conditions: list[str] = Field(default_factory=list, description="Conditions if CONDITIONAL")
    agent_agreement: Literal["UNANIMOUS", "MAJORITY", "SPLIT"]
    key_factors: list[str] = Field(default_factory=list, description="Most important factors")


# =============================================================================
# API REQUEST/RESPONSE SCHEMAS
# =============================================================================

class DecisionRequest(BaseModel):
    """Request to evaluate a credit application."""
    application_type: Literal["client", "startup", "enterprise", "auto"] = Field(
        "auto", 
        description="Type of application. Use 'auto' to detect automatically."
    )
    application: dict = Field(..., description="Application data")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "application_type": "startup",
                    "application": {
                        "sector": "SaaS",
                        "arr_current": 500000,
                        "arr_growth_yoy": 0.8,
                        "burn_rate_monthly": 80000,
                        "runway_months": 6,
                        "burn_multiple": 5.5,
                        "vc_backing": False
                    }
                }
            ]
        }
    }


class DecisionResponse(BaseModel):
    """Response containing the full credit decision."""
    decision_id: str = Field(..., description="Unique identifier for this decision")
    application_type: str = Field(..., description="Detected or specified application type")
    timestamp: datetime = Field(..., description="When the decision was made")
    
    # Agent verdicts
    risk_verdict: Optional[AgentVerdict] = None
    fairness_verdict: Optional[AgentVerdict] = None
    trajectory_verdict: Optional[AgentVerdict] = None
    
    # Final decision
    final_decision: FinalDecision
    
    # Metadata
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if any")


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    components: dict[str, Literal["ok", "error"]]
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# ON-DEMAND AGENT SCHEMAS
# =============================================================================

class ImprovementArea(BaseModel):
    """An area for improvement identified by the Advisor Agent."""
    area: str = Field(..., description="The area needing improvement")
    current_state: str = Field(..., description="Current state assessment")
    target_state: str = Field(..., description="Desired target state")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Priority level")


class Recommendation(BaseModel):
    """A specific actionable recommendation."""
    action: str = Field(..., description="Specific action to take")
    rationale: str = Field(..., description="Why this helps")
    timeline: str = Field(..., description="Realistic timeframe")
    expected_impact: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Expected impact")
    difficulty: Literal["EASY", "MODERATE", "HARD"] = Field(..., description="Difficulty level")


class AdvisorResponse(BaseModel):
    """Response from the Advisor Agent."""
    agent_name: str = Field(default="AdvisorAgent", description="Name of the agent")
    improvement_areas: list[ImprovementArea] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    similar_approved_characteristics: list[str] = Field(default_factory=list)
    overall_outlook: Literal["PROMISING", "CHALLENGING", "DIFFICULT"] = "CHALLENGING"
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    success_cases_analyzed: int = Field(0, description="Number of approved cases analyzed")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    processing_time_ms: float = Field(0, description="Processing time in milliseconds")


class KeyPattern(BaseModel):
    """A pattern observed across historical cases."""
    pattern: str = Field(..., description="The observed pattern")
    frequency: Literal["COMMON", "OCCASIONAL", "RARE"] = Field(..., description="How often this occurs")
    significance: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Significance level")


class Story(BaseModel):
    """A narrative story from a historical case."""
    title: str = Field(..., description="Brief story title")
    summary: str = Field(..., description="Story summary")
    key_factor: Optional[str] = Field(None, description="Key success factor")
    key_lesson: Optional[str] = Field(None, description="Key lesson learned")


class NarrativeResponse(BaseModel):
    """Response from the Narrative Agent."""
    agent_name: str = Field(default="NarrativeAgent", description="Name of the agent")
    narrative_summary: str = Field(..., description="Compelling overall narrative")
    key_patterns: list[KeyPattern] = Field(default_factory=list)
    success_stories: list[Story] = Field(default_factory=list)
    cautionary_tales: list[Story] = Field(default_factory=list)
    industry_context: str = Field("", description="Industry context")
    lessons_learned: list[str] = Field(default_factory=list)
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    cases_analyzed: int = Field(0, description="Total cases analyzed")
    outcome_distribution: dict = Field(default_factory=dict, description="Distribution of outcomes")
    processing_time_ms: float = Field(0, description="Processing time in milliseconds")


# =============================================================================
# COMPARATOR AGENT SCHEMAS
# =============================================================================

class MetricComparison(BaseModel):
    """Comparison of a single metric against approved cases."""
    metric_name: str = Field(..., description="Name of the metric")
    applicant_value: Any = Field(..., description="Applicant's value")
    approved_average: Any = Field(..., description="Average of approved cases")
    approved_range: Optional[dict] = Field(None, description="Min/max range")
    gap_percentage: float = Field(0, description="Gap percentage (negative=better)")
    status: Literal["ABOVE_AVERAGE", "AT_AVERAGE", "BELOW_AVERAGE", "CRITICAL_GAP"] = "AT_AVERAGE"
    
    @field_validator('gap_percentage', mode='before')
    @classmethod
    def coerce_gap_percentage(cls, v):
        if isinstance(v, str):
            # Remove % sign and convert
            v = v.replace('%', '').strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v if v is not None else 0.0
    
    @field_validator('status', mode='before')
    @classmethod
    def coerce_status(cls, v):
        valid = ["ABOVE_AVERAGE", "AT_AVERAGE", "BELOW_AVERAGE", "CRITICAL_GAP"]
        if v in valid:
            return v
        # Map common LLM variations
        v_upper = str(v).upper().replace(" ", "_").replace("-", "_")
        if "ABOVE" in v_upper:
            return "ABOVE_AVERAGE"
        elif "BELOW" in v_upper or "CRITICAL" in v_upper or "GAP" in v_upper:
            return "BELOW_AVERAGE"
        # Default for N/A, unknown, etc.
        return "AT_AVERAGE"


class GapItem(BaseModel):
    """A specific gap identified in the application."""
    metric: str = Field(..., description="Metric with the gap")
    description: str = Field(..., description="Description of the gap")
    gap_severity: Literal["MINOR", "MODERATE", "SIGNIFICANT", "CRITICAL"] = "MODERATE"
    target_value: Any = Field(None, description="Value needed to be competitive")
    
    @field_validator('gap_severity', mode='before')
    @classmethod
    def coerce_gap_severity(cls, v):
        valid = ["MINOR", "MODERATE", "SIGNIFICANT", "CRITICAL"]
        if v in valid:
            return v
        v_upper = str(v).upper()
        if "MINOR" in v_upper or "LOW" in v_upper:
            return "MINOR"
        elif "SIGNIFICANT" in v_upper or "HIGH" in v_upper:
            return "SIGNIFICANT"
        elif "CRITICAL" in v_upper or "SEVERE" in v_upper:
            return "CRITICAL"
        return "MODERATE"


class StrengthItem(BaseModel):
    """A strength relative to approved cases."""
    metric: str = Field(..., description="Metric that's a strength")
    description: str = Field(..., description="Description of the advantage")
    advantage_percentage: float = Field(0, description="How much better than average")
    
    @field_validator('advantage_percentage', mode='before')
    @classmethod
    def coerce_advantage(cls, v):
        if isinstance(v, str):
            v = v.replace('%', '').strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v if v is not None else 0.0


class ComparatorResponse(BaseModel):
    """Response from the Comparator Agent."""
    agent_name: str = Field(default="ComparatorAgent", description="Name of the agent")
    overall_gap_score: float = Field(0, ge=0, le=100, description="Gap score 0-100")
    metric_comparisons: list[MetricComparison] = Field(default_factory=list)
    strengths: list[StrengthItem] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    percentile_ranking: dict = Field(default_factory=dict, description="Percentile rankings")
    closest_approved_case: Optional[dict] = Field(None, description="Most similar approved case")
    executive_summary: str = Field("", description="Summary of gap analysis")
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    approved_cases_analyzed: int = Field(0, description="Cases analyzed")
    processing_time_ms: float = Field(0, description="Processing time in milliseconds")


# =============================================================================
# SCENARIO AGENT SCHEMAS
# =============================================================================

class ScenarioChange(BaseModel):
    """A single change in a scenario."""
    metric: str = Field(..., description="Metric to change")
    from_value: str | int | float = Field(..., description="Current value")
    to_value: str | int | float = Field(..., description="New value in scenario")


class Scenario(BaseModel):
    """A what-if scenario with predictions."""
    scenario_name: str = Field(..., description="Name of the scenario")
    changes: list[ScenarioChange] = Field(default_factory=list)
    predicted_outcome: Literal["APPROVE", "CONDITIONAL", "REJECT"] = "CONDITIONAL"
    new_probability: float = Field(50, ge=0, le=100, description="New approval probability")
    probability_change: float = Field(0, description="Change in probability")
    feasibility: Literal["EASY", "MODERATE", "DIFFICULT", "VERY_DIFFICULT"] = "MODERATE"
    timeframe: str = Field("", description="Time to achieve")
    
    @field_validator('new_probability', 'probability_change', mode='before')
    @classmethod
    def coerce_probabilities(cls, v):
        if isinstance(v, str):
            v = v.replace('%', '').strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v if v is not None else 0.0
    
    @field_validator('predicted_outcome', mode='before')
    @classmethod
    def coerce_outcome(cls, v):
        valid = ["APPROVE", "CONDITIONAL", "REJECT"]
        if v in valid:
            return v
        v_upper = str(v).upper()
        if "APPROVE" in v_upper or "ACCEPT" in v_upper:
            return "APPROVE"
        elif "REJECT" in v_upper or "DENY" in v_upper:
            return "REJECT"
        return "CONDITIONAL"
    
    @field_validator('feasibility', mode='before')
    @classmethod
    def coerce_feasibility(cls, v):
        valid = ["EASY", "MODERATE", "DIFFICULT", "VERY_DIFFICULT"]
        if v in valid:
            return v
        v_upper = str(v).upper().replace(" ", "_").replace("-", "_")
        if "VERY" in v_upper or "EXTREME" in v_upper:
            return "VERY_DIFFICULT"
        elif "DIFFICULT" in v_upper or "HARD" in v_upper:
            return "DIFFICULT"
        elif "EASY" in v_upper or "SIMPLE" in v_upper:
            return "EASY"
        return "MODERATE"


class SensitivityItem(BaseModel):
    """Sensitivity analysis for a metric."""
    metric: str = Field(..., description="Metric name")
    impact_score: float = Field(0, ge=0, le=100, description="Impact score 0-100")
    current_value: Any = Field(..., description="Current value")
    threshold_value: Any = Field(None, description="Threshold for approval")
    improvement_needed: str = Field("", description="Description of needed change")
    
    @field_validator('impact_score', mode='before')
    @classmethod
    def coerce_impact(cls, v):
        if isinstance(v, str):
            v = v.replace('%', '').strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v if v is not None else 0.0


class OptimalPathStep(BaseModel):
    """A step in the optimal path to approval."""
    step_number: int = Field(..., description="Step number")
    action: str = Field(..., description="Action to take")
    expected_impact: str = Field(..., description="Expected impact")
    difficulty: Literal["EASY", "MODERATE", "HARD"] = "MODERATE"


class OptimalPath(BaseModel):
    """The optimal path to approval."""
    description: str = Field(..., description="Summary of approach")
    steps: list[OptimalPathStep] = Field(default_factory=list)
    estimated_timeframe: str = Field("", description="Total time estimate")
    success_probability: float = Field(50, ge=0, le=100)


class RiskFactor(BaseModel):
    """A risk factor that could derail improvement."""
    risk: str = Field(..., description="Risk description")
    likelihood: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    potential_impact: str = Field(..., description="Impact if realized")


class CurrentAssessment(BaseModel):
    """Current assessment of the application."""
    approval_probability: float = Field(50, ge=0, le=100)
    current_outcome: Literal["LIKELY_APPROVE", "BORDERLINE", "LIKELY_REJECT"] = "BORDERLINE"
    limiting_factors: list[str] = Field(default_factory=list)


class ScenarioResponse(BaseModel):
    """Response from the Scenario Agent."""
    agent_name: str = Field(default="ScenarioAgent", description="Name of the agent")
    current_assessment: CurrentAssessment = Field(default_factory=CurrentAssessment)
    scenarios: list[Scenario] = Field(default_factory=list)
    sensitivity_analysis: list[SensitivityItem] = Field(default_factory=list)
    optimal_path: Optional[OptimalPath] = None
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    cases_modeled: int = Field(0, description="Cases used for modeling")
    processing_time_ms: float = Field(0, description="Processing time in milliseconds")


class ScenarioRequest(BaseModel):
    """Request body for custom scenario modeling."""
    custom_scenarios: Optional[list[dict]] = Field(
        None, 
        description="Custom scenarios to model",
        json_schema_extra={
            "examples": [[{
                "description": "If I pay off debt",
                "changes": [{"metric": "debt_to_income_ratio", "to_value": 0.30}]
            }]]
        }
    )
