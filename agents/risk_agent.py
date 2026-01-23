"""
Risk Pattern Agent - Détection d'anomalies et patterns de risque.
Identifie les profils atypiques et les combinaisons de features dangereuses.
Uses LangChain for automatic LangSmith tracing.
"""

import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from .schemas import AgentAnalysis, RiskLevel, SimilarCase

os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


RISK_SYSTEM_PROMPT = """Tu es un agent expert en détection de risques et anomalies pour les décisions de crédit.
Tu analyses les profils de demandeurs pour détecter:
1. Des anomalies (profils atypiques qui s'écartent des patterns normaux)
2. Des combinaisons de features dangereuses (red flags)
3. Des incohérences dans les données
4. Des patterns historiquement associés aux défauts/faillites

Compare le demandeur aux cas similaires pour identifier s'il est un "outlier".

Réponds UNIQUEMENT en JSON valide avec cette structure:
{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "red_flags": ["flag1", "flag2"],
    "positive_signals": ["signal1", "signal2"],
    "recommendation": "ta recommandation",
    "anomaly_score": 0.0-1.0,
    "is_outlier": true/false
}"""


def analyze_risk_patterns(
    application_type: str,
    application: dict,
    similar_cases: list[dict]
) -> AgentAnalysis:
    """Analyze risk patterns and detect anomalies."""
    
    approved_cases = [c for c in similar_cases if c['payload'].get('outcome') == 'APPROVED']
    rejected_cases = [c for c in similar_cases if c['payload'].get('outcome') in ['REJECTED', 'BANKRUPT', 'DEFAULT']]
    
    all_scores = [c['score'] for c in similar_cases]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    if application_type == "client":
        risk_context = f"""
=== PROFIL DEMANDEUR (Client) ===
- Ratio dette/revenu: {application.get('debt_to_income_ratio', 0)*100:.1f}%
- Paiements manqués: {application.get('missed_payments_last_12m', 0)}
- Utilisation crédit: {application.get('credit_utilization_avg', 0)*100:.1f}%
- Ancienneté emploi: {application.get('job_tenure_years', 0)} ans
- Type contrat: {application.get('contract_type', 'Unknown')}
- Objectif prêt: {application.get('loan_purpose', 'Unknown')}

=== ANALYSE DE SIMILARITÉ ===
- Score moyen de similarité: {avg_score:.3f}
- Nombre de cas similaires APPROUVÉS: {len(approved_cases)}
- Nombre de cas similaires REJETÉS: {len(rejected_cases)}
"""
        red_flag_indicators = []
        if application.get('debt_to_income_ratio', 0) > 0.5:
            red_flag_indicators.append("Ratio dette/revenu très élevé (>50%)")
        if application.get('missed_payments_last_12m', 0) > 2:
            red_flag_indicators.append("Historique de paiements manqués")
        if application.get('job_tenure_years', 0) < 1 and application.get('contract_type') != 'CDI':
            red_flag_indicators.append("Emploi instable (CDD + faible ancienneté)")
        if application.get('credit_utilization_avg', 0) > 0.8:
            red_flag_indicators.append("Utilisation crédit excessive (>80%)")
            
    elif application_type == "startup":
        risk_context = f"""
=== PROFIL DEMANDEUR (Startup) ===
- Secteur: {application.get('sector', 'Unknown')}
- Runway: {application.get('runway_months', 0):.1f} mois
- Burn multiple: {application.get('burn_multiple', 0):.2f}
- Croissance ARR: {application.get('arr_growth_yoy', 0)*100:.0f}%
- Churn mensuel: {application.get('churn_rate_monthly', 0)*100:.2f}%
- VC backing: {'Oui' if application.get('vc_backing') else 'Non'}
- Expérience fondateur: {application.get('founder_experience_years', 0)} ans

=== ANALYSE DE SIMILARITÉ ===
- Score moyen de similarité: {avg_score:.3f}
- Cas similaires APPROUVÉS: {len(approved_cases)}
- Cas similaires REJETÉS: {len(rejected_cases)}
"""
        red_flag_indicators = []
        if application.get('runway_months', 0) < 3:
            red_flag_indicators.append("Runway critique (<3 mois)")
        if application.get('burn_multiple', 0) > 3:
            red_flag_indicators.append("Burn multiple excessif (>3)")
        if application.get('churn_rate_monthly', 0) > 0.1:
            red_flag_indicators.append("Taux de churn élevé (>10%/mois)")
        if application.get('arr_growth_yoy', 0) < 0:
            red_flag_indicators.append("Croissance négative")
            
    else:  # enterprise
        risk_context = f"""
=== PROFIL DEMANDEUR (Entreprise) ===
- Industrie: {application.get('industry_code', 'Unknown')}
- Score Altman Z: {application.get('altman_z_score', 0):.2f}
- Current ratio: {application.get('current_ratio', 0):.2f}
- Ratio dette/capitaux: {application.get('debt_to_equity', 0):.2f}
- Couverture intérêts: {application.get('interest_coverage_ratio', 0):.2f}
- Score ESG: {application.get('esg_risk_score', 0):.1f}/100
- Procès actifs: {application.get('legal_lawsuits_active', 0)}
- Track record CEO: {application.get('ceo_track_record', 'Unknown')}

=== ANALYSE DE SIMILARITÉ ===
- Score moyen de similarité: {avg_score:.3f}
- Cas similaires APPROUVÉS: {len(approved_cases)}
- Cas similaires REJETÉS/FAILLITE: {len(rejected_cases)}
"""
        red_flag_indicators = []
        if application.get('altman_z_score', 0) < 1.8:
            red_flag_indicators.append("Zone de détresse Altman (<1.8)")
        if application.get('current_ratio', 0) < 1:
            red_flag_indicators.append("Liquidité insuffisante (current ratio <1)")
        if application.get('interest_coverage_ratio', 0) < 1.5:
            red_flag_indicators.append("Faible couverture des intérêts")
        if application.get('legal_lawsuits_active', 0) > 0:
            red_flag_indicators.append(f"{application.get('legal_lawsuits_active')} procès en cours")
        if "bankruptcy" in str(application.get('ceo_track_record', '')).lower():
            red_flag_indicators.append("CEO avec antécédent de faillite")
    
    if red_flag_indicators:
        risk_context += "\n=== RED FLAGS DÉTECTÉS ===\n"
        for flag in red_flag_indicators:
            risk_context += f"⚠️ {flag}\n"
    
    risk_context += "\n=== DÉTAILS CAS SIMILAIRES ===\n"
    for i, case in enumerate(similar_cases[:5], 1):
        p = case['payload']
        risk_context += f"Cas {i} (score: {case['score']:.3f}): Outcome={p.get('outcome', 'UNKNOWN')}\n"
    
    llm = get_llm()
    messages = [
        SystemMessage(content=RISK_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse les risques et anomalies:\n{risk_context}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": f"Risk Agent - {application_type.capitalize()}", "tags": ["risk", application_type]}
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
            key_metrics={"similarity": case['score']},
            summary=f"Cas {case['payload'].get('outcome', 'UNKNOWN')} (similarité: {case['score']:.2f})"
        ))
    
    return AgentAnalysis(
        agent_name="Risk Pattern Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('red_flags', red_flag_indicators),
        positive_signals=result.get('positive_signals', []),
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )


def analyze(application_type: str, application: dict, similar_cases: list[dict]) -> AgentAnalysis:
    """Main entry point for risk analysis."""
    return analyze_risk_patterns(application_type, application, similar_cases)
