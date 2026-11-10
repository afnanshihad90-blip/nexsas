"""
NEXUS MEDIA AI — Publishing Queue Endpoints
Routes:
- GET /api/publishing/jobs
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import (
    PaginationParams,
    get_pagination,
    require_operator_or_admin,
)
from app.schemas.payloads import (
    PaginationMeta,
    PublishingJobListResponse,
    PublishingJobSchema,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import list_publishing_jobs_service

router = APIRouter(prefix="/api/publishing", tags=["Publishing & Distribution"])


@router.get(
    "/jobs",
    response_model=PublishingJobListResponse,
    summary="List multi-channel publishing jobs (Operator or Admin role required)",
)
async def list_publishing_jobs(
    pagination: PaginationParams = Depends(get_pagination),
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> PublishingJobListResponse:
    items, total, db_status = await list_publishing_jobs_service(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PublishingJobListResponse(
        items=[PublishingJobSchema(**item) for item in items],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
        ),
        database_status=db_status,
    )
