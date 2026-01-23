"""
Credit Decision Memory - Main CLI Application

Usage:
    python main.py --demo           # Run demo with sample applications
    python main.py --type client    # Evaluate a client application
    python main.py --interactive    # Interactive mode
"""

import argparse
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import evaluate_credit_application
from agents.config import validate_config
from agents.schemas import FinalDecision


# =============================================================================
# SAMPLE APPLICATIONS FOR DEMO
# =============================================================================
SAMPLE_CLIENT = {
    "client_id": "DEMO-CLI-001",
    "income_annual": 45000,
    "debt_to_income_ratio": 0.25,
    "missed_payments_last_12m": 0,
    "job_tenure_years": 3,
    "age": 32,
    "contract_type": "CDI",
    "loan_purpose": "Home Improvement",
    "credit_history": "The applicant has maintained a clean credit record with no defaults. They have consistently paid all bills on time for the past 5 years.",
    "credit_utilization_avg": 0.3,
    "net_monthly": 2800,
    "basic_part": 2500,
    "variable_part": 300
}

SAMPLE_STARTUP = {
    "startup_id": "DEMO-STA-001",
    "sector": "FinTech",
    "founder_experience_years": 8,
    "vc_backing": True,
    "arr_current": 2500000,
    "arr_growth_yoy": 1.2,
    "burn_rate_monthly": 150000,
    "runway_months": 14,
    "cac_ltv_ratio": 0.25,
    "churn_rate_monthly": 0.03,
    "burn_multiple": 0.72,
    "pitch_narrative": "Our AI-powered payment platform revolutionizes B2B transactions, reducing processing time by 80% and costs by 60%. We have 150 enterprise clients and growing."
}

SAMPLE_ENTERPRISE = {
    "enterprise_id": "DEMO-ENT-001",
    "industry_code": "Manufacturing",
    "revenue_annual": 50000000,
    "net_profit_margin": 0.08,
    "current_ratio": 1.8,
    "quick_ratio": 1.2,
    "debt_to_equity": 0.6,
    "interest_coverage_ratio": 4.5,
    "altman_z_score": 2.8,
    "esg_risk_score": 35,
    "legal_lawsuits_active": 0,
    "ceo_name": "Marie Dupont",
    "ceo_experience_years": 20,
    "ceo_track_record": "Successfully led company through 2008 crisis",
    "annual_report_risk_section": "The company faces moderate supply chain risks due to global uncertainties, but maintains strong relationships with multiple suppliers."
}

SAMPLE_HIGH_RISK_CLIENT = {
    "client_id": "DEMO-CLI-RISK",
    "income_annual": 28000,
    "debt_to_income_ratio": 0.55,
    "missed_payments_last_12m": 3,
    "job_tenure_years": 0.5,
    "age": 24,
    "contract_type": "CDD",
    "loan_purpose": "Debt Consolidation",
    "credit_history": "The applicant has had multiple payment issues and was in default for 2 months last year.",
    "credit_utilization_avg": 0.85
}


def print_decision(decision: FinalDecision):
    """Pretty print the final decision."""
    
    # Decision header
    decision_color = {
        "APPROVED": "\033[92m",  # Green
        "REJECTED": "\033[91m",  # Red
        "REVIEW_NEEDED": "\033[93m"  # Yellow
    }
    reset = "\033[0m"
    
    print("\n" + "=" * 70)
    print(f"{'CREDIT DECISION MEMORY - ANALYSIS REPORT':^70}")
    print("=" * 70)
    
    color = decision_color.get(decision.decision.value, "")
    print(f"\n{'DÉCISION:':<20} {color}{decision.decision.value}{reset}")
    print(f"{'Confiance:':<20} {decision.confidence*100:.0f}%")
    print(f"{'Niveau de risque:':<20} {decision.overall_risk_level.value}")
    print(f"{'Type demandeur:':<20} {decision.application_type.value}")
    print(f"{'Temps traitement:':<20} {decision.processing_time_seconds:.2f}s")
    
    print("\n" + "-" * 70)
    print("RÉSUMÉ EXÉCUTIF")
    print("-" * 70)
    print(decision.executive_summary)
    
    print("\n" + "-" * 70)
    print("RAISONS PRINCIPALES")
    print("-" * 70)
    for i, reason in enumerate(decision.key_reasons, 1):
        print(f"  {i}. {reason}")
    
    # Agent analyses
    print("\n" + "-" * 70)
    print("ANALYSES DES AGENTS")
    print("-" * 70)
    
    if decision.financial_analysis:
        fa = decision.financial_analysis
        print(f"\n💰 Financial Agent: {fa.risk_level.value} ({fa.confidence*100:.0f}%)")
        if fa.key_findings:
            print(f"   Findings: {', '.join(fa.key_findings[:2])}")
        if fa.red_flags:
            print(f"   ⚠️ Red flags: {', '.join(fa.red_flags[:2])}")
    
    if decision.risk_analysis:
        ra = decision.risk_analysis
        print(f"\n⚠️ Risk Agent: {ra.risk_level.value} ({ra.confidence*100:.0f}%)")
        if ra.red_flags:
            print(f"   Red flags: {', '.join(ra.red_flags[:3])}")
    
    if decision.narrative_analysis:
        na = decision.narrative_analysis
        print(f"\n📝 Narrative Agent: {na.risk_level.value} ({na.confidence*100:.0f}%)")
        if na.key_findings:
            print(f"   Findings: {', '.join(na.key_findings[:2])}")
    
    if decision.prediction_result:
        pr = decision.prediction_result
        print(f"\n🔮 Prediction Agent:")
        print(f"   Probabilité défaut: {pr.default_probability*100:.0f}%")
        print(f"   Timeline risque: {pr.time_to_risk}")
        print(f"   Trajectoire: {pr.risk_trajectory}")
    
    # Conditions and next steps
    if decision.conditions:
        print("\n" + "-" * 70)
        print("CONDITIONS (si approuvé)")
        print("-" * 70)
        for condition in decision.conditions:
            print(f"  • {condition}")
    
    if decision.next_steps:
        print("\n" + "-" * 70)
        print("PROCHAINES ÉTAPES")
        print("-" * 70)
        for step in decision.next_steps:
            print(f"  → {step}")
    
    # Similar cases
    if decision.similar_precedents:
        print("\n" + "-" * 70)
        print("CAS SIMILAIRES HISTORIQUES")
        print("-" * 70)
        for case in decision.similar_precedents[:3]:
            print(f"  • ID: {case.case_id} | Outcome: {case.outcome} | Similarité: {case.similarity_score:.2f}")
    
    print("\n" + "=" * 70)


def run_demo():
    """Run demo with sample applications."""
    print("\n🚀 CREDIT DECISION MEMORY - DÉMO")
    print("=" * 50)
    
    demos = [
        ("Client (Profil Sûr)", "client", SAMPLE_CLIENT),
        ("Client (Haut Risque)", "client", SAMPLE_HIGH_RISK_CLIENT),
        ("Startup (FinTech)", "startup", SAMPLE_STARTUP),
        ("Enterprise (Manufacturing)", "enterprise", SAMPLE_ENTERPRISE),
    ]
    
    print("\nChoisissez une démo:")
    for i, (name, _, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Toutes les démos")
    
    choice = input("\nVotre choix (0-4): ").strip()
    
    if choice == "0":
        selected = demos
    elif choice in ["1", "2", "3", "4"]:
        selected = [demos[int(choice) - 1]]
    else:
        print("Choix invalide")
        return
    
    for name, app_type, application in selected:
        print(f"\n{'=' * 70}")
        print(f"📋 Évaluation: {name}")
        print("=" * 70)
        
        decision = evaluate_credit_application(application, app_type)
        print_decision(decision)
        
        if len(selected) > 1:
            input("\n[Appuyez sur Entrée pour continuer...]")


def run_interactive():
    """Interactive mode to input custom applications."""
    print("\n📝 MODE INTERACTIF")
    print("=" * 50)
    
    print("\nType de demandeur:")
    print("  1. Client (particulier)")
    print("  2. Startup")
    print("  3. Entreprise")
    
    type_choice = input("\nVotre choix (1-3): ").strip()
    
    if type_choice == "1":
        app_type = "client"
        print("\n--- Informations Client ---")
        application = {
            "income_annual": float(input("Revenu annuel (€): ")),
            "debt_to_income_ratio": float(input("Ratio dette/revenu (0-1): ")),
            "missed_payments_last_12m": int(input("Paiements manqués (12 mois): ")),
            "job_tenure_years": float(input("Ancienneté emploi (années): ")),
            "age": int(input("Âge: ")),
            "contract_type": input("Type contrat (CDI/CDD): "),
            "loan_purpose": input("Objectif du prêt: "),
            "credit_history": input("Historique crédit (description): ")
        }
    elif type_choice == "2":
        app_type = "startup"
        print("\n--- Informations Startup ---")
        application = {
            "sector": input("Secteur: "),
            "founder_experience_years": int(input("Expérience fondateur (années): ")),
            "vc_backing": input("VC backing (oui/non): ").lower() == "oui",
            "arr_current": float(input("ARR actuel ($): ")),
            "arr_growth_yoy": float(input("Croissance ARR YoY (ex: 0.5 pour 50%): ")),
            "burn_rate_monthly": float(input("Burn rate mensuel ($): ")),
            "runway_months": float(input("Runway (mois): ")),
            "burn_multiple": float(input("Burn multiple: ")),
            "pitch_narrative": input("Pitch (description): ")
        }
    elif type_choice == "3":
        app_type = "enterprise"
        print("\n--- Informations Entreprise ---")
        application = {
            "industry_code": input("Industrie: "),
            "revenue_annual": float(input("Revenu annuel (€): ")),
            "net_profit_margin": float(input("Marge nette (0-1): ")),
            "current_ratio": float(input("Current ratio: ")),
            "altman_z_score": float(input("Score Altman Z: ")),
            "debt_to_equity": float(input("Ratio dette/capitaux: ")),
            "legal_lawsuits_active": int(input("Procès actifs: ")),
            "ceo_track_record": input("Track record CEO: ")
        }
    else:
        print("Choix invalide")
        return
    
    print("\n⏳ Analyse en cours...")
    decision = evaluate_credit_application(application, app_type)
    print_decision(decision)


def main():
    parser = argparse.ArgumentParser(description="Credit Decision Memory - Multi-Agent System")
    parser.add_argument("--demo", action="store_true", help="Run demo with sample applications")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--type", choices=["client", "startup", "enterprise"], help="Application type")
    parser.add_argument("--json", type=str, help="JSON file with application data")
    
    args = parser.parse_args()
    
    # Validate configuration
    try:
        validate_config()
        print("✓ Configuration validée")
    except ValueError as e:
        print(f"❌ Erreur de configuration: {e}")
        return 1
    
    if args.demo:
        run_demo()
    elif args.interactive:
        run_interactive()
    elif args.type and args.json:
        with open(args.json) as f:
            application = json.load(f)
        decision = evaluate_credit_application(application, args.type)
        print_decision(decision)
    else:
        # Default: run demo
        run_demo()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
