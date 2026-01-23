"""
Configuration centralisée pour le système multi-agents de décision de crédit.
Utilise des modèles économiques pour rester dans le budget.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# API KEYS & ENDPOINTS
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"')
QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip()

# =============================================================================
# LANGSMITH TRACING (Cost Monitoring)
# =============================================================================
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "").strip().strip('"')
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "fairtrace").strip()

# =============================================================================
# LLM CONFIGURATION (Économique)
# =============================================================================
# gpt-4o-mini: ~$0.15/1M input, $0.60/1M output (très économique)
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3  # Plus déterministe pour les décisions financières

# =============================================================================
# EMBEDDING CONFIGURATION (Local - Gratuit)
# =============================================================================
DENSE_MODEL = "mxbai-embed-large"
DENSE_DIM = 1024
SPARSE_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"

# =============================================================================
# QDRANT COLLECTIONS
# =============================================================================
COLLECTIONS = {
    "clients": "clients_v2",
    "startups": "startups_v2",
    "enterprises": "enterprises_v2"
}

# =============================================================================
# RETRIEVAL CONFIGURATION
# =============================================================================
TOP_K_SIMILAR = 5  # Nombre de cas similaires à récupérer
HYBRID_ALPHA = 0.7  # 0.7 dense + 0.3 sparse

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
AGENT_NAMES = {
    "financial": "Financial Metrics Agent",
    "risk": "Risk Pattern Agent",
    "narrative": "Narrative Analysis Agent",
    "prediction": "Prediction Agent",
    "orchestrator": "Orchestrator Agent"
}

# =============================================================================
# DECISION THRESHOLDS
# =============================================================================
THRESHOLDS = {
    # Clients
    "max_debt_to_income": 0.40,
    "max_missed_payments": 3,
    
    # Startups
    "min_runway_months": 6,
    "max_burn_multiple": 2.0,
    
    # Enterprises
    "altman_safe_zone": 3.0,
    "altman_grey_zone": 1.8,
    "min_current_ratio": 1.0
}

# =============================================================================
# VALIDATION
# =============================================================================
def validate_config():
    """Validate that all required configuration is present."""
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not found in .env")
    if not QDRANT_URL:
        errors.append("QDRANT_URL not found in .env")
    if not QDRANT_API_KEY:
        errors.append("QDRANT_API_KEY not found in .env")
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(errors))
    
    return True


if __name__ == "__main__":
    try:
        validate_config()
        print("✓ Configuration validated successfully")
        print(f"  LLM Model: {LLM_MODEL}")
        print(f"  Qdrant URL: {QDRANT_URL[:40]}...")
    except ValueError as e:
        print(f"✗ {e}")
