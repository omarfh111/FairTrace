"""
Prompt Configuration for Synthetic Data Generation.

These prompts have been engineered to:
1. Avoid placeholders like [Company Name] or [Your Name]
2. Produce complete, standalone sentences
3. Ground the output in the specific data provided
4. Avoid meta-commentary ("Sure, here's...", "Here is...")
"""

# =============================================================================
# CLIENT PROMPTS (Credit History)
# =============================================================================
CLIENT_PROMPTS = {
    "credit_history": """You are a credit analyst writing internal notes.
Write exactly 2 complete sentences summarizing this borrower's credit behavior.

Borrower Profile:
- Age: {age} years old
- Missed payments in last 12 months: {missed_payments}
- Debt-to-income ratio: {dti_pct:.0f}%
- Credit utilization: {credit_util:.0f}%

Rules:
- Write in third person (e.g., "The applicant has...")
- Do NOT use placeholders like [Name] or [X]
- Do NOT start with "Sure" or "Here is"
- Be specific and professional
- End with a period

Output ONLY the 2 sentences, nothing else."""
}

# =============================================================================
# STARTUP PROMPTS (Pitch Narrative)
# =============================================================================
STARTUP_PROMPTS = {
    "pitch_narrative": """You are a startup founder writing a pitch deck summary.
Write exactly 2 complete sentences describing this company's value proposition.

Company Profile:
- Sector: {sector}
- Annual Recurring Revenue: ${arr:,}
- Year-over-year growth: {growth_pct:.0f}%
- Monthly burn rate: ${burn:,}
- Runway: {runway:.1f} months

Rules:
- Write as if YOU are the company (use "We" or "Our")
- Do NOT use placeholders like [Company Name] or [Product]
- Do NOT start with "Sure", "Here is", or bullet points
- Reference the actual numbers provided
- End with a period, not an incomplete sentence

Output ONLY the 2 sentences, nothing else."""
}

# =============================================================================
# ENTERPRISE PROMPTS (Risk Assessment)
# =============================================================================
ENTERPRISE_PROMPTS = {
    "risk_report": """You are a credit risk analyst writing an internal assessment.
Write exactly 2 complete sentences evaluating this company's financial health.

Company Profile:
- Industry: {industry}
- Altman Z-Score: {z_score:.2f} (Safe >3.0, Grey 1.8-3.0, Distress <1.8)
- Current Ratio: {current_ratio:.2f}
- Debt-to-Equity: {debt_to_equity:.2f}
- Active Lawsuits: {lawsuits}
- ESG Risk Score: {esg:.1f}/100

Rules:
- Write in third person (e.g., "The company exhibits...")
- Do NOT use placeholders like [Company] or [X]
- Do NOT start with "Sure" or "Here is"
- Reference the Z-Score zone (Safe/Grey/Distress)
- End with a period

Output ONLY the 2 sentences, nothing else."""
}


def get_client_prompt(age: int, missed_payments: int, dti: float, credit_util: float) -> str:
    """Format the client credit history prompt with actual values."""
    return CLIENT_PROMPTS["credit_history"].format(
        age=age,
        missed_payments=missed_payments,
        dti_pct=dti * 100,
        credit_util=credit_util * 100
    )


def get_startup_prompt(sector: str, arr: float, growth: float, burn: float, runway: float) -> str:
    """Format the startup pitch narrative prompt with actual values."""
    return STARTUP_PROMPTS["pitch_narrative"].format(
        sector=sector,
        arr=arr,
        growth_pct=growth * 100,
        burn=burn,
        runway=runway
    )


def get_enterprise_prompt(
    industry: str, z_score: float, current_ratio: float, 
    debt_to_equity: float, lawsuits: int, esg: float
) -> str:
    """Format the enterprise risk report prompt with actual values."""
    return ENTERPRISE_PROMPTS["risk_report"].format(
        industry=industry,
        z_score=z_score,
        current_ratio=current_ratio,
        debt_to_equity=debt_to_equity,
        lawsuits=lawsuits,
        esg=esg
    )


# =============================================================================
# CEO PROMPTS (Management Quality)
# =============================================================================
CEO_PROMPTS = {
    "resume": """You are writing a professional bio for a CEO.
Write exactly 2 complete sentences summarizing their career.

Profile:
- Name: {name}
- Industry: {industry}
- Years of Experience: {experience}
- Track Record: {track_record} (e.g., "Led IPO", "Bankrupted previous startup")

Rules:
- Write in third person (e.g., "{name} is a...")
- Do NOT use placeholders
- If track record is negative, mention it subtly
- End with a period

Output ONLY the 2 sentences, nothing else."""
}

def get_ceo_prompt(name: str, industry: str, experience: int, track_record: str) -> str:
    """Format the CEO resume prompt with actual values."""
    return CEO_PROMPTS["resume"].format(
        name=name,
        industry=industry,
        experience=experience,
        track_record=track_record
    )
