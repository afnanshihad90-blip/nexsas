"""
NEXUS MEDIA AI — Editorial Articles Endpoints
Routes:
- GET /api/articles
- GET /api/articles/{article_id}
- POST /api/articles
- POST /api/articles/{article_id}/approve
- POST /api/articles/{article_id}/publish
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import (
    PaginationParams,
    get_pagination,
    require_admin,
    require_editor_or_admin,
)
from app.schemas.payloads import (
    ArticleCreateRequest,
    ArticleItemSchema,
    ArticleLifecycleRequest,
    ArticleLifecycleResponse,
    ArticleListResponse,
    PaginationMeta,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import (
    DatabaseUnavailableError,
    create_article_service,
    get_article_by_id_service,
    list_articles_service,
    transition_article_state_service,
)

router = APIRouter(prefix="/api/articles", tags=["Articles & Editorial"])


@router.get("", response_model=ArticleListResponse, summary="List editorial articles")
async def list_articles(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by article status"),
    pagination: PaginationParams = Depends(get_pagination),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ArticleListResponse:
    items, total, db_status = await list_articles_service(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
        status_filter=status_filter,
    )
    return ArticleListResponse(
        items=[ArticleItemSchema(**item) for item in items],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
        ),
        database_status=db_status,
    )


@router.get("/{article_id}", response_model=ArticleItemSchema, summary="Get single article by ID or slug")
async def get_article(
    article_id: str,
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ArticleItemSchema:
    item, db_status = await get_article_by_id_service(session=session, article_id=article_id)
    if db_status != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot query article '{article_id}' while database is '{db_status}'.",
                "database_status": db_status,
            },
        )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARTICLE_NOT_FOUND", "message": f"Article '{article_id}' was not found."},
        )
    return ArticleItemSchema(**item)


@router.post(
    "/pipeline/run",
    summary="Trigger the autonomous news-to-article pipeline (Editor/Operator/Admin)",
)
async def trigger_autonomous_pipeline(
    custom_headline: Optional[str] = Query(default=None),
    publishing_mode: Optional[str] = Query(default=None),
    principal: AuthenticatedPrincipal = Depends(require_editor_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
):
    from app.services.pipeline import run_autonomous_editorial_pipeline
    return await run_autonomous_editorial_pipeline(
        session=session,
        custom_headline=custom_headline,
        override_mode=publishing_mode,
    )


@router.post(
    "",
    response_model=ArticleItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new editorial article draft (Editor or Admin role required)",
)
async def create_article(
    payload: ArticleCreateRequest,
    principal: AuthenticatedPrincipal = Depends(require_editor_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ArticleItemSchema:
    try:
        created = await create_article_service(
            session=session,
            payload=payload.model_dump(),
        )
        return ArticleItemSchema(**created)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": exc.message},
        ) from exc


@router.post(
    "/{article_id}/approve",
    response_model=ArticleLifecycleResponse,
    summary="Approve an article for editorial publication (Editor or Admin role required)",
)
async def approve_article(
    article_id: str,
    payload: Optional[ArticleLifecycleRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_editor_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ArticleLifecycleResponse:
    try:
        result = await transition_article_state_service(
            session=session,
            article_id=article_id,
            target_status="approved",
            actor_sub=principal.sub,
            notes=payload.notes if payload else None,
        )
        return ArticleLifecycleResponse(**result)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": exc.message},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARTICLE_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/{article_id}/publish",
    response_model=ArticleLifecycleResponse,
    summary="Publish an approved article (Admin role required)",
)
async def publish_article(
    article_id: str,
    payload: Optional[ArticleLifecycleRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ArticleLifecycleResponse:
    try:
        result = await transition_article_state_service(
            session=session,
            article_id=article_id,
            target_status="published",
            actor_sub=principal.sub,
            notes=payload.notes if payload else None,
        )
        return ArticleLifecycleResponse(**result)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": exc.message},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARTICLE_NOT_FOUND", "message": str(exc)},
        ) from exc
