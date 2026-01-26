# FairTrace - Multi-Agent Credit Decision System

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)

> **Production-grade, explainable AI credit decisioning with multi-agent orchestration, hybrid vector search, and real-time observability.**

![FairTrace Dashboard](docs/images/dashboard.png)

---

## ⚡ TL;DR

FairTrace is a production-grade AI credit decision system that:
- Uses **parallel multi-agent reasoning** instead of single-LLM prompts
- Combines **hybrid vector search (dense + sparse + RRF)** for evidence retrieval
- Produces **auditable, explainable decisions** with full observability
- Is designed for **real banking constraints** (fairness, regulation, traceability)

---

## ❗ Problem This Solves

Traditional credit decision systems suffer from:
- **Black-box ML** with poor explainability
- **Inconsistent decisions** for similar applicants
- **No audit trail** for regulators
- **Single-model failure modes**

FairTrace addresses these by using multiple debating agents, grounding decisions in historical cases, and storing every reasoning step.

---

## 🧪 Data Disclaimer

> This project uses **synthetic but realistic financial data** generated via LLMs. No real customer or banking data is used. The architecture and evaluation framework are **production-ready and data-agnostic**.

---

## 🎯 Overview

FairTrace is a **multi-agent AI system** that evaluates credit applications (consumer loans, startup funding, enterprise credit) using a debate-based architecture. Multiple specialized agents analyze each application from different perspectives, then an orchestrator synthesizes their verdicts into a final, explainable decision.

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Debate** | Risk, Fairness, and Trajectory agents debate each application |
| **Parallel Execution** | Agents run concurrently using async LangGraph (~10s total) |
| **Hybrid Vector Search** | Dense + sparse embeddings with Qdrant for case retrieval |
| **Persistent Storage** | Supabase PostgreSQL for decisions, agent cache, and audit logging |
| **On-Demand Agents** | Advisor, Narrative, Comparator, Scenario agents for deeper insights |
| **Regulation Agent** | RAG-powered chatbot for banking regulation Q&A (BCT circulars) |
| **Full Observability** | LangSmith tracing for every LLM call and retrieval |
| **Modern React UI** | Real-time dashboard with evidence visualization |

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              REACT FRONTEND                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Dashboard  │  │   Evidence  │  │  Decision   │  │   On-Demand Agent      │ │
│  │    View     │  │    Panel    │  │   Details   │  │       Panels           │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │ REST API (HTTP)
┌────────────────────────────────────▼────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                     │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         API Routes (/api/v1)                              │   │
│  │  POST /decisions  │  GET /decisions/{id}  │  GET /{id}/advisor, etc.     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                            │
│  ┌──────────────────────────────────▼──────────────────────────────────────┐    │
│  │                    LANGGRAPH DECISION WORKFLOW                           │    │
│  │                    (Parallel Async Execution)                            │    │
│  │                                                                          │    │
│  │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │    │
│  │    │   START     │────▶│             │────▶│             │                │    │
│  │    └──────┬──────┘    │             │    │             │                │    │
│  │           │           │             │    │             │                │    │
│  │     ┌─────┼─────┬─────┼─────────────┼────┼─────────────┘                │    │
│  │     │     │     │     │             │    │                              │    │
│  │     ▼     ▼     ▼     ▼             ▼    ▼                              │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐                                             │    │
│  │  │ RISK │ │FAIR- │ │TRAJ- │  ◀══════════════════════╗                   │    │
│  │  │AGENT │ │NESS  │ │ECTORY│         PARALLEL        ║                   │    │
│  │  │      │ │AGENT │ │AGENT │       EXECUTION         ║                   │    │
│  │  └──┬───┘ └──┬───┘ └──┬───┘                         ║                   │    │
│  │     │        │        │                             ║                   │    │
│  │     └────────┼────────┘                             ║                   │    │
│  │              ▼                                      ║                   │    │
│  │       ┌─────────────┐                               ║                   │    │
│  │       │ORCHESTRATOR │  Synthesizes final decision   ║                   │    │
│  │       │ (GPT-4o)    │                               ║                   │    │
│  │       └──────┬──────┘                               ║                   │    │
│  │              ▼                                      ║                   │    │
│  │       ┌─────────────┐                               ║                   │    │
│  │       │    END      │                               ║                   │    │
│  │       └─────────────┘                               ║                   │    │
│  └─────────────────────────────────────────────────────╩────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      ON-DEMAND AGENTS (Lazy Loaded)                       │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐             │   │
│  │  │  ADVISOR  │  │ NARRATIVE │  │COMPARATOR │  │ SCENARIO  │             │   │
│  │  │   AGENT   │  │   AGENT   │  │   AGENT   │  │   AGENT   │             │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘             │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────────┐     ┌─────────────────┐
│    SUPABASE     │      │   QDRANT VECTOR DB  │     │    LANGSMITH    │
│   POSTGRESQL    │      │                     │     │   OBSERVABILITY │
│                 │      │  ┌───────────────┐  │     │                 │
│  • Decisions    │      │  │ 1000+ Cases   │  │     │  • LLM Traces   │
│  • Agent Cache  │      │  │ (3 types)     │  │     │  • Latency      │
│  • Applications │      │  └───────────────┘  │     │  • Token Usage  │
└─────────────────┘      └─────────────────────┘     └─────────────────┘
```

---

<details>
<summary>🔄 RAG Pipeline Architecture (click to expand)</summary>

Each agent uses a sophisticated Retrieval-Augmented Generation (RAG) pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE (per Agent)                               │
└─────────────────────────────────────────────────────────────────────────────────┘

 APPLICATION DATA                           QUERY PROCESSING
 ┌─────────────────┐                       ┌─────────────────────────────────────┐
 │ • age: 35       │                       │         LLM Query Builder           │
 │ • income: 55000 │ ─────────────────────▶│     (GPT-4o-mini generates          │
 │ • DTI: 0.35     │                       │      semantic search query)         │
 │ • purpose: home │                       └──────────────┬──────────────────────┘
 └─────────────────┘                                      │
                                                          ▼
                                           ┌─────────────────────────────────────┐
                                           │           QUERY PARSER              │
                                           │     (Extracts JSON filters)         │
                                           │    "income > 50k", "DTI < 0.4"      │
                                           └──────────────┬──────────────────────┘
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              HYBRID EMBEDDING                                    │
│                                                                                  │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐       │
│  │       DENSE EMBEDDINGS         │    │       SPARSE EMBEDDINGS        │       │
│  │                                │    │                                │       │
│  │   ┌────────────────────────┐   │    │   ┌────────────────────────┐   │       │
│  │   │   Ollama (Local)       │   │    │   │    FastEmbed BM25      │   │       │
│  │   │   mxbai-embed-large    │   │    │   │   (Keyword matching)   │   │       │
│  │   │   (1024 dimensions)    │   │    │   │                        │   │       │
│  │   └────────────────────────┘   │    │   └────────────────────────┘   │       │
│  │                                │    │                                │       │
│  │   Captures: Semantic meaning   │    │   Captures: Exact terms,       │       │
│  │   "financial stability" ≈      │    │   acronyms, domain jargon      │       │
│  │   "economic security"          │    │   "DTI" = "DTI" exactly        │       │
│  └────────────────────────────────┘    └────────────────────────────────┘       │
│                    │                                    │                        │
│                    └────────────────┬───────────────────┘                        │
│                                     ▼                                            │
│                        ┌────────────────────────┐                                │
│                        │   RRF (Reciprocal Rank │                                │
│                        │        Fusion)         │                                │
│                        │                        │                                │
│                        │  Combines dense+sparse │                                │
│                        │  scores for best of    │                                │
│                        │  both approaches       │                                │
│                        └────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              QDRANT VECTOR SEARCH                                │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        COLLECTION: fairtrace_cases                       │    │
│  │                                                                          │    │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐    │    │
│  │  │   CLIENT    │     │   STARTUP   │     │      ENTERPRISE         │    │    │
│  │  │   CASES     │     │   CASES     │     │        CASES            │    │    │
│  │  │  (5000)      │     │   (2500)    │     │       (1000)            │    │    │
│  │  │             │     │             │     │                         │    │    │
│  │  │ • Loans     │     │ • Funding   │     │ • Credit lines          │    │    │
│  │  │ • Mortgages │     │ • VC rounds │     │ • Working capital       │    │    │
│  │  │ • Credit    │     │ • Seed/A/B  │     │ • Trade finance         │    │    │
│  │  └─────────────┘     └─────────────┘     └─────────────────────────┘    │    │
│  │                                                                          │    │
│  │  Each case contains:                                                     │    │
│  │  • Application data (metrics, financials)                               │    │
│  │  • Historical outcome (APPROVED, REJECTED, DEFAULT, etc.)               │    │
│  │  • Dense + Sparse embedding vectors                                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  Search Types:                                                                   │
│  • hybrid_search() - Combined dense+sparse with RRF                             │
│  • search_similar_outcomes() - Filter by outcome type                           │
│  • search_by_outcome_type() - Approved/rejected cases only                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT AUGMENTATION                                   │
│                                                                                  │
│  Retrieved Cases (Top 5-10):                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Case 1: Similar income, approved, 88% similarity                       │    │
│  │  Case 2: Similar DTI, defaulted, 85% similarity                         │    │
│  │  Case 3: Same industry, approved, 82% similarity                        │    │
│  │  ...                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│                                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    PROMPT CONSTRUCTION                                   │    │
│  │                                                                          │    │
│  │  System: "You are the Risk Agent. Analyze this application..."          │    │
│  │  Context: [Retrieved similar cases with outcomes]                        │    │
│  │  Application: [Current application data]                                 │    │
│  │  Task: "Provide risk assessment with evidence..."                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LLM GENERATION                                      │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         OpenAI GPT-4o-mini                               │    │
│  │                                                                          │    │
│  │   • Structured JSON output (json_object mode)                           │    │
│  │   • Temperature: 0 for consistency                                       │    │
│  │   • Traced via LangSmith                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│                                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         AGENT VERDICT                                    │    │
│  │  {                                                                       │    │
│  │    "recommendation": "CONDITIONAL",                                      │    │
│  │    "confidence": "MEDIUM",                                               │    │
│  │    "risk_level": "MEDIUM",                                               │    │
│  │    "reasoning": "Based on 5 similar cases...",                          │    │
│  │    "evidence": [                                                         │    │
│  │      {"entity_id": "C-001", "similarity": 0.88, "outcome": "APPROVED"}  │    │
│  │    ]                                                                     │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```
</details>

---

### 🤖 Agent Details

#### Core Decision Agents (Run in Parallel)

| Agent | Role | Search Strategy | Key Metrics |
|-------|------|-----------------|-------------|
| **Risk Agent** | Devil's advocate - finds reasons to reject | Search for similar cases that defaulted or were problematic | Risk level, red flags, mitigating factors |
| **Fairness Agent** | Ensures consistency with similar approved cases | Search for approved cases with similar profiles | Consistency score, similar approved count |
| **Trajectory Agent** | Predicts future outcomes based on patterns | Search for cases with similar starting points | Growth pattern, predicted outcome probability |

#### On-Demand Agents (Lazy-loaded on request)

| Agent | Trigger | Search Strategy | Output |
|-------|---------|-----------------|--------|
| **Advisor Agent** | User clicks "Get Recommendations" | Search for improved cases that got approved after changes | Specific, actionable improvement steps |
| **Narrative Agent** | User clicks "See Stories" | Search for notable success/failure stories | Compelling narratives with lessons learned |
| **Comparator Agent** | User clicks "Gap Analysis" | Search for top approved cases in same category | Metric-by-metric comparison with benchmarks |
| **Scenario Agent** | User defines what-if scenarios | Re-evaluate with modified application data | Probability changes, optimal path to approval |

#### Regulation Agent (Standalone)

| Agent | Trigger | Data Source | Output |
|-------|---------|-------------|--------|
| **Regulation Agent** | Chatbot in dashboard | BCT banking circulars (8,029 chunks) | Citation-aware answers with article references |


---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Qdrant Cloud](https://cloud.qdrant.io) account (free tier works)
- [OpenAI API](https://platform.openai.com) key
- [Supabase](https://supabase.com) project (free tier works)
- [Ollama](https://ollama.ai) (for local embeddings)

### 1. Clone and Setup

```bash
git clone https://github.com/omarfh111/FairTrace.git
cd FairTrace

# Create Python virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
# Supabase PostgreSQL
DATABASE_URL=postgresql://postgres.xxxxx:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres

# Qdrant Cloud
QDRANT_URL=https://your-cluster.region.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# LangSmith (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_your-langsmith-key
LANGCHAIN_PROJECT=fairtrace
```

### 3. Setup Supabase Database

Run this SQL in your Supabase SQL Editor:

```sql
-- Decisions table
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id TEXT UNIQUE NOT NULL,
    application JSONB NOT NULL,
    application_type TEXT NOT NULL,
    risk_verdict JSONB,
    fairness_verdict JSONB,
    trajectory_verdict JSONB,
    final_decision JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent cache table
CREATE TABLE agent_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(decision_id, agent_type, cache_key)
);
```

### Supabase Utility

Supabase provides:
- **Decision Persistence**: Every credit decision is stored with full agent verdicts for audit trails
- **Agent Cache**: On-demand agents (Advisor, Narrative, etc.) cache their responses to avoid redundant LLM calls
- **Query History**: All chat conversations with the Regulation Agent are persisted
- **Row-Level Security**: Production deployments can enable RLS for multi-tenant isolation

### 4. Generate Synthetic Data

```bash
# Start Ollama (in separate terminal)
ollama serve

# Pull embedding model
ollama pull mxbai-embed-large

# Generate synthetic cases and upload to Qdrant
python data_generation/generate_all_data.py
python data_generation/upload_to_qdrant.py
```

### 5. Run the Application

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

---

## 📁 Project Structure

```
fairtrace/
├── api/                        # FastAPI backend
│   ├── main.py                 # Application entry point
│   ├── schemas.py              # Pydantic models
│   └── routes/
│       └── decisions.py        # API endpoints
│
├── agents/                     # AI agents
│   ├── base_agent.py           # Shared LLM configuration
│   ├── risk_agent.py           # Risk assessment
│   ├── fairness_agent.py       # Fairness evaluation
│   ├── trajectory_agent.py     # Outcome prediction
│   ├── advisor_agent.py        # Improvement recommendations
│   ├── narrative_agent.py      # Historical narratives
│   ├── comparator_agent.py     # Gap analysis
│   └── scenario_agent.py       # What-if scenarios
│
├── graph/                      # LangGraph workflow
│   └── decision_graph.py       # Parallel agent orchestration
│
├── tools/                      # Agent tools
│   └── qdrant_retriever.py     # Hybrid vector search
│
├── db/                         # Database layer
│   ├── __init__.py
│   └── repository.py           # Async CRUD operations
│
├── data_generation/            # Synthetic data generation
│   ├── generate_data.py        # Main data generator script
│   ├── prompts_config.py       # LLM prompts for data generation
│   └── output/                 # Generated CSV/JSON files
│
├── ingestion/                  # Vector DB ingestion
│   └── ingest_to_qdrant.py     # Upload data to Qdrant
│
├── evaluation/                 # Evaluation framework
│   ├── generate_eval_dataset.py  # Creates golden Q&A pairs
│   ├── run_evaluation.py       # Runs evaluation metrics
│   ├── golden_qa.json          # Pre-generated evaluation data
│   ├── metrics/                # Custom metric implementations
│   └── reports/                # Evaluation output reports
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── lib/api.ts          # API client
│   │   └── types/              # TypeScript types
│   └── package.json
│
├── config.py                   # Centralized configuration
├── requirements.txt            # Python dependencies
└── .env.example                # Environment template
```

---

## 🔌 API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/decisions` | Submit application for decision |
| `GET` | `/decisions/{id}` | Retrieve decision by ID |
| `GET` | `/decisions` | List recent decisions |
| `GET` | `/decisions/{id}/advisor` | Get improvement recommendations |
| `GET` | `/decisions/{id}/narrative` | Get historical narratives |
| `GET` | `/decisions/{id}/comparator` | Get gap analysis |
| `POST` | `/decisions/{id}/scenario` | Run what-if scenarios |
| `GET` | `/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "application": {
      "age": 35,
      "contract_type": "CDI",
      "income_annual": 55000,
      "debt_to_income_ratio": 0.35,
      "missed_payments_last_12m": 1,
      "loan_purpose": "Home improvement"
    }
  }'
```

### Example Response

```json
{
  "decision_id": "abc123",
  "application_type": "client",
  "final_decision": {
    "recommendation": "CONDITIONAL",
    "confidence": "MEDIUM",
    "risk_level": "MEDIUM",
    "reasoning": "The application shows stable income but elevated DTI...",
    "conditions": ["Reduce debt-to-income below 0.30"],
    "key_factors": ["DTI ratio", "Payment history"]
  },
  "risk_verdict": {...},
  "fairness_verdict": {...},
  "trajectory_verdict": {...},
  "processing_time_ms": 10234
}
```

---

## 📊 Observability

### LangSmith Tracing

Every decision includes full tracing in LangSmith:

- Agent execution times (parallel visualization)
- Token usage and costs
- Vector search results
- LLM prompts and responses

![LangSmith Trace](docs/images/langsmith-trace.png)

### Agent Execution Traces

Our multi-agent system provides detailed execution traces for each agent:

| Advisor Agent | Credit Decision Flow |
|:-------------:|:--------------------:|
| ![Advisor Agent Trace](docs/images/trace_advisor_agent.png) | ![Credit Decision Trace](docs/images/trace_credit_decision.png) |

| Risk Agent | Trajectory Agent |
|:----------:|:----------------:|
| ![Risk Agent Trace](docs/images/trace_risk_agent.png) | ![Trajectory Agent Trace](docs/images/trace_trajectory_agent.png) |

### Qdrant Vector Collections

![Qdrant Collections](docs/images/qdrant_collections.png)

The system maintains 4 vector collections:
- `clients_v2` - 5,000 consumer credit cases
- `enterprises_v2` - 1,000 enterprise credit cases  
- `regulations_v2` - 8,029 banking regulation chunks (BCT)
- `startups_v2` - 2,500 startup funding cases

### Metrics Tracked

| Metric | Description |
|--------|-------------|
| `processing_time_ms` | Total decision time |
| `tokens_used` | Total tokens across all agents |
| `cost` | Estimated API cost |
| `cases_retrieved` | Number of similar cases found |

---

## 🧪 Evaluation

The evaluation framework measures:

1. **Retrieval Quality**: Are the right cases being retrieved?
2. **Decision Consistency**: Do similar applications get similar decisions?
3. **Explanation Quality**: Are the explanations coherent and helpful?

```bash
# Generate evaluation dataset
python evaluation/generate_eval_dataset.py

# Run evaluation
python evaluation/run_evaluation.py
```

---

## 🛠️ Development

### Code Quality

```bash
# Format code
pip install black isort
black .
isort .

# Lint
pip install ruff
ruff check .
```

### Adding a New Agent

1. Create `agents/your_agent.py` extending pattern from `base_agent.py`
2. Add hybrid search tool or other tools in `tools/`
3. Register endpoint in `api/routes/decisions.py`
4. Add response schema in `api/schemas.py`
5. Update frontend in `frontend/src/components/`

### Data Generation

```bash
# Generate synthetic cases (requires Ollama running)
python data_generation/generate_data.py

# Upload to Qdrant
python ingestion/ingest_to_qdrant.py
```

---

## 📊 Evaluation & Benchmarks

### Retrieval Performance (Post-Optimization)

| Configuration | Mean Relevance | MRR | Latency P50 |
|---------------|----------------|-----|-------------|
| **Baseline** | 0.549 | 0.000 | 194ms |
| **Optimized (Multi-ID Dataset)** | - | 0.243 | - |
| **Optimized (Parallel Embeddings)** | - | 0.243 | 135ms |
| **Final (Query Understanding)** | - | **0.322** | **310ms*** |
| *Experimental (with Reranker)* | - | 0.193 | 24,000ms |

*Note: Latency increased slightly due to LLM parsing overhead, but accuracy (MRR) improved significantly.*

*Note: Reranking was disabled for production as it increased latency 80x and degraded accuracy for this dataset.*



### Running Evaluations

```bash
# Standard retrieval metrics
python evaluation/run_evaluation.py --limit 50 --parse

```

### Key Takeaways

- Hybrid retrieval improved MRR by **~60%** over baseline
- Query understanding reduced false positives significantly
- Cross-encoder reranking was **removed** due to 80x latency increase with degraded accuracy
- Final system favors **consistency and explainability** over raw speed

---

## �📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- [Qdrant](https://qdrant.tech/) for vector search
- [Supabase](https://supabase.com/) for PostgreSQL hosting
- [OpenAI](https://openai.com/) for GPT-4o-mini
- [Ollama](https://ollama.ai/) for local embeddings

---

<div align="center">
  <b>Built with ❤️ for explainable AI credit decisions</b>
</div>

---

## 🎓 What This Project Demonstrates

- Designing **agentic AI systems** beyond simple chains
- Applying **RAG to structured + unstructured data**
- **Observability-first** AI development
- **Evaluation-driven** architecture decisions
- Production constraints (latency, auditability, fairness)

---

## ⚖️ Design Tradeoffs

| Decision | Rationale |
|----------|----------|
| **Multi-agent vs single prompt** | Improves robustness through disagreement; makes bias explicit; ~10s latency but much better explainability |
| **No cross-encoder reranker** | Increased latency 80x and degraded MRR; LLM query understanding + hybrid retrieval performed better |
| **Hybrid search** | Dense misses acronyms/numbers; sparse lacks semantics; RRF combines both strengths |
| **Supabase over local DB** | Free tier, managed PostgreSQL, built-in auth for future multi-tenancy |

---

## 🛣️ Roadmap

- [ ] Docker + Kubernetes deployment
- [ ] Human-in-the-loop decision overrides
- [ ] Online learning from decision outcomes
- [ ] Stress testing for fairness metrics
- [ ] Cross-encoder reranking via microservice (low-latency)
