"""
NEXUS MEDIA AI — Async Operations & Repository Service Layer
Executes parameterized SQLAlchemy 2.x queries when Supabase PostgreSQL is connected,
and handles unconfigured/unavailable database states gracefully without crashing.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import probe_database_connection
from app.models.entities import (
    AgentModel,
    ArticleModel,
    NewsItemModel,
    PublishingJobModel,
    RevenueReportModel,
    SystemLogModel,
    SystemSettingModel,
    WebsiteTrafficModel,
)


class DatabaseUnavailableError(RuntimeError):
    """Raised when a mutating operation is attempted while Supabase is not connected."""

    def __init__(self, message: str = "Database is not configured or reachable for write operations.") -> None:
        super().__init__(message)
        self.message = message


async def resolve_db_status() -> str:
    """Return current database connection state ('connected', 'not_configured', or 'unreachable')."""
    health = await probe_database_connection()
    return str(health.get("status", "not_configured"))


async def list_agents_service(
    session: Optional[AsyncSession],
    offset: int = 0,
    limit: int = 25,
    status_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, str]:
    if session is None:
        return [], 0, await resolve_db_status()

    try:
        stmt = select(AgentModel).order_by(AgentModel.name.asc()).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(AgentModel)
        if status_filter:
            stmt = stmt.where(AgentModel.status == status_filter)
            count_stmt = count_stmt.where(AgentModel.status == status_filter)

        result = await session.execute(stmt)
        total = int((await session.execute(count_stmt)).scalar_one() or 0)
        rows = result.scalars().all()
        items = [
            {
                "id": str(r.id),
                "slug": r.slug,
                "name": r.name,
                "role_type": r.role_title,
                "description": r.description,
                "status": r.status,
                "enabled": bool(r.is_enabled),
                "is_orchestrator": bool(r.is_orchestrator),
                "current_task": r.current_task_summary,
                "success_rate": float(r.sla_score_pct or 100.0),
                "avg_latency_ms": 0,
                "items_processed": int(r.processed_today_count or 0),
                "success_count": int(r.success_count or 0),
                "failure_count": int(r.failure_count or 0),
                "error_count": int(r.failure_count or 0),
                "last_run_at": r.last_active_at,
                "next_scheduled_at": None,
            }
            for r in rows
        ]
        return items, total, "connected"
    except Exception:
        return [], 0, "unreachable"


async def get_agent_by_id_service(
    session: Optional[AsyncSession],
    agent_id: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    if session is None:
        return None, await resolve_db_status()

    try:
        stmt = select(AgentModel).where((AgentModel.id == agent_id) | (AgentModel.slug == agent_id))
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None, "connected"
        return (
            {
                "id": str(row.id),
                "slug": row.slug,
                "name": row.name,
                "role_type": row.role_title,
                "description": row.description,
                "status": row.status,
                "enabled": bool(row.is_enabled),
                "is_orchestrator": bool(row.is_orchestrator),
                "current_task": row.current_task_summary,
                "success_rate": float(row.sla_score_pct or 100.0),
                "avg_latency_ms": 0,
                "items_processed": int(row.processed_today_count or 0),
                "success_count": int(row.success_count or 0),
                "failure_count": int(row.failure_count or 0),
                "error_count": int(row.failure_count or 0),
                "last_run_at": row.last_active_at,
                "next_scheduled_at": None,
            },
            "connected",
        )
    except Exception:
        return None, "unreachable"


async def set_agent_Lifecycle_state_service(
    session: Optional[AsyncSession],
    agent_id: str,
    target_status: str,
    actor_sub: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    if session is None:
        raise DatabaseUnavailableError(
            f"Cannot transition agent '{agent_id}' to '{target_status}' because Supabase PostgreSQL is not configured."
        )

    stmt = select(AgentModel).where((AgentModel.id == agent_id) | (AgentModel.slug == agent_id))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise KeyError(f"Agent '{agent_id}' not found.")

    previous_status = row.status
    row.status = target_status
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()

    return {
        "agent_id": str(row.id),
        "previous_status": previous_status,
        "current_status": target_status,
        "updated_by": actor_sub,
        "reason": reason,
        "timestamp": row.updated_at,
    }


async def list_news_service(
    session: Optional[AsyncSession],
    offset: int = 0,
    limit: int = 25,
    status_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, str]:
    if session is None:
        return [], 0, await resolve_db_status()

    try:
        stmt = select(NewsItemModel).order_by(NewsItemModel.first_discovered_at.desc()).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(NewsItemModel)
        if status_filter:
            stmt = stmt.where(NewsItemModel.status == status_filter)
            count_stmt = count_stmt.where(NewsItemModel.status == status_filter)

        rows = (await session.execute(stmt)).scalars().all()
        total = int((await session.execute(count_stmt)).scalar_one() or 0)
        items = [
            {
                "id": str(r.id),
                "headline": r.headline,
                "summary": r.raw_summary or r.short_metadata_description or "",
                "canonical_url": r.canonical_url or r.source_url or "",
                "urgency": "normal",
                "status": r.status,
                "virality_score": 0.0,
                "source_diversity_score": 0.0,
                "discovered_at": r.first_discovered_at,
            }
            for r in rows
        ]
        return items, total, "connected"
    except Exception:
        return [], 0, "unreachable"


async def get_news_by_id_service(
    session: Optional[AsyncSession],
    news_id: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    if session is None:
        return None, await resolve_db_status()

    try:
        cond = NewsItemModel.external_guid == news_id
        try:
            from uuid import UUID as _UUID
            cond = cond | (NewsItemModel.id == _UUID(news_id))
        except ValueError:
            pass
        stmt = select(NewsItemModel).where(cond)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None, "connected"
        return (
            {
                "id": str(row.id),
                "headline": row.headline,
                "summary": row.raw_summary or row.short_metadata_description or "",
                "canonical_url": row.canonical_url or row.source_url or "",
                "urgency": "normal",
                "status": row.status,
                "virality_score": 0.0,
                "source_diversity_score": 0.0,
                "discovered_at": row.first_discovered_at,
            },
            "connected",
        )
    except Exception:
        return None, "unreachable"


STAGE_TO_STATUS = {
    "Drafts": "draft", "Awaiting Approval": "awaiting_approval",
    "Scheduled": "approved", "Published": "published", "Failed": "failed",
}
STATUS_TO_STAGE = {
    "draft": "Drafts", "awaiting_approval": "Awaiting Approval",
    "approved": "Scheduled", "published": "Published", "failed": "Failed",
}


def _article_to_dict(r: Any) -> Dict[str, Any]:
    """Map the real `articles` columns (headline/summary/stage) to the API schema."""
    words = int(r.word_count or 0)
    body = getattr(r, "body_markdown", None) or ""

    # Extract image from markdown if present
    img_match = re.search(r'!\[(.*?)\]\((https?://[^\s\)]+)\)', body)
    img_url = img_match.group(2) if img_match else None
    img_alt = img_match.group(1) if img_match else None

    # Derive accurate category based on text content
    from app.api.blog import guess_category
    category = guess_category(f"{r.headline} {r.summary} {body[:300]}")

    if not img_url:
        fallbacks = {
            "science": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80",
            "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&auto=format&fit=crop&q=80",
            "business": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&auto=format&fit=crop&q=80",
            "world": "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1200&auto=format&fit=crop&q=80",
        }
        img_url = fallbacks.get(category, fallbacks["technology"])
        img_alt = r.headline

    return {
        "id": str(r.id),
        "slug": r.slug,
        "title": r.headline,
        "headline": r.headline,
        "subtitle": None,
        "excerpt": r.summary,
        "summary": r.summary,
        "body_markdown": body,
        "content": body,
        "category": category,
        "image_url": img_url,
        "image_alt": img_alt,
        "image_credit": "Original Wire Press Photo (Editorial)",
        "status": STAGE_TO_STATUS.get(r.stage, str(r.stage).lower()),
        "stage": r.stage,
        "word_count": words,
        "reading_time_minutes": max(1, round(words / 220)),
        "is_public": bool(r.is_public),
        "primary_source_url": getattr(r, "primary_source_url", None),
        "published_at": r.published_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


async def list_articles_service(
    session: Optional[AsyncSession],
    offset: int = 0,
    limit: int = 25,
    status_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, str]:
    if session is None:
        return [], 0, await resolve_db_status()
    try:
        stmt = select(ArticleModel).order_by(ArticleModel.updated_at.desc()).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(ArticleModel)
        if status_filter:
            stage = STATUS_TO_STAGE.get(status_filter, status_filter)
            stmt = stmt.where(ArticleModel.stage == stage)
            count_stmt = count_stmt.where(ArticleModel.stage == stage)
        rows = (await session.execute(stmt)).scalars().all()
        total = int((await session.execute(count_stmt)).scalar_one() or 0)
        return [_article_to_dict(r) for r in rows], total, "connected"
    except Exception:
        return [], 0, "unreachable"


async def get_article_by_id_service(
    session: Optional[AsyncSession],
    article_id: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    if session is None:
        return None, await resolve_db_status()
    try:
        cond = ArticleModel.slug == article_id
        try:
            from uuid import UUID as _UUID
            cond = cond | (ArticleModel.id == _UUID(article_id))
        except ValueError:
            pass
        row = (await session.execute(select(ArticleModel).where(cond))).scalar_one_or_none()
        if row is None:
            return None, "connected"
        return _article_to_dict(row), "connected"
    except Exception:
        return None, "unreachable"


async def get_article_full_service(session: AsyncSession, article_id: str) -> Optional[Any]:
    """Return the raw ArticleModel row (id or slug) for publishing."""
    cond = ArticleModel.slug == article_id
    try:
        from uuid import UUID as _UUID
        cond = cond | (ArticleModel.id == _UUID(article_id))
    except ValueError:
        pass
    return (await session.execute(select(ArticleModel).where(cond))).scalar_one_or_none()


async def create_article_service(
    session: Optional[AsyncSession],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    if session is None:
        raise DatabaseUnavailableError(
            "Cannot persist new article because Supabase PostgreSQL is not configured."
        )
    import secrets, uuid
    headline = str(payload.get("title") or payload.get("headline") or "Untitled Story").strip()
    raw_slug = str(payload.get("slug") or "").strip()
    if not raw_slug:
        raw_slug = re.sub(r"[^a-z0-9]+", "-", headline.lower()).strip("-")
        if not raw_slug:
            raw_slug = f"story-{secrets.token_hex(4)}"

    body = str(payload.get("body_markdown") or payload.get("content") or payload.get("body") or headline).strip()
    summary = str(payload.get("excerpt") or payload.get("summary") or body[:240]).strip()

    # Prepend image if supplied and not already in body
    img_data = payload.get("image")
    img_url = payload.get("image_url") or (img_data.get("url") if isinstance(img_data, dict) else None)
    if img_url and img_url not in body:
        img_alt = payload.get("image_alt") or headline
        body = f"![{img_alt}]({img_url})\n\n{body}"

    now = datetime.now(timezone.utc)
    status_str = str(payload.get("status", "")).lower()
    stage_str = str(payload.get("stage", ""))
    if stage_str.lower() == "published" or status_str == "published":
        stage = "Published"
        is_pub = True
    else:
        stage = stage_str or STATUS_TO_STAGE.get(status_str, "Drafts")
        is_pub = bool(payload.get("is_public", False) or (stage == "Published"))

    # Upsert by slug: if already exists, update safely without crashing on UNIQUE constraint
    existing = (await session.execute(select(ArticleModel).where(ArticleModel.slug == raw_slug))).scalar_one_or_none()
    if existing:
        existing.headline = headline
        existing.summary = summary
        existing.body_markdown = body
        existing.stage = stage
        existing.is_public = is_pub
        existing.word_count = len(body.split())
        existing.updated_at = now
        if is_pub and not existing.published_at:
            existing.published_at = now
        if payload.get("primary_source_url"):
            existing.primary_source_url = payload.get("primary_source_url")
        await session.commit()
        await session.refresh(existing)
        return _article_to_dict(existing)

    article = ArticleModel(
        id=uuid.uuid4(),
        article_code=f"NX-{secrets.token_hex(3).upper()}",
        slug=raw_slug,
        headline=headline,
        summary=summary,
        body_markdown=body,
        stage=stage,
        word_count=len(body.split()),
        is_public=is_pub,
        fact_check_score=int(payload.get("fact_check_score", 0)),
        seo_score=int(payload.get("seo_score", 0)),
        primary_source_url=payload.get("primary_source_url"),
        published_at=now if is_pub else payload.get("published_at"),
        created_at=now,
        updated_at=now,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return _article_to_dict(article)


async def transition_article_state_service(
    session: Optional[AsyncSession],
    article_id: str,
    target_status: str,
    actor_sub: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    if session is None:
        raise DatabaseUnavailableError(
            f"Cannot transition article '{article_id}' to '{target_status}' because Supabase PostgreSQL is not configured."
        )
    row = await get_article_full_service(session, article_id)
    if row is None:
        raise KeyError(f"Article '{article_id}' not found.")

    previous_status = STAGE_TO_STATUS.get(row.stage, str(row.stage).lower())
    now = datetime.now(timezone.utc)
    row.stage = STATUS_TO_STAGE.get(target_status, "Drafts")
    row.updated_at = now
    if target_status == "published":
        row.is_public = True
        row.published_at = now
    await session.commit()
    return {
        "article_id": str(row.id),
        "slug": row.slug,
        "previous_status": previous_status,
        "current_status": target_status,
        "is_public": bool(row.is_public),
        "acted_by": actor_sub,
        "notes": notes,
        "timestamp": now,
    }


async def list_publishing_jobs_service(
    session: Optional[AsyncSession],
    offset: int = 0,
    limit: int = 25,
) -> Tuple[List[Dict[str, Any]], int, str]:
    if session is None:
        return [], 0, await resolve_db_status()

    try:
        stmt = select(PublishingJobModel).order_by(PublishingJobModel.created_at.desc()).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(PublishingJobModel)
        rows = (await session.execute(stmt)).scalars().all()
        total = int((await session.execute(count_stmt)).scalar_one() or 0)
        items = [
            {
                "id": str(r.id),
                "article_id": str(r.article_id) if r.article_id else None,
                "channel": r.target_channel,
                "destination_Label": None,
                "status": STAGE_TO_STATUS.get(r.stage, str(r.stage).lower()),
                "retry_count": int(r.retry_count or 0),
                "scheduled_for": r.scheduled_at,
                "published_at": r.executed_at,
                "external_url": None,
            }
            for r in rows
        ]
        return items, total, "connected"
    except Exception:
        return [], 0, "unreachable"


async def list_traffic_analytics_service(
    session: Optional[AsyncSession],
    limit: int = 30,
) -> Tuple[List[Dict[str, Any]], str]:
    if session is None:
        return [], await resolve_db_status()

    try:
        stmt = select(WebsiteTrafficModel).order_by(WebsiteTrafficModel.recorded_date.desc()).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            {
                "id": str(r.id),
                "recorded_date": str(r.recorded_date),
                "page_path": r.referral_source or "/",
                "pageviews": int(r.page_views or 0),
                "unique_visitors": int(r.unique_visitors or 0),
                "avg_engagement_seconds": float(r.avg_read_time_seconds or 0.0),
            }
            for r in rows
        ]
        return items, "connected"
    except Exception:
        return [], "unreachable"


async def list_revenue_analytics_service(
    session: Optional[AsyncSession],
    limit: int = 30,
) -> Tuple[List[Dict[str, Any]], str]:
    if session is None:
        return [], await resolve_db_status()

    try:
        stmt = select(RevenueReportModel).order_by(RevenueReportModel.report_date.desc()).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            {
                "id": str(r.id),
                "report_date": str(r.report_date),
                "revenue_source": "AdSense",
                "gross_revenue_usd": float(r.gross_revenue_usd or 0.0),
                "net_revenue_usd": float(r.gross_revenue_usd or 0.0),
                "rpm_usd": float(r.effective_rpm_usd or 0.0),
                "impressions": int(r.impressions or 0),
            }
            for r in rows
        ]
        return items, "connected"
    except Exception:
        return [], "unreachable"


async def list_system_logs_service(
    session: Optional[AsyncSession],
    offset: int = 0,
    limit: int = 50,
    severity_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, str]:
    if session is None:
        return [], 0, await resolve_db_status()

    try:
        stmt = select(SystemLogModel).order_by(SystemLogModel.created_at.desc()).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(SystemLogModel)
        if severity_filter:
            stmt = stmt.where(SystemLogModel.severity == severity_filter)
            count_stmt = count_stmt.where(SystemLogModel.severity == severity_filter)

        rows = (await session.execute(stmt)).scalars().all()
        total = int((await session.execute(count_stmt)).scalar_one() or 0)
        items = [
            {
                "id": str(r.id),
                "severity": r.severity,
                "service_component": r.subsystem,
                "event_code": (r.trace_context or {}).get("event_code", "LOG_EVENT"),
                "message": r.message,
                "correlation_id": (r.trace_context or {}).get("correlation_id"),
                "created_at": r.created_at,
            }
            for r in rows
        ]
        return items, total, "connected"
    except Exception:
        return [], 0, "unreachable"


# In-memory kill switch fallback when database is unconfigured
_IN_MEMORY_KILL_SWITCH = False


async def get_kill_switch_service(session: Optional[AsyncSession]) -> bool:
    """Returns True if the global kill switch is engaged, False otherwise."""
    global _IN_MEMORY_KILL_SWITCH
    if session is None:
        return _IN_MEMORY_KILL_SWITCH

    try:
        stmt = select(SystemSettingModel).where(SystemSettingModel.setting_key == "kill_switch")
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is not None and isinstance(row.setting_value, dict):
            return bool(row.setting_value.get("enabled", False))
        return False
    except Exception:
        return _IN_MEMORY_KILL_SWITCH


async def set_kill_switch_service(
    session: Optional[AsyncSession],
    enabled: bool,
    actor_sub: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Sets the global emergency stop / kill switch flag."""
    global _IN_MEMORY_KILL_SWITCH
    _IN_MEMORY_KILL_SWITCH = enabled
    now = datetime.now(timezone.utc)

    if session is None:
        return {
            "kill_switch_enabled": enabled,
            "updated_by": actor_sub,
            "reason": reason,
            "timestamp": now,
            "source": "in_memory",
        }

    try:
        stmt = select(SystemSettingModel).where(SystemSettingModel.setting_key == "kill_switch")
        row = (await session.execute(stmt)).scalar_one_or_none()
        payload = {"enabled": enabled, "updated_by": actor_sub, "reason": reason}
        if row is None:
            import uuid
            row = SystemSettingModel(
                id=uuid.uuid4(),
                setting_key="kill_switch",
                setting_value=payload,
                description="Global emergency kill switch: stops all publishing and new agent tasks.",
                updated_at=now,
            )
            session.add(row)
        else:
            row.setting_value = payload
            row.updated_at = now
        await session.commit()
        return {
            "kill_switch_enabled": enabled,
            "updated_by": actor_sub,
            "reason": reason,
            "timestamp": now,
            "source": "database",
        }
    except Exception as exc:
        await session.rollback()
        return {
            "kill_switch_enabled": enabled,
            "updated_by": actor_sub,
            "reason": reason,
            "timestamp": now,
            "source": "in_memory_fallback",
        }
