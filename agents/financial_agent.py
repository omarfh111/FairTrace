"""
Financial Metrics Agent - Analyse les ratios et métriques financières.
Compare avec les cas historiques similaires pour évaluer la santé financière.
Uses LangChain for automatic LangSmith tracing.
"""

import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, THRESHOLDS
from .schemas import AgentAnalysis, RiskLevel, SimilarCase

# Ensure LangSmith tracing is enabled from environment
os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    """Get ChatOpenAI with LangSmith tracing enabled."""
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


FINANCIAL_SYSTEM_PROMPT = """Tu es un agent expert en analyse financière pour les décisions de crédit.
Tu analyses les métriques financières d'une demande de crédit et les compares avec des cas historiques similaires.

Tu dois:
1. Évaluer les ratios financiers clés
2. Comparer avec les seuils standards et les cas similaires
3. Identifier les forces et faiblesses financières
4. Donner un niveau de risque: LOW, MEDIUM, HIGH, ou CRITICAL

Réponds UNIQUEMENT en JSON valide avec cette structure:
{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "red_flags": ["flag1", "flag2"],
    "positive_signals": ["signal1", "signal2"],
    "recommendation": "ta recommandation"
}"""


def analyze_client_financials(application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Analyze financial metrics for a client application."""
    
    similar_approved = [c for c in similar_cases if c['payload'].get('outcome') == 'APPROVED']
    similar_rejected = [c for c in similar_cases if c['payload'].get('outcome') == 'REJECTED']
    
    metrics_summary = f"""
=== DEMANDE ACTUELLE ===
- Revenu annuel: €{application.get('income_annual', 0):,.0f}
- Ratio dette/revenu: {application.get('debt_to_income_ratio', 0)*100:.1f}%
- Paiements manqués (12 mois): {application.get('missed_payments_last_12m', 0)}
- Ancienneté emploi: {application.get('job_tenure_years', 0)} ans
- Utilisation crédit: {application.get('credit_utilization_avg', 0)*100:.1f}%
- Type contrat: {application.get('contract_type', 'Unknown')}

=== SEUILS DE RÉFÉRENCE ===
- Max dette/revenu acceptable: {THRESHOLDS['max_debt_to_income']*100}%
- Max paiements manqués: {THRESHOLDS['max_missed_payments']}

=== CAS SIMILAIRES APPROUVÉS ({len(similar_approved)}) ===
"""
    
    for i, case in enumerate(similar_approved[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score similarité: {case['score']:.2f}):
  - Revenu: €{p.get('income_annual', 0):,.0f}
  - Dette/revenu: {p.get('debt_to_income_ratio', 0)*100:.1f}%
  - Paiements manqués: {p.get('missed_payments_last_12m', 0)}
"""

    metrics_summary += f"\n=== CAS SIMILAIRES REJETÉS ({len(similar_rejected)}) ===\n"
    
    for i, case in enumerate(similar_rejected[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score similarité: {case['score']:.2f}):
  - Revenu: €{p.get('income_annual', 0):,.0f}
  - Dette/revenu: {p.get('debt_to_income_ratio', 0)*100:.1f}%
  - Paiements manqués: {p.get('missed_payments_last_12m', 0)}
"""

    # Call LLM with LangChain (auto-traced)
    llm = get_llm()
    messages = [
        SystemMessage(content=FINANCIAL_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse ces métriques financières:\n{metrics_summary}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": "Financial Agent - Client", "tags": ["financial", "client"]}
    )
    
    # Parse JSON with error handling
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        result = {
            "risk_level": "MEDIUM",
            "confidence": 0.5,
            "key_findings": ["Analyse en cours"],
            "red_flags": [],
            "positive_signals": [],
            "recommendation": "Analyse manuelle recommandée"
        }
    
    cited_cases = []
    for case in similar_cases[:3]:
        cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={
                "income": case['payload'].get('income_annual'),
                "dti": case['payload'].get('debt_to_income_ratio'),
                "missed_payments": case['payload'].get('missed_payments_last_12m')
            },
            summary=f"Client avec revenu €{case['payload'].get('income_annual', 0):,.0f}"
        ))
    
    return AgentAnalysis(
        agent_name="Financial Metrics Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('red_flags', []),
        positive_signals=result.get('positive_signals', []),
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )


def analyze_startup_financials(application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Analyze financial metrics for a startup application."""
    
    similar_approved = [c for c in similar_cases if c['payload'].get('outcome') == 'APPROVED']
    similar_rejected = [c for c in similar_cases if c['payload'].get('outcome') == 'REJECTED']
    
    metrics_summary = f"""
=== STARTUP ACTUELLE ===
- ARR actuel: ${application.get('arr_current', 0):,.0f}
- Croissance ARR YoY: {application.get('arr_growth_yoy', 0)*100:.0f}%
- Burn rate mensuel: ${application.get('burn_rate_monthly', 0):,.0f}
- Runway: {application.get('runway_months', 0):.1f} mois
- Burn multiple: {application.get('burn_multiple', 0):.2f}
- Ratio CAC/LTV: {application.get('cac_ltv_ratio', 0):.2f}
- Churn mensuel: {application.get('churn_rate_monthly', 0)*100:.2f}%
- VC backing: {'Oui' if application.get('vc_backing') else 'Non'}
- Expérience fondateur: {application.get('founder_experience_years', 0)} ans

=== SEUILS DE RÉFÉRENCE ===
- Min runway acceptable: {THRESHOLDS['min_runway_months']} mois
- Max burn multiple: {THRESHOLDS['max_burn_multiple']}

=== CAS SIMILAIRES APPROUVÉS ({len(similar_approved)}) ===
"""
    
    for i, case in enumerate(similar_approved[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score: {case['score']:.2f}):
  - ARR: ${p.get('arr_current', 0):,.0f}, Runway: {p.get('runway_months', 0):.1f} mois
  - Burn multiple: {p.get('burn_multiple', 0):.2f}
"""

    metrics_summary += f"\n=== CAS REJETÉS ({len(similar_rejected)}) ===\n"
    
    for i, case in enumerate(similar_rejected[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score: {case['score']:.2f}):
  - ARR: ${p.get('arr_current', 0):,.0f}, Runway: {p.get('runway_months', 0):.1f} mois
  - Burn multiple: {p.get('burn_multiple', 0):.2f}
"""

    llm = get_llm()
    messages = [
        SystemMessage(content=FINANCIAL_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse ces métriques financières de startup:\n{metrics_summary}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": "Financial Agent - Startup", "tags": ["financial", "startup"]}
    )
    
    result = json.loads(response.content)
    
    cited_cases = []
    for case in similar_cases[:3]:
        cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={
                "arr": case['payload'].get('arr_current'),
                "runway": case['payload'].get('runway_months'),
                "burn_multiple": case['payload'].get('burn_multiple')
            },
            summary=f"Startup {case['payload'].get('sector', 'Unknown')} avec runway {case['payload'].get('runway_months', 0):.1f} mois"
        ))
    
    return AgentAnalysis(
        agent_name="Financial Metrics Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('red_flags', []),
        positive_signals=result.get('positive_signals', []),
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )


def analyze_enterprise_financials(application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Analyze financial metrics for an enterprise application."""
    
    similar_approved = [c for c in similar_cases if c['payload'].get('outcome') == 'APPROVED']
    similar_rejected = [c for c in similar_cases if c['payload'].get('outcome') in ['REJECTED', 'BANKRUPT']]
    
    z_score = application.get('altman_z_score', 0)
    if z_score > THRESHOLDS['altman_safe_zone']:
        altman_zone = "Zone Sûre (>3.0)"
    elif z_score > THRESHOLDS['altman_grey_zone']:
        altman_zone = "Zone Grise (1.8-3.0)"
    else:
        altman_zone = "Zone de Détresse (<1.8)"
    
    metrics_summary = f"""
=== ENTREPRISE ACTUELLE ===
- Revenu annuel: €{application.get('revenue_annual', 0):,.0f}
- Marge nette: {application.get('net_profit_margin', 0)*100:.1f}%
- Current ratio: {application.get('current_ratio', 0):.2f}
- Quick ratio: {application.get('quick_ratio', 0):.2f}
- Ratio dette/capitaux: {application.get('debt_to_equity', 0):.2f}
- Couverture intérêts: {application.get('interest_coverage_ratio', 0):.2f}
- Score Altman Z: {z_score:.2f} ({altman_zone})
- Score ESG: {application.get('esg_risk_score', 0):.1f}/100
- Procès actifs: {application.get('legal_lawsuits_active', 0)}

=== SEUILS DE RÉFÉRENCE ===
- Zone sûre Altman: >{THRESHOLDS['altman_safe_zone']}
- Zone grise: {THRESHOLDS['altman_grey_zone']}-{THRESHOLDS['altman_safe_zone']}
- Min current ratio: {THRESHOLDS['min_current_ratio']}

=== CAS SIMILAIRES APPROUVÉS ({len(similar_approved)}) ===
"""
    
    for i, case in enumerate(similar_approved[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score: {case['score']:.2f}):
  - Revenu: €{p.get('revenue_annual', 0):,.0f}, Z-Score: {p.get('altman_z_score', 0):.2f}
  - Current ratio: {p.get('current_ratio', 0):.2f}
"""

    metrics_summary += f"\n=== CAS REJETÉS/FAILLITE ({len(similar_rejected)}) ===\n"
    
    for i, case in enumerate(similar_rejected[:3], 1):
        p = case['payload']
        metrics_summary += f"""
Cas {i} (score: {case['score']:.2f}, outcome: {p.get('outcome')}):
  - Revenu: €{p.get('revenue_annual', 0):,.0f}, Z-Score: {p.get('altman_z_score', 0):.2f}
  - Current ratio: {p.get('current_ratio', 0):.2f}
"""

    llm = get_llm()
    messages = [
        SystemMessage(content=FINANCIAL_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse ces métriques financières d'entreprise:\n{metrics_summary}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": "Financial Agent - Enterprise", "tags": ["financial", "enterprise"]}
    )
    
    result = json.loads(response.content)
    
    cited_cases = []
    for case in similar_cases[:3]:
        cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={
                "revenue": case['payload'].get('revenue_annual'),
                "altman_z": case['payload'].get('altman_z_score'),
                "current_ratio": case['payload'].get('current_ratio')
            },
            summary=f"Entreprise {case['payload'].get('industry_code', 'Unknown')} avec Z-Score {case['payload'].get('altman_z_score', 0):.2f}"
        ))
    
    return AgentAnalysis(
        agent_name="Financial Metrics Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('red_flags', []),
        positive_signals=result.get('positive_signals', []),
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )


def analyze(application_type: str, application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Main entry point for financial analysis."""
    if application_type == "client":
        return analyze_client_financials(application, similar_cases)
    elif application_type == "startup":
        return analyze_startup_financials(application, similar_cases)
    elif application_type == "enterprise":
        return analyze_enterprise_financials(application, similar_cases)
    else:
        raise ValueError(f"Unknown application type: {application_type}")
