"""
Decision Routes - Credit Decision API Endpoints

Endpoints:
- POST /decisions - Submit application for credit decision
- GET /decisions/{decision_id} - Retrieve a previous decision
- GET /decisions/{decision_id}/advisor - Get improvement recommendations (on-demand)
- GET /decisions/{decision_id}/narrative - Get historical narratives (on-demand)
- GET /decisions/{decision_id}/comparator - Get gap analysis vs. approved cases (on-demand)
- POST /decisions/{decision_id}/scenario - Run what-if scenario modeling (on-demand)
"""

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from langsmith import traceable

from api.schemas import (
    DecisionRequest,
    DecisionResponse,
    AgentVerdict,
    FinalDecision,
    EvidenceItem,
    ErrorResponse,
    AdvisorResponse,
    NarrativeResponse,
    ImprovementArea,
    Recommendation,
    KeyPattern,
    Story,
    ComparatorResponse,
    MetricComparison,
    GapItem,
    StrengthItem,
    ScenarioResponse,
    ScenarioRequest,
    Scenario,
    ScenarioChange,
    SensitivityItem,
    OptimalPath,
    OptimalPathStep,
    RiskFactor,
    CurrentAssessment
)

# Import the decision pipeline
try:
    from graph.decision_graph import run_credit_decision_async
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False

# Import database repository
try:
    from db import repository as db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  Database module not available - using in-memory fallback")

# Import on-demand agents
try:
    from agents.advisor_agent import AdvisorAgent
    from agents.narrative_agent import NarrativeAgent
    from agents.comparator_agent import ComparatorAgent
    from agents.scenario_agent import ScenarioAgent
    ONDEMAND_AGENTS_AVAILABLE = True
except ImportError:
    ONDEMAND_AGENTS_AVAILABLE = False

# In-memory fallback storage (used if database not available)
_decision_store: dict[str, DecisionResponse] = {}
_application_store: dict[str, dict] = {}

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _detect_application_type(application: dict) -> str:
    """Auto-detect application type from fields."""
    if "client_id" in application or "debt_to_income_ratio" in application:
        return "client"
    elif "startup_id" in application or "burn_multiple" in application:
        return "startup"
    elif "enterprise_id" in application or "altman_z_score" in application:
        return "enterprise"
    else:
        # Default based on common fields
        if "arr_current" in application or "sector" in application:
            return "startup"
        elif "income_annual" in application:
            return "client"
        else:
            return "client"  # Default


def _convert_verdict(raw_verdict: dict | None) -> AgentVerdict | None:
    """Convert raw verdict dict to AgentVerdict schema."""
    if not raw_verdict:
        return None
    
    # Convert evidence
    evidence = []
    for e in raw_verdict.get("evidence", []):
        evidence.append(EvidenceItem(
            entity_id=str(e.get("entity_id", "")),
            similarity_score=float(e.get("similarity_score", 0)),
            outcome=str(e.get("outcome", "UNKNOWN")),
            key_factors=e.get("key_factors", [])
        ))
    
    return AgentVerdict(
        agent_name=raw_verdict.get("agent_name", "Unknown"),
        recommendation=raw_verdict.get("recommendation", "ESCALATE"),
        confidence=raw_verdict.get("confidence", "LOW"),
        risk_level=raw_verdict.get("risk_level", "MEDIUM"),
        reasoning=raw_verdict.get("reasoning", ""),
        key_concerns=raw_verdict.get("key_concerns", []),
        mitigating_factors=raw_verdict.get("mitigating_factors", []),
        evidence=evidence
    )


def _convert_final_decision(raw_decision: dict | None) -> FinalDecision:
    """Convert raw decision dict to FinalDecision schema."""
    if not raw_decision:
        return FinalDecision(
            recommendation="ESCALATE",
            confidence="LOW",
            risk_level="MEDIUM",
            reasoning="Unable to process decision",
            conditions=[],
            agent_agreement="SPLIT",
            key_factors=[]
        )
    
    return FinalDecision(
        recommendation=raw_decision.get("recommendation", "ESCALATE"),
        confidence=raw_decision.get("confidence", "LOW"),
        risk_level=raw_decision.get("risk_level", "MEDIUM"),
        reasoning=raw_decision.get("reasoning", ""),
        conditions=raw_decision.get("conditions", []),
        agent_agreement=raw_decision.get("agent_agreement", "SPLIT"),
        key_factors=raw_decision.get("key_factors", [])
    )


@router.post(
    "",
    response_model=DecisionResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Submit Credit Application",
    description="Submit an application for credit decision. The system will run all agents and return a synthesized decision."
)
@traceable(name="api_credit_decision", run_type="chain")
async def create_decision(request: DecisionRequest) -> DecisionResponse:
    """
    Submit a credit application for evaluation.
    
    The system will:
    1. Detect application type (or use specified type)
    2. Run Risk, Fairness, and Trajectory agents in parallel
    3. Synthesize a final decision via the Orchestrator
    4. Return the complete decision with all verdicts
    """
    start_time = time.time()
    decision_id = str(uuid.uuid4())
    
    # Detect application type
    if request.application_type == "auto":
        app_type = _detect_application_type(request.application)
    else:
        app_type = request.application_type
    
    try:
        if not GRAPH_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Decision graph not available. Check agent imports."
            )
        
        # Run the decision pipeline ASYNC for true parallelism
        result = await run_credit_decision_async(request.application)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response schema
        response = DecisionResponse(
            decision_id=decision_id,
            application_type=app_type,
            timestamp=datetime.now(timezone.utc),
            risk_verdict=_convert_verdict(result.get("risk_verdict")),
            fairness_verdict=_convert_verdict(result.get("fairness_verdict")),
            trajectory_verdict=_convert_verdict(result.get("trajectory_verdict")),
            final_decision=_convert_final_decision(result.get("final_decision")),
            processing_time_ms=processing_time,
            error=result.get("error")
        )
        
        # Save to database (async)
        if DB_AVAILABLE:
            await db.save_decision(
                decision_id=decision_id,
                application=request.application,
                application_type=app_type,
                risk_verdict=result.get("risk_verdict"),
                fairness_verdict=result.get("fairness_verdict"),
                trajectory_verdict=result.get("trajectory_verdict"),
                final_decision=result.get("final_decision")
            )
        else:
            # Fallback to in-memory
            _decision_store[decision_id] = response
            _application_store[decision_id] = request.application.copy()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        
        # Return error response
        response = DecisionResponse(
            decision_id=decision_id,
            application_type=app_type,
            timestamp=datetime.now(timezone.utc),
            risk_verdict=None,
            fairness_verdict=None,
            trajectory_verdict=None,
            final_decision=FinalDecision(
                recommendation="ESCALATE",
                confidence="LOW",
                risk_level="MEDIUM",
                reasoning=f"Error during processing: {str(e)}",
                conditions=[],
                agent_agreement="SPLIT",
                key_factors=["Processing error"]
            ),
            processing_time_ms=processing_time,
            error=str(e)
        )
        
        # Save error state to database too
        if DB_AVAILABLE:
            await db.save_decision(
                decision_id=decision_id,
                application=request.application,
                application_type=app_type,
                final_decision={"error": str(e), "decision": "ESCALATE"}
            )
        else:
            _decision_store[decision_id] = response
        
        return response


@router.get(
    "/{decision_id}",
    response_model=DecisionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Decision not found"}
    },
    summary="Get Decision by ID",
    description="Retrieve a previously made credit decision by its ID."
)
async def get_decision(decision_id: str) -> DecisionResponse:
    """Retrieve a previous decision by ID."""
    # Try database first
    if DB_AVAILABLE:
        db_result = await db.get_decision(decision_id)
        if db_result:
            # Convert database result to response schema
            return DecisionResponse(
                decision_id=db_result["decision_id"],
                application_type=db_result["application_type"],
                timestamp=datetime.fromisoformat(db_result["created_at"]) if db_result.get("created_at") else datetime.now(timezone.utc),
                risk_verdict=_convert_verdict(db_result.get("risk_verdict")),
                fairness_verdict=_convert_verdict(db_result.get("fairness_verdict")),
                trajectory_verdict=_convert_verdict(db_result.get("trajectory_verdict")),
                final_decision=_convert_final_decision(db_result.get("final_decision")),
                processing_time_ms=0,
                error=None
            )
    
    # Fallback to in-memory
    if decision_id in _decision_store:
        return _decision_store[decision_id]
    
    raise HTTPException(
        status_code=404,
        detail=f"Decision {decision_id} not found"
    )


@router.get(
    "",
    response_model=list[DecisionResponse],
    summary="List Recent Decisions",
    description="List the most recent credit decisions (up to 100)."
)
async def list_decisions(limit: int = 10) -> list[DecisionResponse]:
    """List recent decisions."""
    decisions = list(_decision_store.values())
    # Sort by timestamp descending
    decisions.sort(key=lambda d: d.timestamp, reverse=True)
    return decisions[:min(limit, 100)]


# =============================================================================
# ON-DEMAND AGENT ENDPOINTS
# =============================================================================

async def _get_application_for_agent(decision_id: str) -> dict:
    """Helper to get application data from database or in-memory store."""
    # Try database first
    if DB_AVAILABLE:
        application = await db.get_application(decision_id)
        if application:
            return application
    
    # Fallback to in-memory
    if decision_id in _application_store:
        return _application_store[decision_id]
    
    raise HTTPException(
        status_code=404,
        detail=f"Original application data not found for decision {decision_id}"
    )


async def _check_decision_exists(decision_id: str) -> bool:
    """Check if a decision exists in database or in-memory store."""
    if DB_AVAILABLE:
        result = await db.get_decision(decision_id)
        if result:
            return True
    return decision_id in _decision_store


@router.get(
    "/{decision_id}/advisor",
    response_model=AdvisorResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Decision not found"},
        503: {"model": ErrorResponse, "description": "Advisor agent not available"}
    },
    summary="Get Improvement Recommendations",
    description="Get actionable recommendations to improve the application's chances of approval."
)
@traceable(name="api_advisor_agent", run_type="chain")
async def get_advisor_analysis(decision_id: str, force_refresh: bool = False) -> AdvisorResponse:
    """
    Get improvement recommendations from the Advisor Agent.
    
    This on-demand endpoint provides actionable suggestions to improve
    an application that received CONDITIONAL or REJECT decisions.
    Results are cached for efficiency.
    """
    # Check if decision exists
    if not await _check_decision_exists(decision_id):
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id} not found"
        )
    
    # Check database cache unless force refresh
    if not force_refresh and DB_AVAILABLE:
        cached = await db.get_agent_cache(decision_id, "advisor")
        if cached:
            return AdvisorResponse(**cached)
    
    if not ONDEMAND_AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Advisor agent not available. Check agent imports."
        )
    
    # Get original application
    application = await _get_application_for_agent(decision_id)
    
    # Get original decision for context
    if DB_AVAILABLE:
        db_decision = await db.get_decision(decision_id)
        if db_decision and db_decision.get("final_decision"):
            original_context = {
                "recommendation": db_decision["final_decision"].get("decision", "UNKNOWN"),
                "key_concerns": db_decision["final_decision"].get("key_factors", [])
            }
        else:
            original_context = {"recommendation": "UNKNOWN", "key_concerns": []}
    elif decision_id in _decision_store:
        original_decision = _decision_store[decision_id]
        original_context = {
            "recommendation": original_decision.final_decision.recommendation,
            "key_concerns": original_decision.final_decision.key_factors
        }
    else:
        original_context = {"recommendation": "UNKNOWN", "key_concerns": []}
    
    start_time = time.time()
    
    try:
        # Run the advisor agent
        advisor = AdvisorAgent()
        result = advisor.run(application, original_context)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response schema
        response = AdvisorResponse(
            agent_name=result.get("agent_name", "AdvisorAgent"),
            improvement_areas=[
                ImprovementArea(**area) for area in result.get("improvement_areas", [])
            ],
            recommendations=[
                Recommendation(**rec) for rec in result.get("recommendations", [])
            ],
            similar_approved_characteristics=result.get("similar_approved_characteristics", []),
            overall_outlook=result.get("overall_outlook", "CHALLENGING"),
            confidence=result.get("confidence", "MEDIUM"),
            success_cases_analyzed=result.get("success_cases_analyzed", 0),
            evidence=[
                EvidenceItem(
                    entity_id=str(e.get("entity_id", "")),
                    similarity_score=float(e.get("similarity_score", 0)),
                    outcome=str(e.get("outcome", "UNKNOWN"))
                ) for e in result.get("evidence", [])
            ],
            processing_time_ms=processing_time
        )
        
        # Cache in database
        if DB_AVAILABLE:
            await db.save_agent_cache(decision_id, "advisor", response.model_dump())
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running advisor agent: {str(e)}"
        )



@router.get(
    "/{decision_id}/narrative",
    response_model=NarrativeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Decision not found"},
        503: {"model": ErrorResponse, "description": "Narrative agent not available"}
    },
    summary="Get Historical Narratives",
    description="Get stories and insights extracted from similar historical cases."
)
@traceable(name="api_narrative_agent", run_type="chain")
async def get_narrative_analysis(decision_id: str, force_refresh: bool = False) -> NarrativeResponse:
    """
    Get narrative insights from the Narrative Agent.
    
    This on-demand endpoint provides compelling stories, patterns, and
    lessons learned from similar historical cases.
    Results are cached for efficiency.
    """
    # Check if decision exists
    if not await _check_decision_exists(decision_id):
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id} not found"
        )
    
    # Check database cache unless force refresh
    if not force_refresh and DB_AVAILABLE:
        cached = await db.get_agent_cache(decision_id, "narrative")
        if cached:
            return NarrativeResponse(**cached)
    
    if not ONDEMAND_AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Narrative agent not available. Check agent imports."
        )
    
    # Get original application
    application = await _get_application_for_agent(decision_id)
    
    start_time = time.time()
    
    try:
        # Run the narrative agent
        narrative = NarrativeAgent()
        result = narrative.run(application)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response schema
        response = NarrativeResponse(
            agent_name=result.get("agent_name", "NarrativeAgent"),
            narrative_summary=result.get("narrative_summary", ""),
            key_patterns=[
                KeyPattern(**pattern) for pattern in result.get("key_patterns", [])
            ],
            success_stories=[
                Story(**story) for story in result.get("success_stories", [])
            ],
            cautionary_tales=[
                Story(**story) for story in result.get("cautionary_tales", [])
            ],
            industry_context=result.get("industry_context", ""),
            lessons_learned=result.get("lessons_learned", []),
            confidence=result.get("confidence", "MEDIUM"),
            cases_analyzed=result.get("cases_analyzed", 0),
            outcome_distribution=result.get("outcome_distribution", {}),
            processing_time_ms=processing_time
        )
        
        # Cache in database
        if DB_AVAILABLE:
            await db.save_agent_cache(decision_id, "narrative", response.model_dump())
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running narrative agent: {str(e)}"
        )


@router.get(
    "/{decision_id}/comparator",
    response_model=ComparatorResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Decision not found"},
        503: {"model": ErrorResponse, "description": "Comparator agent not available"}
    },
    summary="Get Gap Analysis",
    description="Compare application against successful cases to identify gaps and strengths."
)
@traceable(name="api_comparator_agent", run_type="chain")
async def get_comparator_analysis(decision_id: str, force_refresh: bool = False) -> ComparatorResponse:
    """
    Get gap analysis from the Comparator Agent.
    
    This on-demand endpoint compares the application against similar
    approved/funded cases to show exactly where improvements are needed.
    Results are cached for efficiency.
    """
    # Check if decision exists
    if not await _check_decision_exists(decision_id):
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id} not found"
        )
    
    # Check database cache unless force refresh
    if not force_refresh and DB_AVAILABLE:
        cached = await db.get_agent_cache(decision_id, "comparator")
        if cached:
            return ComparatorResponse(**cached)
    
    if not ONDEMAND_AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Comparator agent not available. Check agent imports."
        )
    
    # Get original application
    application = await _get_application_for_agent(decision_id)
    
    start_time = time.time()
    
    try:
        # Run the comparator agent
        comparator = ComparatorAgent()
        result = comparator.run(application)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response schema
        response = ComparatorResponse(
            agent_name=result.get("agent_name", "ComparatorAgent"),
            overall_gap_score=result.get("overall_gap_score", 50),
            metric_comparisons=[
                MetricComparison(**mc) for mc in result.get("metric_comparisons", [])
            ],
            strengths=[
                StrengthItem(**s) for s in result.get("strengths", [])
            ],
            gaps=[
                GapItem(**g) for g in result.get("gaps", [])
            ],
            percentile_ranking=result.get("percentile_ranking", {}),
            closest_approved_case=result.get("closest_approved_case"),
            executive_summary=result.get("executive_summary", ""),
            confidence=result.get("confidence", "MEDIUM"),
            approved_cases_analyzed=result.get("approved_cases_analyzed", 0),
            processing_time_ms=processing_time
        )
        
        # Cache in database
        if DB_AVAILABLE:
            await db.save_agent_cache(decision_id, "comparator", response.model_dump())
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running comparator agent: {str(e)}"
        )


@router.post(
    "/{decision_id}/scenario",
    response_model=ScenarioResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Decision not found"},
        503: {"model": ErrorResponse, "description": "Scenario agent not available"}
    },
    summary="Run What-If Scenarios",
    description="Model different scenarios and their potential impact on the decision outcome."
)
@traceable(name="api_scenario_agent", run_type="chain")
async def run_scenario_analysis(
    decision_id: str, 
    request: ScenarioRequest | None = Body(None),
    force_refresh: bool = False
) -> ScenarioResponse:
    """
    Run what-if scenario analysis with the Scenario Agent.
    
    This on-demand endpoint models different scenarios to show how
    changes to the application would affect the decision outcome.
    Optionally accepts custom scenarios to model.
    Results are cached for efficiency (cache key includes scenarios).
    """
    # Check if decision exists
    if not await _check_decision_exists(decision_id):
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id} not found"
        )
    
    # Build cache key (include custom scenarios if provided)
    custom_scenarios = None
    cache_extra = None
    if request and request.custom_scenarios:
        custom_scenarios = request.custom_scenarios
        cache_extra = {"scenarios": custom_scenarios}
    
    # Check database cache unless force refresh
    if not force_refresh and DB_AVAILABLE:
        cached = await db.get_agent_cache(decision_id, "scenario", cache_extra)
        if cached:
            return ScenarioResponse(**cached)
    
    if not ONDEMAND_AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Scenario agent not available. Check agent imports."
        )
    
    # Get original application
    application = await _get_application_for_agent(decision_id)
    
    start_time = time.time()
    
    try:
        # Run the scenario agent
        scenario_agent = ScenarioAgent()
        result = scenario_agent.run(application, custom_scenarios)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response schema
        current_assessment = result.get("current_assessment", {})
        optimal_path_data = result.get("optimal_path")
        
        response = ScenarioResponse(
            agent_name=result.get("agent_name", "ScenarioAgent"),
            current_assessment=CurrentAssessment(
                approval_probability=current_assessment.get("approval_probability", 50),
                current_outcome=current_assessment.get("current_outcome", "BORDERLINE"),
                limiting_factors=current_assessment.get("limiting_factors", [])
            ),
            scenarios=[
                Scenario(
                    scenario_name=s.get("scenario_name", ""),
                    changes=[ScenarioChange(**c) for c in s.get("changes", [])],
                    predicted_outcome=s.get("predicted_outcome", "CONDITIONAL"),
                    new_probability=s.get("new_probability", 50),
                    probability_change=s.get("probability_change", 0),
                    feasibility=s.get("feasibility", "MODERATE"),
                    timeframe=s.get("timeframe", "")
                ) for s in result.get("scenarios", [])
            ],
            sensitivity_analysis=[
                SensitivityItem(**si) for si in result.get("sensitivity_analysis", [])
            ],
            optimal_path=OptimalPath(
                description=optimal_path_data.get("description", ""),
                steps=[OptimalPathStep(**step) for step in optimal_path_data.get("steps", [])],
                estimated_timeframe=optimal_path_data.get("estimated_timeframe", ""),
                success_probability=optimal_path_data.get("success_probability", 50)
            ) if optimal_path_data else None,
            risk_factors=[
                RiskFactor(**rf) for rf in result.get("risk_factors", [])
            ],
            confidence=result.get("confidence", "MEDIUM"),
            cases_modeled=result.get("cases_modeled", 0),
            processing_time_ms=processing_time
        )
        
        # Cache in database
        if DB_AVAILABLE:
            await db.save_agent_cache(decision_id, "scenario", response.model_dump(), cache_extra)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running scenario agent: {str(e)}"
        )

