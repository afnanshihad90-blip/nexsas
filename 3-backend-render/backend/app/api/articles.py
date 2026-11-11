"""
NEXUS MEDIA AI — Editorial Articles Endpoints
Routes:
- GET /api/articles
- GET /api/articles/{article_id}
- POST /api/articles
- POST /api/articles/{article_id}/approve
- POST /api/articles/{article_id}/publish
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import (
    PaginationParams,
    get_optional_principal,
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
    ScrapeAndPublishRequest,
    ScrapeAndPublishResponse,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import (
    DatabaseUnavailableError,
    create_article_service,
    get_article_by_id_service,
    list_articles_service,
    transition_article_state_service,
)

logger = logging.getLogger("nexus_media_ai.api.articles")

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
    image_url: Optional[str] = Query(default=None),
    source_url: Optional[str] = Query(default=None),
    principal: AuthenticatedPrincipal = Depends(require_editor_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
):
    from app.services.pipeline import run_autonomous_editorial_pipeline
    return await run_autonomous_editorial_pipeline(
        session=session,
        custom_headline=custom_headline,
        override_mode=publishing_mode,
        custom_image_url=image_url,
        source_url=source_url,
    )


@router.post(
    "/scrape-and-publish",
    response_model=ScrapeAndPublishResponse,
    summary="Deep-scrape source wire, synthesize full in-depth article with media, and publish to database & blog",
)
async def scrape_and_publish_article(
    payload: ScrapeAndPublishRequest,
    principal: Optional[AuthenticatedPrincipal] = Depends(get_optional_principal),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> ScrapeAndPublishResponse:
    from datetime import datetime, timezone
    import re
    import uuid
    from app.config import get_settings
    from app.intelligence.scraper import scrape_source_article, synthesize_rich_article
    from app.publishing.blog_client import push_article

    settings = get_settings()

    # 1. Scrape full content, inline images, and video embeds from the wire source
    scraped = scrape_source_article(payload.source_url)

    # 2. Get provider adapter if configured
    provider = None
    try:
        from app.agents.provider import AIProviderAdapter
        provider = AIProviderAdapter()
    except Exception as pr_err:
        logger.info("Provider adapter initialization notice: %s", pr_err)

    # 3. Synthesize rich, expansive editorial article preserving all media
    body_md = await synthesize_rich_article(
        headline=payload.headline,
        scraped_data=scraped,
        provider_adapter=provider,
        mode=payload.mode or "ai_rewrite",
    )

    # 4. Hero image selection
    hero_img = scraped.get("hero_image") or payload.image_url
    if not hero_img:
        cat_lower = (payload.category or "").lower()
        if any(k in cat_lower for k in ("science", "space", "astronomy", "physics")):
            hero_img = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80"
        elif any(k in cat_lower for k in ("market", "business", "finance", "economy")):
            hero_img = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&auto=format&fit=crop&q=80"
        else:
            hero_img = "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&auto=format&fit=crop&q=80"

    # 5. Clean slug generation
    clean_slug = re.sub(r"[^a-z0-9]+", "-", payload.headline.lower()).strip("-")[:120]
    if not clean_slug:
        clean_slug = f"story-{uuid.uuid4().hex[:8]}"

    word_count = len(body_md.split())
    first_para = scraped.get("paragraphs", [""])[0] if scraped.get("paragraphs") else payload.headline
    excerpt = first_para[:250] if first_para else payload.headline

    # 6. Database record creation & publishing
    article_id = str(uuid.uuid4())
    if session is not None:
        try:
            article_payload = {
                "title": payload.headline,
                "headline": payload.headline,
                "slug": clean_slug,
                "body_markdown": body_md,
                "content": body_md,
                "excerpt": excerpt,
                "summary": excerpt,
                "category": payload.category or "technology",
                "stage": "Published",
                "status": "published",
                "is_public": True,
                "primary_source_url": payload.source_url,
                "image_url": hero_img,
                "image_alt": payload.headline,
                "image_credit": "Original Wire Press Photo" if scraped.get("hero_image") else "Editorial Archive",
                "image_credit_url": payload.source_url,
                "published_at": datetime.now(timezone.utc),
            }
            created = await create_article_service(session=session, payload=article_payload)
            if created and created.get("id"):
                article_id = created["id"]
                try:
                    await transition_article_state_service(
                        session=session,
                        article_id=article_id,
                        target_status="published",
                        actor_sub=principal.sub if principal else "editorial_agent",
                        notes="Published via deep wire scraping & rich media pipeline.",
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("Database article persistence warning: %s", exc)

    # 7. Push to configured blog endpoint
    if settings.BLOG_ENDPOINT and settings.BLOG_SIGNING_SECRET:
        try:
            blog_payload = {
                "title": payload.headline,
                "slug": clean_slug,
                "content": body_md,
                "excerpt": excerpt,
                "category": payload.category or "technology",
                "status": "published",
                "image": {
                    "url": hero_img,
                    "alt": payload.headline,
                    "credit": "Original Wire Press Photo" if scraped.get("hero_image") else "Editorial Archive",
                    "credit_url": payload.source_url,
                    "license": "Editorial Press Rights",
                },
                "sources": [
                    {
                        "title": "Primary Wire Reporting",
                        "url": payload.source_url,
                    }
                ],
            }
            await push_article(
                settings.BLOG_ENDPOINT,
                settings.BLOG_SIGNING_SECRET,
                blog_payload,
                idempotency_key=f"scrape-article-{article_id}",
            )
        except Exception as b_err:
            logger.info("Direct blog push note: %s", b_err)

    return ScrapeAndPublishResponse(
        ok=True,
        article_id=article_id,
        title=payload.headline,
        headline=payload.headline,
        slug=clean_slug,
        category=payload.category or "technology",
        body_markdown=body_md,
        word_count=word_count,
        image_url=hero_img,
        images=scraped.get("images", []),
        youtube_ids=scraped.get("youtube_ids", []),
        primary_source_url=payload.source_url,
        status="published",
        error=scraped.get("error"),
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
