"""
NEXUS MEDIA AI — Traffic & Revenue Analytics Endpoints
Routes:
- GET /api/analytics/traffic
- GET /api/analytics/revenue
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import require_admin
from app.schemas.payloads import (
    RevenueAnalyticsResponse,
    RevenuePointSchema,
    TrafficAnalyticsResponse,
    TrafficPointSchema,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import (
    list_revenue_analytics_service,
    list_traffic_analytics_service,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Telemetry"])


@router.get(
    "/traffic",
    response_model=TrafficAnalyticsResponse,
    summary="Get website traffic telemetry (Admin role required)",
)
async def get_traffic_analytics(
    limit: int = Query(default=30, ge=1, le=90),
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> TrafficAnalyticsResponse:
    items, db_status = await list_traffic_analytics_service(session=session, limit=limit)
    return TrafficAnalyticsResponse(
        items=[TrafficPointSchema(**item) for item in items],
        database_status=db_status,
    )


@router.get(
    "/revenue",
    response_model=RevenueAnalyticsResponse,
    summary="Get programmatic and direct revenue reports (Admin role required)",
)
async def get_revenue_analytics(
    limit: int = Query(default=30, ge=1, le=90),
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> RevenueAnalyticsResponse:
    items, db_status = await list_revenue_analytics_service(session=session, limit=limit)
    return RevenueAnalyticsResponse(
        items=[RevenuePointSchema(**item) for item in items],
        database_status=db_status,
    )
