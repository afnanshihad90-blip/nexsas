"""
NEXUS MEDIA AI — System & Database Health Endpoints
Routes:
- GET /api/system/health
- GET /api/system/health/database
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.database import probe_database_connection
from app.schemas.payloads import DatabaseHealthResponse, SystemHealthResponse

router = APIRouter(prefix="/api/system/health", tags=["System Health"])


@router.get("", response_model=SystemHealthResponse, summary="Application & database health status")
async def get_system_health() -> SystemHealthResponse:
    """
    Returns overall application health and live database connection state.
    Matches the Step 3 required response schema:
    {
      "application": "NEXUS MEDIA AI",
      "status": "online",
      "database": "not_configured",
      "environment": "development",
      "version": "0.1.0"
    }
    """
    settings = get_settings()
    db_probe = await probe_database_connection()
    return SystemHealthResponse(
        application=settings.APP_NAME,
        status="online",
        database=str(db_probe.get("status", "not_configured")),
        environment=settings.APP_ENV,
        version=settings.APP_VERSION,
    )


@router.get(
    "/database",
    response_model=DatabaseHealthResponse,
    summary="Detailed Supabase PostgreSQL connection and pool health check",
)
async def get_database_health() -> DatabaseHealthResponse:
    """Probes the async SQLAlchemy engine and returns pool & SSL status without exposing credentials."""
    db_probe = await probe_database_connection()
    return DatabaseHealthResponse(
        status=str(db_probe.get("status", "not_configured")),
        configured=bool(db_probe.get("configured", False)),
        driver=str(db_probe.get("driver", "postgresql+asyncpg")),
        ssl_enabled=bool(db_probe.get("ssl_enabled", True)),
        session_pooler_compatible=bool(db_probe.get("session_pooler_compatible", True)),
        latency_ms=db_probe.get("latency_ms"),
        message=str(db_probe.get("message", "")),
        checked_at=datetime.now(timezone.utc),
    )
