"""
Prediction Agent - Prédiction de défaut, faillite et timeline de risque.
Identifie les indicateurs précurseurs et estime quand le risque se matérialisera.
Uses LangChain for automatic LangSmith tracing.
"""

import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, THRESHOLDS
from .schemas import AgentAnalysis, RiskLevel, SimilarCase, PredictionResult

os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


PREDICTION_SYSTEM_PROMPT = """Tu es un agent expert en prédiction de risque de crédit.
Tu analyses les profils pour prédire:
1. La probabilité de défaut/faillite
2. Le moment où le risque pourrait se matérialiser (timeline)
3. La trajectoire du risque (improving, stable, deteriorating)
4. Les signaux d'alerte précoces

Base tes prédictions sur:
- Les métriques actuelles du demandeur
- Les patterns des cas similaires historiques
- Les indicateurs précurseurs connus

Réponds UNIQUEMENT en JSON valide avec cette structure:
{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "default_probability": 0.0-1.0,
    "time_to_risk": "6 mois|12 mois|18 mois|24+ mois|immédiat",
    "risk_trajectory": "improving|stable|deteriorating",
    "warning_signals": ["signal1", "signal2"],
    "key_findings": ["finding1", "finding2"],
    "recommendation": "ta recommandation"
}"""


def analyze_predictions(
    application_type: str,
    application: dict,
    similar_cases: list[dict]
) -> tuple[AgentAnalysis, PredictionResult]:
    """Predict default/bankruptcy risk and timeline."""
    
    approved_ok = [c for c in similar_cases if c['payload'].get('outcome') == 'APPROVED']
    defaults = [c for c in similar_cases if c['payload'].get('outcome') in ['REJECTED', 'DEFAULT', 'BANKRUPT']]
    
    if application_type == "client":
        dti = application.get('debt_to_income_ratio', 0)
        missed = application.get('missed_payments_last_12m', 0)
        utilization = application.get('credit_utilization_avg', 0)
        tenure = application.get('job_tenure_years', 0)
        
        prediction_context = f"""
=== PROFIL ACTUEL (Client) ===
- Ratio dette/revenu: {dti*100:.1f}% (seuil danger: >{THRESHOLDS['max_debt_to_income']*100}%)
- Paiements manqués: {missed} (seuil danger: >{THRESHOLDS['max_missed_payments']})
- Utilisation crédit: {utilization*100:.1f}%
- Stabilité emploi: {tenure} ans, contrat {application.get('contract_type', 'Unknown')}
- Objectif prêt: {application.get('loan_purpose', 'Unknown')}

=== INDICATEURS DE RISQUE ===
{"⚠️ Ratio dette/revenu élevé - risque de surendettement" if dti > 0.4 else "✓ Ratio dette/revenu acceptable"}
{"⚠️ Historique de paiements manqués - pattern de défaut" if missed > 0 else "✓ Aucun paiement manqué"}
{"⚠️ Utilisation crédit excessive - stress financier" if utilization > 0.7 else "✓ Utilisation crédit modérée"}
{"⚠️ Emploi instable" if tenure < 1 else "✓ Emploi stable"}

=== PATTERNS DES CAS SIMILAIRES ===
Cas similaires ayant fait défaut: {len(defaults)}
Cas similaires en règle: {len(approved_ok)}
"""

    elif application_type == "startup":
        runway = application.get('runway_months', 0)
        burn = application.get('burn_multiple', 0)
        growth = application.get('arr_growth_yoy', 0)
        churn = application.get('churn_rate_monthly', 0)
        
        prediction_context = f"""
=== PROFIL ACTUEL (Startup) ===
- Runway: {runway:.1f} mois (danger: <{THRESHOLDS['min_runway_months']} mois)
- Burn multiple: {burn:.2f} (danger: >{THRESHOLDS['max_burn_multiple']})
- Croissance ARR: {growth*100:.0f}%
- Churn mensuel: {churn*100:.2f}%
- VC backing: {'Oui' if application.get('vc_backing') else 'Non'}
- Expérience fondateur: {application.get('founder_experience_years', 0)} ans

=== INDICATEURS DE RISQUE ===
{"🚨 CRITIQUE: Runway < 3 mois - survie immédiate en danger" if runway < 3 else "⚠️ Runway < 6 mois - tension financière" if runway < 6 else "✓ Runway confortable"}
{"⚠️ Burn multiple excessif - inefficacité capital" if burn > 2 else "✓ Burn multiple acceptable"}
{"⚠️ Croissance négative - déclin" if growth < 0 else "✓ Croissance positive"}
{"⚠️ Churn élevé - rétention problématique" if churn > 0.05 else "✓ Churn acceptable"}

=== TIMELINE ESTIMÉE ===
Épuisement cash prévu: {runway:.0f} mois
{"Sans levée de fonds, fermeture probable dans " + str(int(runway)) + " mois" if runway < 12 else "Runway suffisant pour 12+ mois"}

=== PATTERNS DES CAS SIMILAIRES ===
Startups similaires ayant échoué: {len(defaults)}
Startups similaires ayant réussi: {len(approved_ok)}
"""

    else:  # enterprise
        z_score = application.get('altman_z_score', 0)
        current = application.get('current_ratio', 0)
        coverage = application.get('interest_coverage_ratio', 0)
        lawsuits = application.get('legal_lawsuits_active', 0)
        
        if z_score > 3:
            z_zone = "Zone Sûre"
            z_risk = "Faible probabilité de faillite"
        elif z_score > 1.8:
            z_zone = "Zone Grise"
            z_risk = "Risque modéré, surveillance nécessaire"
        else:
            z_zone = "Zone de Détresse"
            z_risk = "Risque élevé de faillite dans 24 mois"
        
        prediction_context = f"""
=== PROFIL ACTUEL (Entreprise) ===
- Score Altman Z: {z_score:.2f} → {z_zone}
- Current ratio: {current:.2f} (danger: <1)
- Couverture intérêts: {coverage:.2f} (danger: <1.5)
- Procès actifs: {lawsuits}
- Marge nette: {application.get('net_profit_margin', 0)*100:.1f}%

=== PRÉDICTION ALTMAN ===
Zone: {z_zone}
Interprétation: {z_risk}

=== INDICATEURS DE RISQUE ===
{"🚨 CRITIQUE: Z-Score en zone de détresse" if z_score < 1.8 else "⚠️ Z-Score en zone grise" if z_score < 3 else "✓ Z-Score en zone sûre"}
{"⚠️ Liquidité insuffisante" if current < 1 else "✓ Liquidité adéquate"}
{"⚠️ Couverture intérêts faible" if coverage < 1.5 else "✓ Couverture intérêts ok"}
{"⚠️ Risque juridique: " + str(lawsuits) + " procès" if lawsuits > 0 else "✓ Pas de procès en cours"}

=== PATTERNS DES CAS SIMILAIRES ===
Entreprises similaires en faillite: {len([c for c in defaults if c['payload'].get('outcome') == 'BANKRUPT'])}
Entreprises similaires rejetées: {len([c for c in defaults if c['payload'].get('outcome') == 'REJECTED'])}
Entreprises similaires approuvées: {len(approved_ok)}
"""

    prediction_context += "\n=== DÉTAIL CAS SIMILAIRES ===\n"
    for i, case in enumerate(similar_cases[:5], 1):
        p = case['payload']
        prediction_context += f"Cas {i}: Outcome={p.get('outcome', 'UNKNOWN')} (similarité: {case['score']:.2f})\n"
    
    llm = get_llm()
    messages = [
        SystemMessage(content=PREDICTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Prédit le risque de défaut/faillite:\n{prediction_context}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": f"Prediction Agent - {application_type.capitalize()}", "tags": ["prediction", application_type]}
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
            "default_probability": 0.3,
            "time_to_risk": "12 mois",
            "risk_trajectory": "stable",
            "warning_signals": [],
            "key_findings": ["Prédiction en cours"],
            "recommendation": "Surveillance recommandée"
        }
    
    prediction = PredictionResult(
        default_probability=result.get('default_probability', 0.5),
        time_to_risk=result.get('time_to_risk', 'unknown'),
        risk_trajectory=result.get('risk_trajectory', 'stable'),
        warning_signals=result.get('warning_signals', [])
    )
    
    cited_cases = []
    for case in similar_cases[:3]:
        cited_cases.append(SimilarCase(
            case_id=str(case['id']),
            similarity_score=case['score'],
            outcome=case['payload'].get('outcome', 'UNKNOWN'),
            key_metrics={"predicted_risk": result.get('default_probability', 0.5)},
            summary=f"Cas historique: {case['payload'].get('outcome', 'UNKNOWN')}"
        ))
    
    analysis = AgentAnalysis(
        agent_name="Prediction Agent",
        risk_level=RiskLevel(result.get('risk_level', 'MEDIUM')),
        confidence=result.get('confidence', 0.7),
        key_findings=result.get('key_findings', []),
        red_flags=result.get('warning_signals', []),
        positive_signals=[],
        recommendation=result.get('recommendation', ''),
        similar_cases_cited=cited_cases
    )
    
    return analysis, prediction


def analyze(application_type: str, application: dict, similar_cases: list[dict]) -> tuple[AgentAnalysis, PredictionResult]:
    """Main entry point for prediction analysis."""
    return analyze_predictions(application_type, application, similar_cases)
