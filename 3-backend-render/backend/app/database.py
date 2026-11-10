"""Async SQLAlchemy 2.x engine, Supabase Session Pooler support, and health checks."""

from __future__ import annotations

import logging
import ssl
from typing import AsyncGenerator, Dict, Optional

from app.config import AppSettings, get_settings

logger = logging.getLogger("nexus.database")

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SQLALCHEMY_AVAILABLE = False
    AsyncEngine = object  # type: ignore
    AsyncSession = object  # type: ignore

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def build_ssl_connect_args(settings: AppSettings) -> Dict[str, object]:
    """Configures asyncpg SSL parameters and Supabase Session Pooler compatibility."""
    connect_args: Dict[str, object] = {
        "command_timeout": 15,
        # Supabase PgBouncer / Session & Transaction Pooler safe prepared statement setting
        "statement_cache_size": 0,
    }
    ssl_mode = (settings.DATABASE_SSL or "require").strip().lower()
    if ssl_mode in ("require", "verify-ca", "verify-full", "true", "1"):
        ctx = ssl.create_default_context()
        if ssl_mode == "require":
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    return connect_args


def get_async_engine(settings: Optional[AppSettings] = None) -> Optional[AsyncEngine]:
    """Lazily initializes the SQLAlchemy 2.x AsyncEngine when DATABASE_URL is configured."""
    global _engine, _session_factory
    cfg = settings or get_settings()
    if not cfg.is_database_configured or not SQLALCHEMY_AVAILABLE:
        return None

    if _engine is None:
        _engine = create_async_engine(
            cfg.normalized_async_database_url,
            pool_pre_ping=True,
            pool_size=cfg.DB_POOL_SIZE,
            max_overflow=cfg.DB_MAX_OVERFLOW,
            pool_recycle=cfg.DB_POOL_RECYCLE_SECONDS,
            connect_args=build_ssl_connect_args(cfg),
            echo=False,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """FastAPI dependency yielding an AsyncSession or None when database is unconfigured."""
    get_async_engine()
    if _session_factory is None:
        yield None
        return

    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Disposes the async engine cleanly on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def probe_database_connection(settings: Optional[AppSettings] = None) -> Dict[str, object]:
    """
    Executes a real `SELECT 1` connection check against Supabase PostgreSQL.
    Never fabricates a connected state and never leaks connection credentials.
    """
    cfg = settings or get_settings()
    if not cfg.is_database_configured:
        return {
            "status": "not_configured",
            "connected": False,
            "pooler_compatible": True,
            "ssl_mode": cfg.DATABASE_SSL,
            "detail": "DATABASE_URL is not configured in server environment variables.",
        }

    engine = get_async_engine(cfg)
    if engine is None:
        return {
            "status": "disconnected",
            "connected": False,
            "pooler_compatible": True,
            "ssl_mode": cfg.DATABASE_SSL,
            "detail": "SQLAlchemy async driver unavailable.",
        }

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "connected": True,
            "pooler_compatible": True,
            "ssl_mode": cfg.DATABASE_SSL,
            "detail": "Verified active connection to Supabase PostgreSQL.",
        }
    except Exception as exc:
        logger.warning("Database connection health check failed: %s", exc.__class__.__name__)
        return {
            "status": "disconnected",
            "connected": False,
            "pooler_compatible": True,
            "ssl_mode": cfg.DATABASE_SSL,
            "detail": "Database connection check failed. Verify DATABASE_URL and network reachability.",
        }
