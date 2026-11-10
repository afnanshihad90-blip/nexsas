"""
NEXUS MEDIA AI — Step 5: News Intelligence API Endpoints
Routes (static sub-paths declared before /{news_id}):
- GET   /api/news
- GET   /api/news/trending
- GET   /api/news/categories
- GET   /api/news/sources
- GET   /api/news/clusters
- GET   /api/news/collection/status
- GET   /api/news/{news_id}
- POST  /api/news/scan
- POST  /api/news/sources
- PATCH /api/news/sources/{source_id}
- POST  /api/news/{news_id}/classify
- POST  /api/news/{news_id}/archive
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import (
    PaginationParams,
    get_pagination,
    require_admin,
    require_operator_or_admin,
)
from app.intelligence.engine import get_news_intelligence_engine
from app.intelligence.security import SSRFValidationError
from app.schemas.payloads import (
    NewsArchiveRequest,
    NewsCategoryListResponse,
    NewsCategorySchema,
    NewsClassifyRequest,
    NewsItemSchema,
    NewsListResponse,
    NewsScanRequest,
    NewsSourceCreateRequest,
    NewsSourceListResponse,
    NewsSourceSchema,
    NewsSourceUpdateRequest,
    PaginationMeta,
    StoryClusterListResponse,
    TrendingListResponse,
    TrendingStorySchema,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import get_news_by_id_service, list_news_service

router = APIRouter(prefix="/api/news", tags=["News Intelligence"])


@router.get("", response_model=NewsListResponse, summary="List discovered news items with filtering and pagination")
async def list_news(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by news status"),
    category: Optional[str] = Query(default=None, description="Filter by category slug"),
    source: Optional[str] = Query(default=None, description="Filter by source ID or name"),
    date_from: Optional[str] = Query(default=None, alias="date", description="Filter by publication/discovery date prefix"),
    search: Optional[str] = Query(default=None, description="Search by headline or summary"),
    pagination: PaginationParams = Depends(get_pagination),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> NewsListResponse:
    items, total, db_status = await list_news_service(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
        status_filter=status_filter,
    )

    if db_status != "connected":
        engine = get_news_intelligence_engine()
        memory_items = list(engine.news_items.values())
        if status_filter:
            memory_items = [i for i in memory_items if i.get("status") == status_filter]
        if category:
            memory_items = [i for i in memory_items if i.get("category") == category]
        if source:
            src_q = source.lower()
            memory_items = [
                i
                for i in memory_items
                if src_q in str(i.get("source_id", "")).lower()
                or src_q in str(i.get("source_name", "")).lower()
            ]
        if date_from:
            memory_items = [
                i
                for i in memory_items
                if str(i.get("publication_timestamp") or i.get("discovered_at") or "").startswith(date_from)
            ]
        if search:
            q = search.lower()
            memory_items = [
                i
                for i in memory_items
                if q in str(i.get("headline", "")).lower()
                or q in str(i.get("summary", "")).lower()
            ]

        total = len(memory_items)
        sliced = memory_items[pagination.offset : pagination.offset + pagination.page_size]
        return NewsListResponse(
            items=[NewsItemSchema(**item) for item in sliced],
            pagination=PaginationMeta(
                page=pagination.page,
                page_size=pagination.page_size,
                total_items=total,
            ),
            database_status=db_status,
        )

    return NewsListResponse(
        items=[NewsItemSchema(**item) for item in items],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
        ),
        database_status=db_status,
    )


@router.get("/trending", response_model=TrendingListResponse, summary="List weighted trending stories and score breakdowns")
async def list_trending_news(
    category: Optional[str] = Query(default=None, description="Filter by category slug"),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0, description="Minimum trend score filter"),
) -> TrendingListResponse:
    engine = get_news_intelligence_engine()
    stories = engine.list_trending_stories(category_slug=category, min_score=min_score)
    return TrendingListResponse(
        items=[TrendingStorySchema(**story) for story in stories],
        database_status="not_configured",
    )


@router.get("/categories", response_model=NewsCategoryListResponse, summary="List supported news niches and configurations")
async def list_news_categories() -> NewsCategoryListResponse:
    engine = get_news_intelligence_engine()
    categories = engine.list_categories()
    return NewsCategoryListResponse(
        items=[NewsCategorySchema(**cat) for cat in categories],
        database_status="not_configured",
    )


@router.get("/sources", response_model=NewsSourceListResponse, summary="List configured news source connectors")
async def list_news_sources() -> NewsSourceListResponse:
    engine = get_news_intelligence_engine()
    sources = engine.list_sources()
    return NewsSourceListResponse(
        items=[NewsSourceSchema(**src) for src in sources],
        database_status="not_configured",
    )


@router.get("/clusters", response_model=StoryClusterListResponse, summary="List deduplicated event story clusters")
async def list_news_clusters() -> StoryClusterListResponse:
    engine = get_news_intelligence_engine()
    return StoryClusterListResponse(
        items=engine.list_clusters(),
        database_status="not_configured",
    )


@router.get("/collection/status", summary="Get news collection engine & Cloudflare Worker scheduler status")
async def get_collection_status() -> Dict[str, Any]:
    engine = get_news_intelligence_engine()
    return engine.get_collection_status()


@router.post("/scan", summary="Trigger a scheduled or manual news collection scan")
async def trigger_news_scan(
    payload: NewsScanRequest,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
) -> Dict[str, Any]:
    engine = get_news_intelligence_engine()
    try:
        result = engine.run_collection_scan(
            idempotency_key=payload.idempotency_key,
            trigger_source=payload.trigger_source or f"operator:{principal.subject}",
            source_ids=payload.source_ids,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SCAN_OVERLAP_PREVENTED", "message": str(exc)},
        ) from exc


@router.post("/sources", response_model=NewsSourceSchema, status_code=status.HTTP_201_CREATED, summary="Register a new news source connector (Admin only)")
async def create_news_source(
    payload: NewsSourceCreateRequest,
    _principal: AuthenticatedPrincipal = Depends(require_admin),
) -> NewsSourceSchema:
    engine = get_news_intelligence_engine()
    try:
        created = engine.add_source(
            name=payload.name,
            endpoint_url=payload.endpoint_url,
            connector_type=payload.connector_type,
            protocol=payload.protocol,
            trust_tier=payload.trust_tier,
            reliability_score=payload.reliability_score,
            poll_interval_seconds=payload.poll_interval_seconds,
            category_slug=payload.category_slug,
            robots_txt_compliant=payload.robots_txt_compliant,
            terms_approved=payload.terms_approved,
        )
        return NewsSourceSchema(**created)
    except SSRFValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SSRF_VALIDATION_FAILED", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SOURCE_CONFIG", "message": str(exc)},
        ) from exc


@router.patch("/sources/{source_id}", response_model=NewsSourceSchema, summary="Update or test a news source connector (Admin only)")
async def update_news_source(
    source_id: str,
    payload: NewsSourceUpdateRequest,
    _principal: AuthenticatedPrincipal = Depends(require_admin),
) -> NewsSourceSchema:
    engine = get_news_intelligence_engine()
    try:
        updated = engine.update_source(
            source_id=source_id,
            is_enabled=payload.is_enabled,
            endpoint_url=payload.endpoint_url,
            poll_interval_seconds=payload.poll_interval_seconds,
            reliability_score=payload.reliability_score,
            category_slug=payload.category_slug,
            test_connection=payload.test_connection,
        )
        return NewsSourceSchema(**updated)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": str(exc)},
        ) from exc
    except SSRFValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SSRF_VALIDATION_FAILED", "message": str(exc)},
        ) from exc


@router.post("/{news_id}/classify", response_model=NewsItemSchema, summary="Classify or re-classify a discovered news item")
async def classify_news_item(
    news_id: str,
    payload: NewsClassifyRequest,
    _principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
) -> NewsItemSchema:
    engine = get_news_intelligence_engine()
    try:
        updated = engine.classify_existing_item(
            news_id=news_id,
            category_override=payload.category_slug,
        )
        return NewsItemSchema(**updated)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NEWS_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post("/{news_id}/archive", response_model=NewsItemSchema, summary="Archive a discovered news item")
async def archive_news_item(
    news_id: str,
    payload: NewsArchiveRequest,
    _principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
) -> NewsItemSchema:
    engine = get_news_intelligence_engine()
    try:
        archived = engine.archive_news_item(news_id=news_id, reason=payload.reason)
        return NewsItemSchema(**archived)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NEWS_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.get("/{news_id}", response_model=NewsItemSchema, summary="Get single discovered news item")
async def get_news_item(
    news_id: str,
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> NewsItemSchema:
    engine = get_news_intelligence_engine()
    if news_id in engine.news_items:
        return NewsItemSchema(**engine.news_items[news_id])

    item, db_status = await get_news_by_id_service(session=session, news_id=news_id)
    if db_status != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot query news item '{news_id}' while database is '{db_status}'.",
                "database_status": db_status,
            },
        )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NEWS_NOT_FOUND", "message": f"News item '{news_id}' was not found."},
        )
    return NewsItemSchema(**item)
