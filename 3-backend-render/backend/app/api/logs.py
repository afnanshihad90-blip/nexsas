"""
NEXUS MEDIA AI — System Activity Logs Endpoints
Routes:
- GET /api/logs
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import PaginationParams, get_pagination, require_admin
from app.schemas.payloads import PaginationMeta, SystemLogItemSchema, SystemLogListResponse
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import list_system_logs_service

router = APIRouter(prefix="/api/logs", tags=["System Logs"])


@router.get(
    "",
    response_model=SystemLogListResponse,
    summary="List structured system audit logs (Admin role required)",
)
async def list_system_logs(
    severity: Optional[str] = Query(default=None, description="Filter by log severity"),
    pagination: PaginationParams = Depends(get_pagination),
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> SystemLogListResponse:
    items, total, db_status = await list_system_logs_service(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
        severity_filter=severity,
    )
    return SystemLogListResponse(
        items=[SystemLogItemSchema(**item) for item in items],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
        ),
        database_status=db_status,
    )
