"""
Database Repository - CRUD operations for decisions and agent cache.

Uses asyncpg for async PostgreSQL operations with Supabase.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Any
import hashlib

import asyncpg
from asyncpg import Pool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

# Connection pool
_pool: Optional[Pool] = None


async def get_pool() -> Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _pool


async def init_db():
    """Initialize database connection pool."""
    global _pool
    try:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        print("✅ Database connection: OK")
    except Exception as e:
        print(f"⚠️  Database connection: FAILED - {e}")
        raise


async def close_db():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("👋 Database connection closed")


# =============================================================================
# DECISIONS
# =============================================================================

async def save_decision(
    decision_id: str,
    application: dict,
    application_type: str,
    risk_verdict: Optional[dict] = None,
    fairness_verdict: Optional[dict] = None,
    trajectory_verdict: Optional[dict] = None,
    final_decision: Optional[dict] = None
) -> str:
    """
    Save a decision to the database.
    
    Returns the decision_id.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO decisions (
                decision_id, application, application_type,
                risk_verdict, fairness_verdict, trajectory_verdict,
                final_decision, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (decision_id) DO UPDATE SET
                risk_verdict = EXCLUDED.risk_verdict,
                fairness_verdict = EXCLUDED.fairness_verdict,
                trajectory_verdict = EXCLUDED.trajectory_verdict,
                final_decision = EXCLUDED.final_decision
        """,
            decision_id,
            json.dumps(application),
            application_type,
            json.dumps(risk_verdict) if risk_verdict else None,
            json.dumps(fairness_verdict) if fairness_verdict else None,
            json.dumps(trajectory_verdict) if trajectory_verdict else None,
            json.dumps(final_decision) if final_decision else None,
            datetime.now(timezone.utc)
        )
    
    return decision_id


async def get_decision(decision_id: str) -> Optional[dict]:
    """
    Retrieve a decision by ID.
    
    Returns None if not found.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                decision_id, application, application_type,
                risk_verdict, fairness_verdict, trajectory_verdict,
                final_decision, created_at
            FROM decisions
            WHERE decision_id = $1
        """, decision_id)
    
    if not row:
        return None
    
    return {
        "decision_id": row["decision_id"],
        "application": json.loads(row["application"]) if row["application"] else {},
        "application_type": row["application_type"],
        "risk_verdict": json.loads(row["risk_verdict"]) if row["risk_verdict"] else None,
        "fairness_verdict": json.loads(row["fairness_verdict"]) if row["fairness_verdict"] else None,
        "trajectory_verdict": json.loads(row["trajectory_verdict"]) if row["trajectory_verdict"] else None,
        "final_decision": json.loads(row["final_decision"]) if row["final_decision"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None
    }


async def get_application(decision_id: str) -> Optional[dict]:
    """
    Retrieve just the application data for a decision.
    
    Used by on-demand agents.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT application
            FROM decisions
            WHERE decision_id = $1
        """, decision_id)
    
    if not row:
        return None
    
    return json.loads(row["application"]) if row["application"] else None


async def decision_exists(decision_id: str) -> bool:
    """Check if a decision exists."""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 1 FROM decisions WHERE decision_id = $1
        """, decision_id)
    
    return row is not None


# =============================================================================
# AGENT CACHE
# =============================================================================

def _make_cache_key(agent_type: str, extra: Optional[dict] = None) -> str:
    """Generate a cache key for an agent response."""
    if extra:
        extra_str = json.dumps(extra, sort_keys=True)
        extra_hash = hashlib.md5(extra_str.encode()).hexdigest()[:8]
        return f"{agent_type}_{extra_hash}"
    return agent_type


async def save_agent_cache(
    decision_id: str,
    agent_type: str,
    response: dict,
    extra: Optional[dict] = None
) -> None:
    """
    Cache an on-demand agent response.
    
    Args:
        decision_id: The decision this cache belongs to
        agent_type: Type of agent (advisor, narrative, comparator, scenario)
        response: The agent's response to cache
        extra: Optional extra data to include in cache key (e.g., custom scenarios)
    """
    pool = await get_pool()
    cache_key = _make_cache_key(agent_type, extra)
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO agent_cache (decision_id, agent_type, cache_key, response, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (decision_id, agent_type, cache_key) DO UPDATE SET
                response = EXCLUDED.response,
                created_at = EXCLUDED.created_at
        """,
            decision_id,
            agent_type,
            cache_key,
            json.dumps(response),
            datetime.now(timezone.utc)
        )


async def get_agent_cache(
    decision_id: str,
    agent_type: str,
    extra: Optional[dict] = None
) -> Optional[dict]:
    """
    Retrieve a cached agent response.
    
    Returns None if not found.
    """
    pool = await get_pool()
    cache_key = _make_cache_key(agent_type, extra)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT response
            FROM agent_cache
            WHERE decision_id = $1 AND agent_type = $2 AND cache_key = $3
        """, decision_id, agent_type, cache_key)
    
    if not row:
        return None
    
    return json.loads(row["response"]) if row["response"] else None


# =============================================================================
# SYNC WRAPPERS (for non-async code)
# =============================================================================

def save_decision_sync(
    decision_id: str,
    application: dict,
    application_type: str,
    risk_verdict: Optional[dict] = None,
    fairness_verdict: Optional[dict] = None,
    trajectory_verdict: Optional[dict] = None,
    final_decision: Optional[dict] = None
) -> str:
    """Synchronous wrapper for save_decision."""
    return asyncio.get_event_loop().run_until_complete(
        save_decision(
            decision_id, application, application_type,
            risk_verdict, fairness_verdict, trajectory_verdict, final_decision
        )
    )


def get_decision_sync(decision_id: str) -> Optional[dict]:
    """Synchronous wrapper for get_decision."""
    return asyncio.get_event_loop().run_until_complete(
        get_decision(decision_id)
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("Testing Database Repository...")
        print("=" * 50)
        
        await init_db()
        
        # Test save
        test_id = "TEST-12345678"
        await save_decision(
            decision_id=test_id,
            application={"test": True, "amount": 50000},
            application_type="client",
            final_decision={"decision": "APPROVE", "confidence": "HIGH"}
        )
        print(f"✅ Saved decision: {test_id}")
        
        # Test retrieve
        result = await get_decision(test_id)
        print(f"✅ Retrieved decision: {result['decision_id']}")
        print(f"   Application: {result['application']}")
        print(f"   Final Decision: {result['final_decision']}")
        
        # Test cache
        await save_agent_cache(test_id, "advisor", {"test": "response"})
        cached = await get_agent_cache(test_id, "advisor")
        print(f"✅ Cache test: {cached}")
        
        await close_db()
        print("\n✅ All tests passed!")
    
    asyncio.run(test())
