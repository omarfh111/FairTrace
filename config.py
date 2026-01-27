"""
Centralized Configuration - All settings from environment variables.

Usage:
    from config import settings
    
    print(settings.DATABASE_URL)
    print(settings.OPENAI_API_KEY)
"""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL connection string for Supabase"
    )
    
    # Vector Database (Qdrant)
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key for cloud instances"
    )
    
    # LLM (OpenAI)
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model"
    )
    
    # Embeddings (Ollama)
    OLLAMA_HOST: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    EMBEDDING_MODEL: str = Field(
        default="qwen3-embedding:0.6b",
        description="Dense embedding model"
    )
    
    # LangSmith Observability
    LANGCHAIN_TRACING_V2: bool = Field(
        default=True,
        description="Enable LangSmith tracing"
    )
    LANGCHAIN_API_KEY: Optional[str] = Field(
        default=None,
        description="LangSmith API key"
    )
    LANGCHAIN_PROJECT: str = Field(
        default="fairtrace",
        description="LangSmith project name"
    )
    
    # API Configuration
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    API_PORT: int = Field(
        default=8000,
        description="API server port"
    )
    
    # CORS
    CORS_ORIGINS: str = Field(
        default="*",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Redis (optional caching)
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()


# Validation at import time
def validate_settings():
    """Validate critical settings are present."""
    errors = []
    
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required")
    
    if not settings.QDRANT_URL:
        errors.append("QDRANT_URL is required")
    
    if errors:
        print("⚠️  Configuration warnings:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Configuration: All required settings present")


if __name__ == "__main__":
    print("Configuration Test")
    print("=" * 40)
    print(f"DATABASE_URL: {'SET' if settings.DATABASE_URL else 'NOT SET'}")
    print(f"QDRANT_URL: {settings.QDRANT_URL}")
    print(f"OPENAI_API_KEY: {'SET' if settings.OPENAI_API_KEY else 'NOT SET'}")
    print(f"LANGCHAIN_PROJECT: {settings.LANGCHAIN_PROJECT}")
    validate_settings()
