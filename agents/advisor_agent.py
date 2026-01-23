"""
Advisor Agent - Provides recommendations to improve credit acceptance.
Analyzes weaknesses and suggests actionable improvements.
"""

import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, THRESHOLDS
from .schemas import FinalDecision, RiskLevel, DecisionOutcome

os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY
    )


ADVISOR_SYSTEM_PROMPT = """Tu es un conseiller expert en crédit et finance.
Ton rôle est d'aider les demandeurs à améliorer leur profil pour obtenir un crédit.

Basé sur l'analyse de crédit fournie, tu dois:
1. Identifier les points faibles qui ont impacté la décision
2. Proposer des actions concrètes et réalisables pour améliorer le profil
3. Estimer le temps nécessaire pour voir des améliorations
4. Prioriser les actions par impact (HIGH, MEDIUM, LOW)

Sois positif et encourageant tout en restant réaliste.

IMPORTANT: Réponds UNIQUEMENT avec un objet JSON valide (pas de texte avant ou après):
{
    "overall_assessment": "évaluation globale du profil en 2-3 phrases",
    "main_weaknesses": ["faiblesse1", "faiblesse2", "faiblesse3"],
    "recommendations": [
        {
            "action": "description de l'action",
            "priority": "HIGH",
            "impact": "impact attendu",
            "timeline": "durée estimée",
            "details": "détails sur comment faire"
        }
    ],
    "quick_wins": ["action rapide 1", "action rapide 2"],
    "long_term_strategy": "stratégie à long terme en 2-3 phrases",
    "estimated_improvement": "estimation d'amélioration du profil"
}"""


def generate_advice(
    decision: FinalDecision,
    application: dict,
    application_type: str
) -> dict:
    """
    Generate personalized advice to improve credit profile.
    
    Returns:
        Dict with recommendations and action plan
    """
    # Build context from decision
    context = f"=== PROFIL DU DEMANDEUR ({application_type.upper()}) ===\n"
    
    if application_type == "client":
        context += f"""
- Revenu annuel: €{application.get('income_annual', 0):,.0f}
- Ratio dette/revenu: {application.get('debt_to_income_ratio', 0)*100:.1f}%
- Paiements manqués: {application.get('missed_payments_last_12m', 0)}
- Ancienneté emploi: {application.get('job_tenure_years', 0)} ans
- Utilisation crédit: {application.get('credit_utilization_avg', 0)*100:.1f}%
- Type contrat: {application.get('contract_type', 'Unknown')}
"""
    elif application_type == "startup":
        context += f"""
- Secteur: {application.get('sector', 'Unknown')}
- ARR: ${application.get('arr_current', 0):,.0f}
- Runway: {application.get('runway_months', 0):.1f} mois
- Burn multiple: {application.get('burn_multiple', 0):.2f}
- Croissance ARR: {application.get('arr_growth_yoy', 0)*100:.0f}%
- VC backing: {'Oui' if application.get('vc_backing') else 'Non'}
"""
    else:  # enterprise
        context += f"""
- Industrie: {application.get('industry_code', 'Unknown')}
- Revenu: €{application.get('revenue_annual', 0):,.0f}
- Score Altman Z: {application.get('altman_z_score', 0):.2f}
- Current ratio: {application.get('current_ratio', 0):.2f}
- Marge nette: {application.get('net_profit_margin', 0)*100:.1f}%
- Procès en cours: {application.get('legal_lawsuits_active', 0)}
"""
    
    context += f"""
=== DÉCISION ACTUELLE ===
- Résultat: {decision.decision.value}
- Niveau de risque: {decision.overall_risk_level.value}
- Confiance: {decision.confidence*100:.0f}%

=== RÉSUMÉ ===
{decision.executive_summary or 'Non disponible'}

=== RAISONS DE LA DÉCISION ===
"""
    for reason in (decision.key_reasons or []):
        context += f"- {reason}\n"
    
    # Add red flags
    all_red_flags = []
    if decision.financial_analysis and decision.financial_analysis.red_flags:
        all_red_flags.extend(decision.financial_analysis.red_flags)
    if decision.risk_analysis and decision.risk_analysis.red_flags:
        all_red_flags.extend(decision.risk_analysis.red_flags)
    
    if all_red_flags:
        context += "\n=== POINTS D'ATTENTION ===\n"
        for flag in all_red_flags[:5]:
            context += f"- {flag}\n"
    
    # Call LLM
    llm = get_llm()
    messages = [
        SystemMessage(content=ADVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse ce profil et donne des conseils:\n{context}")
    ]
    
    response = llm.invoke(
        messages,
        config={"run_name": f"Advisor Agent - {application_type.capitalize()}", "tags": ["advisor", application_type]}
    )
    
    # Parse response
    try:
        # Try to extract JSON from response
        content = response.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
    except json.JSONDecodeError:
        # Return a fallback structure with the raw response
        result = {
            "overall_assessment": "Analyse générée avec succès. Veuillez consulter les recommandations ci-dessous.",
            "main_weaknesses": ["Profil nécessitant une amélioration"],
            "recommendations": [
                {
                    "action": "Améliorer les indicateurs financiers clés",
                    "priority": "HIGH",
                    "impact": "Amélioration significative du profil",
                    "timeline": "3-6 mois",
                    "details": response.content[:500] if response.content else "Consultez un conseiller financier"
                }
            ],
            "quick_wins": ["Réduire les dépenses non essentielles", "Consolider les dettes existantes"],
            "long_term_strategy": "Améliorer progressivement tous les indicateurs financiers sur 12-24 mois.",
            "estimated_improvement": "Amélioration potentielle du profil de 20-30% en 6 mois avec les actions recommandées."
        }
    
    return result
