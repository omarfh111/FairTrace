"""
Credit Decision Memory - Synthetic Data Generator
Generates high-quality JSON datasets for Clients, Startups, and Enterprises.

Usage:
    python generate_data.py --clients 8000 --startups 1500 --enterprises 500
"""

import json
import random
import argparse
from pathlib import Path
from typing import Optional

from faker import Faker
import numpy as np
from tqdm import tqdm

# Import prompt templates
from prompts_config import get_client_prompt, get_startup_prompt, get_enterprise_prompt, get_ceo_prompt

# Optional: Ollama for text generation
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

fake = Faker()
random.seed(42)  # Reproducibility
np.random.seed(42)

# --- Configuration ---
OUTPUT_DIR = Path(__file__).parent / "output"
EVAL_DIR = Path(__file__).parent.parent / "evaluation"
OLLAMA_MODEL = "qwen2.5:0.5b"  # Fast, <1B params
TEST_SPLIT_RATIO = 0.1  # 10% for test

# --- Ollama Success Tracking ---
ollama_stats = {
    "clients": {"success": 0, "fallback": 0},
    "startups": {"success": 0, "fallback": 0},
    "enterprises": {"success": 0, "fallback": 0}
}

# --- Golden Q&A Pairs for Evaluation ---
golden_qa_pairs = []


# =============================================================================
# TEXT GENERATION (Ollama SLM)
# =============================================================================
def generate_text_with_ollama(prompt: str, max_tokens: int = 100) -> tuple[str, bool]:
    """Generate realistic text using a local Ollama model.
    
    Returns:
        Tuple of (generated_text, success_flag)
    """
    if not OLLAMA_AVAILABLE:
        return fake.paragraph(nb_sentences=3), False
    try:
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"num_predict": max_tokens, "temperature": 0.7}
        )
        text = response["response"].strip()
        # Consider it a success if we got a non-empty response
        if text and len(text) > 10:
            return text, True
        return fake.paragraph(nb_sentences=3), False
    except Exception:
        # Fallback to Faker if Ollama fails
        return fake.paragraph(nb_sentences=3), False


# =============================================================================
# CLIENT GENERATOR
# =============================================================================
def generate_client(client_id: int, use_ollama: bool = False) -> dict:
    """Generate a single Client record with realistic financial metrics."""
    age = random.randint(22, 65)
    job_tenure = random.randint(0, min(age - 18, 30))
    
    # Contract Type (Critical for Credit)
    contract_type = random.choices(
        ["CDI", "CDD", "Freelance", "Unemployed"], 
        weights=[70, 15, 10, 5]
    )[0]
    
    # Income & Payslip Structure
    income = random.randint(20000, 180000)
    basic_salary_pct = random.uniform(0.7, 1.0) if contract_type == "CDI" else random.uniform(0.5, 0.9)
    bonus_pct = 1.0 - basic_salary_pct
    
    payslip_structure = {
        "gross_monthly": round(income / 12, 2),
        "net_monthly": round((income / 12) * 0.75, 2),  # Approx net
        "basic_part": round((income / 12) * basic_salary_pct, 2),
        "variable_part": round((income / 12) * bonus_pct, 2)
    }
    
    # Derive realistic metrics
    fixed_costs_pct = random.uniform(0.3, 0.6)
    disposable = (income / 12) * (1 - fixed_costs_pct)
    
    # Debt-to-Income (realistic range)
    dti = random.uniform(0.05, 0.55)
    
    # Savings rate (inversely correlated with DTI)
    savings_rate = max(0.0, random.uniform(0.0, 0.3) - (dti * 0.3))
    
    # Spending volatility (younger = more volatile)
    volatility = random.uniform(0.1, 0.5) + (0.3 if age < 30 else 0.0)
    volatility = min(volatility, 1.0)
    
    # Credit behavior
    missed_payments = random.choices([0, 1, 2, 3, 4, 5], weights=[60, 15, 10, 7, 5, 3])[0]
    credit_util = random.uniform(0.1, 0.9)
    
    # Loan purpose
    purposes = [
        "Home renovation", "Debt consolidation", "Vehicle purchase",
        "Medical expenses", "Education", "Business investment", "Travel"
    ]
    
    # Determine outcome based on risk signals
    risk_score = (dti * 0.4) + (missed_payments * 0.1) + (credit_util * 0.2) + (volatility * 0.2)
    if risk_score > 0.6:
        outcome = random.choices(["APPROVED", "REJECTED", "DEFAULT"], weights=[20, 50, 30])[0]
    elif risk_score > 0.4:
        outcome = random.choices(["APPROVED", "REJECTED", "DEFAULT"], weights=[50, 35, 15])[0]
    else:
        outcome = random.choices(["APPROVED", "REJECTED", "DEFAULT"], weights=[80, 15, 5])[0]
    
    # Generate credit history text
    if use_ollama:
        history_prompt = get_client_prompt(
            age=age,
            missed_payments=missed_payments,
            dti=dti,
            credit_util=credit_util
        )
        credit_history, success = generate_text_with_ollama(history_prompt, max_tokens=80)
        if success:
            ollama_stats["clients"]["success"] += 1
        else:
            ollama_stats["clients"]["fallback"] += 1
    else:
        if missed_payments == 0:
            credit_history = "Clean payment history with no delinquencies. Strong track record of timely repayments."
        elif missed_payments <= 2:
            credit_history = f"Minor payment issues with {missed_payments} late payment(s) in the past 12 months. Generally reliable borrower."
        else:
            credit_history = f"Concerning payment pattern with {missed_payments} missed payments. Elevated risk profile requiring enhanced monitoring."
    
    # Assign train/test split
    split = "test" if random.random() < TEST_SPLIT_RATIO else "train"
    
    record = {
        "client_id": f"CLI-{client_id:05d}",
        "age": age,
        "contract_type": contract_type,
        "job_tenure_years": job_tenure,
        "income_annual": round(income, 2),
        "payslip_structure": payslip_structure,
        "disposable_income_monthly": round(disposable, 2),
        "debt_to_income_ratio": round(dti, 3),
        "savings_rate": round(savings_rate, 3),
        "spending_volatility_index": round(volatility, 3),
        "missed_payments_last_12m": missed_payments,
        "credit_utilization_avg": round(credit_util, 3),
        "loan_purpose": random.choice(purposes),
        "credit_history": credit_history,
        "outcome": outcome,
        "split": split
    }
    
    # Generate golden Q&A pairs for specific test cases
    if split == "test" and missed_payments >= 3:
        golden_qa_pairs.append({
            "query": f"Find clients with poor payment history similar to someone with {missed_payments} missed payments",
            "expected_id": record["client_id"],
            "collection": "clients_v2",
            "reasoning": f"Client has {missed_payments} missed payments and {outcome} outcome"
        })
    
    return record


# =============================================================================
# STARTUP GENERATOR
# =============================================================================
def generate_startup(startup_id: int, use_ollama: bool = False) -> dict:
    """Generate a single Startup record with realistic SaaS/Growth metrics."""
    sectors = ["SaaS", "FinTech", "HealthTech", "E-commerce", "DeepTech", "CleanTech", "EdTech"]
    sector = random.choice(sectors)
    
    founder_exp = random.randint(0, 20)
    vc_backed = random.random() < 0.3  # 30% are VC-backed
    
    # ARR and Growth
    arr = random.randint(50000, 5000000)
    arr_growth = random.uniform(-0.1, 2.0)  # -10% to +200%
    
    # Burn and Runway
    if vc_backed:
        cash = random.randint(500000, 10000000)
    else:
        cash = random.randint(50000, 1000000)
    
    burn_rate = random.randint(20000, 500000)
    runway = cash / burn_rate if burn_rate > 0 else 24
    
    # Unit Economics
    cac = random.randint(100, 5000)
    ltv = cac * random.uniform(0.5, 5.0)
    cac_ltv = cac / ltv if ltv > 0 else 2.0
    
    churn = random.uniform(0.01, 0.15)
    
    # Burn Multiple (key VC metric)
    net_new_arr = arr * arr_growth / 12 if arr_growth > 0 else 1
    burn_multiple = burn_rate / net_new_arr if net_new_arr > 0 else 10.0
    burn_multiple = min(burn_multiple, 15.0)  # Cap for realism
    
    # Determine outcome
    health_score = (runway / 24) + (1.0 if vc_backed else 0.0) - (burn_multiple / 10) - (cac_ltv * 0.5)
    if health_score > 1.0:
        outcome = random.choices(["FUNDED", "REJECTED", "BANKRUPT"], weights=[70, 25, 5])[0]
    elif health_score > 0.0:
        outcome = random.choices(["FUNDED", "REJECTED", "BANKRUPT"], weights=[40, 45, 15])[0]
    else:
        outcome = random.choices(["FUNDED", "REJECTED", "BANKRUPT"], weights=[10, 40, 50])[0]
    
    # Generate pitch narrative
    if use_ollama:
        pitch_prompt = get_startup_prompt(
            sector=sector,
            arr=arr,
            growth=arr_growth,
            burn=burn_rate,
            runway=runway
        )
        pitch, success = generate_text_with_ollama(pitch_prompt, max_tokens=100)
        if success:
            ollama_stats["startups"]["success"] += 1
        else:
            ollama_stats["startups"]["fallback"] += 1
    else:
        pitch = f"A {sector} startup disrupting the market with innovative solutions. Currently at ${arr:,} ARR with {arr_growth*100:.0f}% year-over-year growth."
    
    # Assign train/test split
    split = "test" if random.random() < TEST_SPLIT_RATIO else "train"
    
    record = {
        "startup_id": f"STA-{startup_id:05d}",
        "sector": sector,
        "founder_experience_years": founder_exp,
        "vc_backing": vc_backed,
        "arr_current": round(arr, 2),
        "arr_growth_yoy": round(arr_growth, 3),
        "burn_rate_monthly": round(burn_rate, 2),
        "runway_months": round(runway, 1),
        "cac_ltv_ratio": round(cac_ltv, 3),
        "churn_rate_monthly": round(churn, 4),
        "burn_multiple": round(burn_multiple, 2),
        "pitch_narrative": pitch,
        "outcome": outcome,
        "split": split
    }
    
    # Generate golden Q&A for high-risk startups
    if split == "test" and burn_multiple > 5.0:
        golden_qa_pairs.append({
            "query": f"Find {sector} startups with dangerous burn rates and poor unit economics",
            "expected_id": record["startup_id"],
            "collection": "startups_v2",
            "reasoning": f"Burn multiple of {burn_multiple:.1f}x indicates cash inefficiency"
        })
    
    return record


# =============================================================================
# ENTERPRISE GENERATOR
# =============================================================================
def generate_enterprise(enterprise_id: int, use_ollama: bool = False) -> dict:
    """Generate a single Enterprise record with realistic solvency metrics."""
    industries = [
        "Manufacturing", "Retail", "Technology", "Healthcare",
        "Energy", "Financial Services", "Real Estate", "Transportation"
    ]
    industry = random.choice(industries)
    
    # Financials (large scale)
    revenue = random.randint(10_000_000, 500_000_000)
    profit_margin = random.uniform(-0.05, 0.25)
    
    # Balance Sheet items (for ratio calculation)
    total_assets = revenue * random.uniform(0.8, 2.0)
    current_assets = total_assets * random.uniform(0.2, 0.5)
    cash = current_assets * random.uniform(0.1, 0.4)
    receivables = current_assets * random.uniform(0.2, 0.5)
    
    total_liabilities = total_assets * random.uniform(0.3, 0.8)
    current_liabilities = total_liabilities * random.uniform(0.2, 0.5)
    long_term_liabilities = total_liabilities - current_liabilities
    
    total_equity = total_assets - total_liabilities
    share_capital = total_equity * 0.4
    retained_earnings = total_equity * 0.6
    
    # Structured "Bilan" (Balance Sheet)
    financials_bilan = {
        "assets": {
            "current_assets": round(current_assets, 2),
            "cash": round(cash, 2),
            "receivables": round(receivables, 2),
            "fixed_assets": round(total_assets - current_assets, 2),
            "total_assets": round(total_assets, 2)
        },
        "liabilities": {
            "current_liabilities": round(current_liabilities, 2),
            "long_term_liabilities": round(long_term_liabilities, 2),
            "total_liabilities": round(total_liabilities, 2)
        },
        "equity": {
            "share_capital": round(share_capital, 2),
            "retained_earnings": round(retained_earnings, 2),
            "total_equity": round(total_equity, 2)
        }
    }
    
    # Ratios
    current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 2.0
    quick_ratio = (cash + receivables) / current_liabilities if current_liabilities > 0 else 1.5
    debt_to_equity = total_liabilities / total_equity if total_equity > 0 else 5.0
    
    # Interest Coverage (EBIT / Interest)
    ebit = revenue * profit_margin * 1.3  # Approximate
    interest_expense = total_liabilities * 0.05  # 5% average rate
    interest_coverage = ebit / interest_expense if interest_expense > 0 else 10.0
    
    # Altman Z-Score (simplified)
    # Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
    working_capital = current_assets - current_liabilities
    retained_earnings = total_equity * 0.6
    market_value_equity = total_equity * 1.5
    
    z_a = working_capital / total_assets if total_assets > 0 else 0
    z_b = retained_earnings / total_assets if total_assets > 0 else 0
    z_c = ebit / total_assets if total_assets > 0 else 0
    z_d = market_value_equity / total_liabilities if total_liabilities > 0 else 0
    z_e = revenue / total_assets if total_assets > 0 else 0
    
    z_score = 1.2*z_a + 1.4*z_b + 3.3*z_c + 0.6*z_d + 1.0*z_e
    z_score = max(min(z_score, 5.0), -1.0)  # Clamp to realistic range
    
    # ESG and Legal
    esg_score = random.uniform(30, 95)
    lawsuits = random.choices([0, 1, 2, 3, 5, 10], weights=[50, 25, 12, 8, 4, 1])[0]
    
    # Determine outcome
    if z_score > 3.0:
        outcome = random.choices(["STABLE", "WATCHLIST", "BANKRUPT"], weights=[85, 12, 3])[0]
    elif z_score > 1.8:
        outcome = random.choices(["STABLE", "WATCHLIST", "BANKRUPT"], weights=[50, 40, 10])[0]
    else:
        outcome = random.choices(["STABLE", "WATCHLIST", "BANKRUPT"], weights=[15, 35, 50])[0]
    
    # Generate risk report
    if use_ollama:
        risk_prompt = get_enterprise_prompt(
            industry=industry,
            z_score=z_score,
            current_ratio=current_ratio,
            debt_to_equity=debt_to_equity,
            lawsuits=lawsuits,
            esg=esg_score
        )
        risk_report, success = generate_text_with_ollama(risk_prompt, max_tokens=100)
        if success:
            ollama_stats["enterprises"]["success"] += 1
        else:
            ollama_stats["enterprises"]["fallback"] += 1
    else:
        if z_score > 3.0:
            risk_report = f"Strong financial position with healthy liquidity ratios. {industry} sector outlook remains positive."
        elif z_score > 1.8:
            risk_report = f"Moderate risk profile with some liquidity concerns. Requires ongoing monitoring of {industry} market conditions."
        else:
            risk_report = f"Elevated distress indicators with Z-Score below safe threshold. Significant concerns about ongoing viability in {industry} sector."

    # CEO Profile (Multimodal Signal)
    ceo_name = fake.name()
    ceo_exp = random.randint(5, 35)
    
    # Link CEO track record to Company Z-Score
    if z_score > 3.0:
        track_record = "Led previous company to IPO"
    elif z_score > 1.8:
        track_record = "Stable leadership in mid-market"
    else:
        track_record = "Previous venture faced bankruptcy"
        
    if use_ollama:
        ceo_prompt = get_ceo_prompt(ceo_name, industry, ceo_exp, track_record)
        ceo_resume, success = generate_text_with_ollama(ceo_prompt, max_tokens=60)
        if success:
             ollama_stats["enterprises"]["success"] += 1 # Count as well
    else:
        ceo_resume = f"{ceo_name} has {ceo_exp} years of experience in {industry}. Known for {track_record}."

    ceo_profile = {
        "name": ceo_name,
        "experience_years": ceo_exp,
        "track_record": track_record,
        "resume_summary": ceo_resume
    }
    
    # Assign train/test split
    split = "test" if random.random() < TEST_SPLIT_RATIO else "train"
    
    record = {
        "enterprise_id": f"ENT-{enterprise_id:05d}",
        "industry_code": industry,
        "ceo_profile": ceo_profile,
        "financials_bilan": financials_bilan,
        "revenue_annual": round(revenue, 2),
        "net_profit_margin": round(profit_margin, 4),
        "current_ratio": round(current_ratio, 3),
        "quick_ratio": round(quick_ratio, 3),
        "debt_to_equity": round(debt_to_equity, 3),
        "interest_coverage_ratio": round(interest_coverage, 2),
        "altman_z_score": round(z_score, 3),
        "esg_risk_score": round(esg_score, 1),
        "legal_lawsuits_active": lawsuits,
        "annual_report_risk_section": risk_report,
        "outcome": outcome,
        "split": split
    }
    
    # Generate golden Q&A for distressed enterprises
    if split == "test" and z_score < 1.8:
        golden_qa_pairs.append({
            "query": f"Find {industry} companies in financial distress with poor solvency",
            "expected_id": record["enterprise_id"],
            "collection": "enterprises_v2",
            "reasoning": f"Altman Z-Score of {z_score:.2f} is in distress zone (<1.8)"
        })
    if split == "test" and lawsuits >= 3:
        golden_qa_pairs.append({
            "query": f"Find companies with significant legal exposure and litigation risk",
            "expected_id": record["enterprise_id"],
            "collection": "enterprises_v2",
            "reasoning": f"Has {lawsuits} active lawsuits indicating legal risk"
        })
    
    return record


# =============================================================================
# MAIN DRIVER
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Generate synthetic credit data.")
    parser.add_argument("--clients", type=int, default=100, help="Number of client records")
    parser.add_argument("--startups", type=int, default=50, help="Number of startup records")
    parser.add_argument("--enterprises", type=int, default=20, help="Number of enterprise records")
    parser.add_argument("--use-ollama", action="store_true", help="Use Ollama for text generation")
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate Clients
    print(f"Generating {args.clients} clients...")
    clients = [generate_client(i, use_ollama=args.use_ollama) for i in tqdm(range(1, args.clients + 1))]
    with open(OUTPUT_DIR / "clients.json", "w") as f:
        json.dump(clients, f, indent=2)
    
    # Generate Startups
    print(f"Generating {args.startups} startups...")
    startups = [generate_startup(i, use_ollama=args.use_ollama) for i in tqdm(range(1, args.startups + 1))]
    with open(OUTPUT_DIR / "startups.json", "w") as f:
        json.dump(startups, f, indent=2)
    
    # Generate Enterprises
    print(f"Generating {args.enterprises} enterprises...")
    enterprises = [generate_enterprise(i, use_ollama=args.use_ollama) for i in tqdm(range(1, args.enterprises + 1))]
    with open(OUTPUT_DIR / "enterprises.json", "w") as f:
        json.dump(enterprises, f, indent=2)
    
    print(f"\n✓ Data saved to {OUTPUT_DIR.resolve()}")
    print(f"  - clients.json: {len(clients)} records")
    print(f"  - startups.json: {len(startups)} records")
    print(f"  - enterprises.json: {len(enterprises)} records")
    
    # Count train/test splits
    train_count = sum(1 for c in clients if c['split'] == 'train') + \
                  sum(1 for s in startups if s['split'] == 'train') + \
                  sum(1 for e in enterprises if e['split'] == 'train')
    test_count = len(clients) + len(startups) + len(enterprises) - train_count
    print(f"  - Train/Test Split: {train_count} train, {test_count} test")
    
    # Save golden Q&A pairs for evaluation
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVAL_DIR / "golden_qa.json", "w") as f:
        json.dump(golden_qa_pairs, f, indent=2)
    print(f"  - golden_qa.json: {len(golden_qa_pairs)} evaluation pairs")
    
    # Print Ollama statistics if used
    if args.use_ollama:
        print("\n📊 Ollama Text Generation Statistics:")
        for collection, stats in ollama_stats.items():
            total = stats["success"] + stats["fallback"]
            if total > 0:
                pct = (stats["success"] / total) * 100
                print(f"  - {collection}: {stats['success']}/{total} ({pct:.1f}% Ollama, {100-pct:.1f}% fallback)")


if __name__ == "__main__":
    main()
