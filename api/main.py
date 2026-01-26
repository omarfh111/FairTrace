"""
FairTrace API - Credit Decision Service

Production-grade FastAPI application for multi-agent credit decisioning.

Usage:
    uvicorn api.main:app --reload --port 8000

Endpoints:
    POST /api/v1/decisions     - Submit application for credit decision
    GET  /api/v1/decisions/:id - Retrieve a previous decision
    GET  /api/v1/health        - Health check
    GET  /docs                 - OpenAPI documentation
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from api.schemas import HealthResponse
from api.routes import decisions_router, chat_router

# App metadata
APP_TITLE = "FairTrace API"
APP_DESCRIPTION = """
## Multi-Agent Credit Decision System

FairTrace uses a multi-agent architecture to evaluate credit applications:

- **Risk Agent**: Identifies red flags and reasons to reject
- **Fairness Agent**: Ensures equitable treatment
- **Trajectory Agent**: Predicts future outcomes
- **Orchestrator**: Synthesizes a final decision

### Features
- Hybrid vector search (dense + sparse embeddings)
- Redis semantic caching for performance
- LangSmith tracing for observability
- Structured responses with evidence

### Quick Start
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/decisions",
    json={
        "application": {
            "sector": "SaaS",
            "arr_current": 500000,
            "burn_multiple": 5.5,
            "runway_months": 6,
            "vc_backing": False
        }
    }
)
print(response.json()["final_decision"]["recommendation"])
```
"""
APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("🚀 FairTrace API starting...")
    print(f"📍 API docs available at: http://localhost:8000/docs")
    
    # Check dependencies
    try:
        from tools.qdrant_retriever import get_qdrant_client
        get_qdrant_client()
        print("✅ Qdrant connection: OK")
    except Exception as e:
        print(f"⚠️  Qdrant connection: FAILED - {e}")
    
    # Initialize database
    try:
        from db import repository as db
        await db.init_db()
    except Exception as e:
        print(f"⚠️  Database connection: FAILED - {e}")
    
    try:
        from tools.embedding_cache import get_redis_client
        get_redis_client().ping()
        print("✅ Redis connection: OK")
    except Exception as e:
        print(f"⚠️  Redis connection: FAILED - {e}")
    
    yield
    
    # Shutdown
    print("👋 FairTrace API shutting down...")
    
    # Close database connection
    try:
        from db import repository as db
        await db.close_db()
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "FairTrace API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health Check",
    description="Check the health of all system components."
)
async def health_check() -> HealthResponse:
    """Check health of all system components."""
    components = {}
    overall_status = "healthy"
    
    # Check Qdrant
    try:
        from tools.qdrant_retriever import get_qdrant_client
        client = get_qdrant_client()
        # Try to list collections to verify connection
        client.get_collections()
        components["qdrant"] = "ok"
    except Exception:
        components["qdrant"] = "error"
        overall_status = "degraded"
    
    # Check Redis
    try:
        from tools.embedding_cache import get_redis_client
        get_redis_client().ping()
        components["redis"] = "ok"
    except Exception:
        components["redis"] = "error"
        overall_status = "degraded"
    
    # Check Ollama (embedding model)
    try:
        import ollama
        ollama.list()
        components["ollama"] = "ok"
    except Exception:
        components["ollama"] = "error"
        overall_status = "degraded"
    
    # Check OpenAI
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and len(api_key) > 10:
            components["openai"] = "ok"
        else:
            components["openai"] = "error"
            overall_status = "degraded"
    except Exception:
        components["openai"] = "error"
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=APP_VERSION,
        components=components,
        timestamp=datetime.now(timezone.utc)
    )


# Error handlers
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# For running directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
