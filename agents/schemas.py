"""
Schémas Pydantic pour le système multi-agents de décision de crédit.
Définit les structures de données pour les applications, analyses et décisions.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationType(str, Enum):
    """Type de demandeur de crédit."""
    CLIENT = "client"
    STARTUP = "startup"
    ENTERPRISE = "enterprise"


class DecisionOutcome(str, Enum):
    """Décision finale possible."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW_NEEDED = "REVIEW_NEEDED"


class RiskLevel(str, Enum):
    """Niveau de risque détecté."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# INPUT SCHEMAS
# =============================================================================
class ClientApplication(BaseModel):
    """Demande de crédit d'un particulier."""
    client_id: Optional[str] = None
    income_annual: float = Field(..., description="Revenu annuel en euros")
    debt_to_income_ratio: float = Field(..., description="Ratio dette/revenu (0-1)")
    missed_payments_last_12m: int = Field(default=0, description="Paiements manqués")
    job_tenure_years: float = Field(..., description="Ancienneté dans l'emploi")
    age: int = Field(..., description="Âge du demandeur")
    contract_type: str = Field(default="CDI", description="Type de contrat")
    loan_purpose: str = Field(..., description="Objectif du prêt")
    credit_history: Optional[str] = Field(None, description="Historique textuel")
    credit_utilization_avg: float = Field(default=0.3, description="Utilisation crédit moyenne")
    
    # Payslip structure (optional)
    net_monthly: Optional[float] = None
    basic_part: Optional[float] = None
    variable_part: Optional[float] = None


class StartupApplication(BaseModel):
    """Demande de financement d'une startup."""
    startup_id: Optional[str] = None
    sector: str = Field(..., description="Secteur d'activité")
    founder_experience_years: int = Field(..., description="Expérience du fondateur")
    vc_backing: bool = Field(default=False, description="Financé par VC")
    arr_current: float = Field(..., description="ARR actuel en euros")
    arr_growth_yoy: float = Field(..., description="Croissance ARR YoY (0-1)")
    burn_rate_monthly: float = Field(..., description="Burn rate mensuel")
    runway_months: float = Field(..., description="Runway en mois")
    cac_ltv_ratio: float = Field(..., description="Ratio CAC/LTV")
    churn_rate_monthly: float = Field(default=0.05, description="Taux de churn mensuel")
    burn_multiple: float = Field(..., description="Burn multiple")
    pitch_narrative: Optional[str] = Field(None, description="Pitch de la startup")


class EnterpriseApplication(BaseModel):
    """Demande de financement d'une entreprise."""
    enterprise_id: Optional[str] = None
    industry_code: str = Field(..., description="Code industrie")
    revenue_annual: float = Field(..., description="Revenu annuel")
    net_profit_margin: float = Field(..., description="Marge nette (0-1)")
    current_ratio: float = Field(..., description="Current ratio")
    quick_ratio: float = Field(..., description="Quick ratio")
    debt_to_equity: float = Field(..., description="Ratio dette/capitaux propres")
    interest_coverage_ratio: float = Field(..., description="Ratio couverture intérêts")
    altman_z_score: float = Field(..., description="Score Altman Z")
    esg_risk_score: float = Field(default=50.0, description="Score risque ESG (0-100)")
    legal_lawsuits_active: int = Field(default=0, description="Procès en cours")
    
    # CEO Profile
    ceo_name: Optional[str] = None
    ceo_experience_years: Optional[int] = None
    ceo_track_record: Optional[str] = None
    
    # Textual
    annual_report_risk_section: Optional[str] = None


# =============================================================================
# AGENT OUTPUT SCHEMAS
# =============================================================================
class SimilarCase(BaseModel):
    """Un cas similaire récupéré de la base."""
    case_id: str
    similarity_score: float
    outcome: str
    key_metrics: dict
    summary: str


class AgentAnalysis(BaseModel):
    """Résultat d'analyse d'un agent spécialisé."""
    agent_name: str
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0, le=1, description="Confiance dans l'analyse")
    key_findings: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    recommendation: str
    similar_cases_cited: list[SimilarCase] = Field(default_factory=list)


class PredictionResult(BaseModel):
    """Résultat de prédiction de l'agent prediction."""
    default_probability: float = Field(..., ge=0, le=1)
    time_to_risk: Optional[str] = Field(None, description="Estimation temporelle du risque")
    risk_trajectory: str = Field(default="stable", description="stable, improving, deteriorating")
    warning_signals: list[str] = Field(default_factory=list)


# =============================================================================
# FINAL DECISION SCHEMA
# =============================================================================
class FinalDecision(BaseModel):
    """Décision finale avec explications complètes."""
    application_type: ApplicationType
    decision: DecisionOutcome
    confidence: float = Field(..., ge=0, le=1)
    overall_risk_level: RiskLevel
    
    # Analyses des agents
    financial_analysis: Optional[AgentAnalysis] = None
    risk_analysis: Optional[AgentAnalysis] = None
    narrative_analysis: Optional[AgentAnalysis] = None
    prediction_result: Optional[PredictionResult] = None
    
    # Synthèse
    executive_summary: str
    key_reasons: list[str]
    similar_precedents: list[SimilarCase] = Field(default_factory=list)
    
    # Recommandations
    conditions: list[str] = Field(default_factory=list, description="Conditions si approuvé")
    next_steps: list[str] = Field(default_factory=list)
    
    # Metadata
    processing_time_seconds: Optional[float] = None
    tokens_used: Optional[int] = None


# =============================================================================
# WORKFLOW STATE (pour LangGraph)
# =============================================================================
class WorkflowState(BaseModel):
    """État du workflow multi-agents."""
    application: dict
    application_type: ApplicationType
    similar_cases: list[dict] = Field(default_factory=list)
    
    # Analyses progressives
    financial_analysis: Optional[dict] = None
    risk_analysis: Optional[dict] = None
    narrative_analysis: Optional[dict] = None
    prediction_result: Optional[dict] = None
    
    # Décision finale
    final_decision: Optional[dict] = None
    
    # Tracking
    current_step: str = "start"
    errors: list[str] = Field(default_factory=list)
