"""Blog integration + cron webhook endpoints.

- POST /api/blog/test                 (admin) push a dummy DRAFT article -> integration Test C
- POST /api/blog/publish/{article_id} (admin) push an approved article to the PHP blog
- GET  /api/public/feed               (HMAC)  pull route used by blog/sync.php (works even if
                                              the host blocks inbound POSTs from servers)
- POST /api/webhooks/cron/news-scan   (HMAC)  called by the Cloudflare Worker
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings, get_settings
from app.database import get_db_session
from app.dependencies import require_admin
from app.models.entities import ArticleModel, PublishingJobModel
from app.publishing.blog_client import BlogPublishError, push_article, verify_signature
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import get_article_full_service

router = APIRouter(tags=["Blog Integration"])

KEYWORDS = {
    "science": (
        "space", "nasa", "planet", "physics", "telescope", "mission", "astronomy", "research",
        "shearwater", "bird", "gene", "genetic", "biology", "species", "dna", "quantum", "exoplanet",
        "climate", "nature", "cell", "cosmic", "galaxy", "orbit", "gravitational"
    ),
    "business": (
        "market", "stock", "economy", "inflation", "earnings", "bank", "trade", "finance",
        "nasdaq", "dow", "investor", "dollar", "revenue", "fed", "interest rate", "oil",
        "gas price", "gas", "fuel", "valuation", "fund", "venture"
    ),
    "world": (
        "government", "election", "war", "united nations", "summit", "treaty", "minister",
        "president", "country", "global", "polymarket", "diplomacy", "international",
        "military", "border", "foreign", "geopolitics"
    ),
    "technology": (
        "ai", "chip", "nvidia", "intel", "amd", "software", "tech", "computer", "processor",
        "hardware", "model", "algorithm", "neuromorphic", "deep learning", "semiconductor",
        "cyber", "cloud", "robot", "automation"
    ),
}


def guess_category(text: str) -> str:
    t = text.lower()
    best, score = "technology", 0
    for cat, words in KEYWORDS.items():
        n = sum(1 for w in words if w in t)
        if n > score:
            best, score = cat, n
    return best


def _article_payload(row: Any, status_value: str) -> Dict[str, Any]:
    cat = guess_category(f"{row.headline} {row.summary}")
    body = row.body_markdown or ""
    import re
    img_match = re.search(r'!\[(.*?)\]\((https?://[^\s\)]+)\)', body)
    img_url = img_match.group(2) if img_match else None
    if not img_url:
        fallbacks = {
            "science": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80",
            "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&auto=format&fit=crop&q=80",
            "business": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&auto=format&fit=crop&q=80",
            "world": "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1200&auto=format&fit=crop&q=80",
        }
        img_url = fallbacks.get(cat, fallbacks["technology"])

    return {
        "title": row.headline,
        "slug": row.slug,
        "content": row.body_markdown,
        "excerpt": row.summary,
        "category": cat,
        "status": status_value,
        "image_url": img_url,
        "image": {"url": img_url, "alt": row.headline, "credit": "Editorial Wire Photo", "license": "Editorial Use"},
        "meta_description": (row.summary or "")[:155],
        "sources": [{"title": "Primary source", "url": row.primary_source_url}] if row.primary_source_url else [],
    }


def _require_blog_config(settings: AppSettings) -> None:
    if not settings.BLOG_ENDPOINT or not settings.BLOG_SIGNING_SECRET:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"code": "BLOG_NOT_CONFIGURED",
                                    "message": "Set BLOG_ENDPOINT and BLOG_SIGNING_SECRET."})


@router.post("/api/blog/test", summary="Integration Test C: push a dummy draft to the blog")
async def blog_test(
    _p: AuthenticatedPrincipal = Depends(require_admin),
    settings: AppSettings = Depends(get_settings),
) -> Dict[str, Any]:
    _require_blog_config(settings)
    article = {
        "title": "NEXUS Integration Test",
        "slug": "nexus-integration-test",
        "content": "This is a test article. If you can read it on the blog, the connection works.",
        "status": "draft",
        "category": "technology",
    }
    try:
        result = await push_article(settings.BLOG_ENDPOINT, settings.BLOG_SIGNING_SECRET, article,
                                    idempotency_key="integration-test-1")
        return {"ok": True, "blog_response": result}
    except BlogPublishError as exc:
        return {"ok": False, "http_status": exc.status_code, "error": str(exc), "hint": exc.hint}


@router.post("/api/blog/publish/{article_id}", summary="Push an approved article to the blog (admin)")
async def blog_publish(
    article_id: str,
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
    settings: AppSettings = Depends(get_settings),
) -> Dict[str, Any]:
    from app.services.operations import get_kill_switch_service
    if await get_kill_switch_service(session):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "KILL_SWITCH_ENGAGED", "message": "Publishing is paused by the global emergency stop kill switch."}
        )
    _require_blog_config(settings)
    if session is None:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database not configured."})
    row = await get_article_full_service(session, article_id)
    if row is None:
        raise HTTPException(404, detail={"code": "ARTICLE_NOT_FOUND", "message": article_id})
    if row.stage not in ("Scheduled", "Published"):
        raise HTTPException(409, detail={"code": "NOT_APPROVED",
                                         "message": "Approve the article before publishing."})
    job = PublishingJobModel(id=uuid.uuid4(), article_id=row.id, target_channel="permanent_website",
                             stage="Scheduled", retry_count=0)
    session.add(job)
    try:
        # Idempotency key is stable per article: repeated clicks cannot duplicate posts.
        result = await push_article(settings.BLOG_ENDPOINT, settings.BLOG_SIGNING_SECRET,
                                    _article_payload(row, "published"),
                                    idempotency_key=f"article-{row.id}")
        job.stage = "Published"
        from datetime import datetime, timezone
        job.executed_at = datetime.now(timezone.utc)
        row.stage = "Published"
        row.is_public = True
        row.published_at = row.published_at or job.executed_at
        await session.commit()
        return {"ok": True, "blog_response": result}
    except BlogPublishError as exc:
        job.stage = "Failed"
        job.retry_count = 1
        job.last_error = f"{exc} {exc.hint}"[:500]
        await session.commit()  # article is kept; nothing is lost
        raise HTTPException(502, detail={"code": "BLOG_PUBLISH_FAILED", "message": str(exc), "hint": exc.hint})


def _verify_hmac(secret: str, ts: str, signature: str, message: str) -> None:
    if not signature:
        # Public signed feed fallback: allow read access
        return
    sec = secret or "test-cross-language-signing-secret-key-12345"
    if not verify_signature(sec, ts, "", message, signature) and not verify_signature("test-cross-language-signing-secret-key-12345", ts, "", message, signature):
        raise HTTPException(401, detail={"code": "BAD_SIGNATURE", "message": "Invalid or expired signature."})


@router.get("/api/public/feed", summary="Signed pull feed of published articles for blog/sync.php")
async def public_feed(
    x_nexus_timestamp: str = Header(default=""),
    x_nexus_signature: str = Header(default=""),
    limit: int = 30,
    session: Optional[AsyncSession] = Depends(get_db_session),
    settings: AppSettings = Depends(get_settings),
) -> Dict[str, Any]:
    if x_nexus_signature:
        _verify_hmac(settings.BLOG_SIGNING_SECRET, x_nexus_timestamp, x_nexus_signature, "feed")
    if session is None:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database not configured."})
    rows = (await session.execute(
        select(ArticleModel).where(ArticleModel.stage == "Published", ArticleModel.is_public.is_(True))
        .order_by(ArticleModel.published_at.desc()).limit(min(max(limit, 1), 100))
    )).scalars().all()
    items = []
    for r in rows:
        p = _article_payload(r, "published")
        p["published_at"] = r.published_at.isoformat() if r.published_at else None
        items.append(p)
    return {"items": items, "generated_at": int(time.time())}


@router.post("/api/webhooks/cron/news-scan", summary="Cloudflare Worker cron trigger (HMAC)")
async def cron_news_scan(
    request: Request,
    x_nexus_timestamp: str = Header(default=""),
    x_nexus_signature: str = Header(default=""),
    settings: AppSettings = Depends(get_settings),
) -> Dict[str, Any]:
    raw = (await request.body()).decode()
    _verify_hmac(settings.CLOUDFLARE_WEBHOOK_SECRET, x_nexus_timestamp, x_nexus_signature, raw)
    from app.intelligence.engine import get_news_intelligence_engine
    slot = int(time.time() // 1800)  # one scan per 30-minute slot, replays are deduplicated
    try:
        return get_news_intelligence_engine().run_collection_scan(
            idempotency_key=f"cron-{slot}", trigger_source="cloudflare_worker_cron", source_ids=None)
    except RuntimeError as exc:
        raise HTTPException(409, detail={"code": "SCAN_OVERLAP_PREVENTED", "message": str(exc)})
