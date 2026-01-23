# 🏦 Credit Decision Memory

> Système Multi-Agents pour Décisions de Crédit Expliquables avec RAG

Un système d'aide à la décision de crédit basé sur l'IA qui utilise **6 agents spécialisés**, **RAG avec Qdrant**, et **LangGraph** pour fournir des décisions de crédit expliquables et traçables.

## 🎯 Fonctionnalités

- **🤖 6 Agents IA Spécialisés** - Analyse multi-dimensionnelle
- **🔍 RAG Hybride** - Recherche dense + sparse avec Qdrant
- **📄 Rapports PDF** - Documents professionnels téléchargeables
- **💡 Agent Conseiller** - Recommandations pour améliorer le profil
- **💬 Expert Comptable Chatbot** - Assistant IA interactif
- **📊 Décisions Expliquables** - Chaque décision cite des cas similaires historiques

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Streamlit                       │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐   │
│  │  Analyse    │ │   Conseils   │ │  Expert Comptable   │   │
│  │  de Crédit  │ │              │ │     Chatbot         │   │
│  └─────────────┘ └──────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator (LangGraph)                  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐    │
│  │Financial │ │  Risk    │ │ Narrative │ │ Prediction │    │
│  │  Agent   │ │  Agent   │ │   Agent   │ │   Agent    │    │
│  └──────────┘ └──────────┘ └───────────┘ └────────────┘    │
│                                                              │
│  ┌──────────┐ ┌────────────────────────────────────────┐   │
│  │ Advisor  │ │           Expert Chatbot               │   │
│  │  Agent   │ │                                        │   │
│  └──────────┘ └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Retriever                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ Dense Embed   │  │ Sparse Embed  │  │  RRF Fusion   │   │
│  │ (mxbai-large) │  │   (BM42)      │  │               │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Qdrant Vector Database                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ clients_v2  │ │ startups_v2 │ │   enterprises_v2    │   │
│  │  (5000)     │ │   (2500)    │ │      (1000)         │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Structure du Projet

```
hackthon/
├── agents/                      # Agents IA
│   ├── __init__.py
│   ├── config.py                # Configuration centralisée
│   ├── schemas.py               # Schémas Pydantic
│   ├── rag_retriever.py         # Module RAG Qdrant
│   ├── financial_agent.py       # Agent métriques financières
│   ├── risk_agent.py            # Agent détection risques
│   ├── narrative_agent.py       # Agent analyse textuelle
│   ├── prediction_agent.py      # Agent prédiction
│   ├── orchestrator.py          # Orchestrateur LangGraph
│   ├── advisor_agent.py         # Agent conseiller
│   ├── expert_chatbot.py        # Chatbot expert comptable
│   └── pdf_generator.py         # Génération PDF
├── data/                        # Données JSON
│   ├── clients.json             # 5000 clients
│   ├── startups.json            # 2500 startups
│   └── enterprises.json         # 1000 entreprises
├── ingestion/
│   └── ingest.py                # Script d'ingestion Qdrant
├── app.py                       # Interface Streamlit
├── main.py                      # CLI
├── requirements.txt             # Dépendances
└── .env                         # Variables d'environnement
```

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone <repo-url>
cd hackthon
```

### 2. Créer l'environnement virtuel

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # Linux/Mac
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créez un fichier `.env` à la racine :

```env
# Qdrant
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_URL=https://your-cluster.cloud.qdrant.io/

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LangSmith (optionnel - pour le tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=credit-decision
```

### 5. Ingérer les données dans Qdrant

```bash
python ingestion/ingest.py
```

### 6. Lancer l'application

```bash
streamlit run app.py
```

Ouvrez http://localhost:8501

## 🤖 Les 6 Agents

| Agent | Rôle | Métriques Analysées |
|-------|------|---------------------|
| 💰 **Financial** | Analyse financière | Ratios, revenus, dettes |
| ⚠️ **Risk** | Détection anomalies | Red flags, outliers |
| 📝 **Narrative** | Analyse textuelle | Pitch, historique crédit |
| 🔮 **Prediction** | Prédiction défaut | Probabilité, timeline |
| 💡 **Advisor** | Recommandations | Plan d'action |
| 💬 **Expert** | Chatbot comptable | Questions financières |

## 📊 Types de Demandeurs

### Client (Particulier)
- Revenu annuel, ratio dette/revenu
- Paiements manqués, utilisation crédit
- Type de contrat, ancienneté emploi

### Startup
- ARR, croissance, runway
- Burn rate, burn multiple
- VC backing, expérience fondateur

### Entreprise
- Score Altman Z, current ratio
- Marge nette, couverture intérêts
- ESG score, procès en cours

## 💰 Coûts

Le système utilise **gpt-4o-mini** pour être économique :

| Opération | Coût Estimé |
|-----------|-------------|
| 1 analyse complète | ~$0.002 |
| 100 analyses | ~$0.20 |
| 1000 analyses | ~$2.00 |

## 🔧 Configuration

Modifiez `agents/config.py` pour ajuster :

```python
# Modèle LLM
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3

# Seuils de décision
THRESHOLDS = {
    "max_debt_to_income": 0.40,
    "min_runway_months": 6,
    "altman_safe_zone": 3.0,
}
```

## 📝 Utilisation CLI

```bash
# Mode démo
python main.py --demo

# Mode interactif
python main.py --interactive

# Fichier JSON
python main.py --type client --json application.json
```

## 🧪 Tests

```bash
# Test connexion Qdrant
python -c "from agents.rag_retriever import test_connection; test_connection()"

# Test configuration
python -c "from agents.config import validate_config; validate_config(); print('OK')"
```

## 📄 Licence

MIT License

## 👥 Auteurs

Développé pour le hackathon avec ❤️
