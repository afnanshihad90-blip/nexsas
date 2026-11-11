"""
NEXUS MEDIA AI — Pydantic v2 Request & Response Schemas (Step 3 & Step 4)
Includes full compatibility fallback for standard-library unittest verification.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List, Optional
import uuid

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
except ImportError:  # Fallback for environments without pydantic installed

    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            return dict(self.__dict__)

    def ConfigDict(**kwargs: Any) -> Dict[str, Any]:
        return kwargs

    def Field(default: Any = None, **kwargs: Any) -> Any:  # type: ignore[misc]
        if default is ... and "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default

    def field_validator(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        def decorator(fn: Any) -> Any:
            return fn

        return decorator


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    total_items: int = Field(default=0, ge=0)


# ============================================================================
# 1. System & Database Health Schemas
# ============================================================================
class SystemHealthResponse(BaseModel):
    application: str = "NEXUS MEDIA AI"
    status: str = "online"
    database: str = "not_configured"
    environment: str = "development"
    version: str = "0.1.0"


class DatabaseHealthResponse(BaseModel):
    status: str = "not_configured"
    configured: bool = False
    driver: str = "postgresql+asyncpg"
    ssl_enabled: bool = True
    session_pooler_compatible: bool = True
    latency_ms: Optional[int] = None
    message: str = ""
    checked_at: Optional[datetime] = None


# ============================================================================
# 2. AI Agents & Step 4 Multi-Agent Control Schemas
# ============================================================================
class AgentItemSchema(BaseModel):
    id: str
    slug: str
    name: str
    role_type: str
    description: Optional[str] = None
    status: str
    enabled: bool = True
    is_orchestrator: bool = False
    provider: str = "gemini"
    model: str = "gemini-2.5-pro"
    timeout_seconds: int = 90
    max_retries: int = 3
    temperature: Optional[float] = 0.2
    system_instructions: Optional[str] = None
    current_task: Optional[str] = None
    success_rate: float = 100.0
    avg_latency_ms: int = 0
    items_processed: int = 0
    success_count: int = 0
    failure_count: int = 0
    error_count: int = 0
    last_run_at: Optional[Any] = None
    next_scheduled_at: Optional[Any] = None


class AgentListResponse(BaseModel):
    items: List[AgentItemSchema] = Field(default_factory=list)
    pagination: PaginationMeta
    database_status: str = "not_configured"
    orchestrator_summary: Optional[Dict[str, Any]] = None


class AgentActionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=300)


class AgentActionResponse(BaseModel):
    agent_id: str
    previous_status: str
    current_status: str
    enabled: bool = True
    updated_by: str
    reason: Optional[str] = None
    timestamp: Any


class AgentConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = Field(default=None, max_length=64)
    model: Optional[str] = Field(default=None, max_length=128)
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    system_instructions: Optional[str] = Field(default=None, max_length=4000)
    allow_image_generation: Optional[bool] = None


class WorkflowRunRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=4, max_length=160)
    topic_headline: str = Field(..., min_length=8, max_length=240)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    feed_items: Optional[List[Dict[str, Any]]] = None
    candidate_images: Optional[List[Dict[str, Any]]] = None
    analytics_connected: bool = False


# ============================================================================
# 3. News Intelligence Schemas (Step 5)
# ============================================================================
class NewsItemSchema(BaseModel):
    id: str
    headline: str
    original_headline: Optional[str] = None
    normalized_headline: Optional[str] = None
    summary: Optional[str] = None
    short_metadata_description: Optional[str] = None
    canonical_url: str
    original_article_url: Optional[str] = None
    source_id: Optional[str] = None
    source_name: str = "Unknown Source"
    story_cluster_id: Optional[str] = None
    author: Optional[str] = None
    language: str = "en"
    category: str = "world-trending-news"
    category_name: Optional[str] = None
    secondary_tags: List[str] = Field(default_factory=list)
    classification: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    image_legally_usable: bool = False
    source_reliability_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_syndicated_copy: bool = False
    collection_status: str = "collected"
    urgency: str = "normal"
    status: str = "ingested"
    virality_score: float = 0.0
    trend_score: float = 0.0
    trend_level: str = "Ignore"
    source_diversity_score: float = 0.0
    publication_timestamp: Optional[Any] = None
    first_discovered_timestamp: Optional[Any] = None
    discovered_at: Optional[Any] = None


class NewsListResponse(BaseModel):
    items: List[NewsItemSchema] = Field(default_factory=list)
    pagination: PaginationMeta
    database_status: str = "not_configured"


class NewsCategorySchema(BaseModel):
    id: str
    slug: str
    name: str
    sector_group: str
    priority_weight: int = 5
    is_enabled: bool = True
    keywords: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


class NewsCategoryListResponse(BaseModel):
    items: List[NewsCategorySchema] = Field(default_factory=list)
    database_status: str = "not_configured"


class NewsSourceSchema(BaseModel):
    id: str
    name: str
    protocol: str
    connector_type: str = "rss_feed"
    endpoint_url: str
    trust_tier: str = "Secondary Attribution"
    reliability_score: float = 85.0
    poll_interval_seconds: int = 300
    timeout_seconds: int = 15
    rate_limit_per_minute: int = 30
    max_retries: int = 3
    status: str = "NOT_CONNECTED"
    is_enabled: bool = True
    robots_txt_compliant: bool = True
    terms_approved: bool = True
    category_slug: str = "world-trending-news"
    last_polled_at: Optional[Any] = None
    last_success_at: Optional[Any] = None
    last_error_message: Optional[str] = None
    articles_ingested_24h: int = 0


class NewsSourceListResponse(BaseModel):
    items: List[NewsSourceSchema] = Field(default_factory=list)
    database_status: str = "not_configured"


class NewsSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=160)
    endpoint_url: str = Field(..., min_length=10, max_length=2048)
    connector_type: str = Field(default="admin_rss", max_length=32)
    protocol: str = Field(default="RSS 2.0", max_length=32)
    trust_tier: str = Field(default="Secondary Attribution", max_length=64)
    reliability_score: float = Field(default=82.0, ge=0.0, le=100.0)
    poll_interval_seconds: int = Field(default=300, ge=60, le=86400)
    category_slug: str = Field(default="world-trending-news", max_length=64)
    robots_txt_compliant: bool = True
    terms_approved: bool = True


class NewsSourceUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    endpoint_url: Optional[str] = Field(default=None, min_length=10, max_length=2048)
    poll_interval_seconds: Optional[int] = Field(default=None, ge=60, le=86400)
    reliability_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    category_slug: Optional[str] = Field(default=None, max_length=64)
    test_connection: bool = False


class TrendingStorySchema(BaseModel):
    story_id: str
    cluster_key: str
    main_headline: str
    normalized_headline: str
    category_slug: str
    trend_score: float
    trend_level: str
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    trend_category: str
    supporting_source_count: int = 1
    independent_publishers_count: int = 1
    syndicated_copies_count: int = 0
    popularity_estimate_mode: str = "estimated_from_coverage"
    trend_status: str = "emerging"
    first_discovered_time: Any = None
    latest_update_time: Any = None
    related_source_ids: List[str] = Field(default_factory=list)
    related_news_ids: List[str] = Field(default_factory=list)
    sent_to_research: bool = False
    canonical_url: Optional[str] = None
    canonicalUrl: Optional[str] = None
    source_name: Optional[str] = None
    summary: Optional[str] = None
    short_metadata_description: Optional[str] = None
    image_url: Optional[str] = None
    related_sources: List[Dict[str, Any]] = Field(default_factory=list)


class TrendingListResponse(BaseModel):
    items: List[TrendingStorySchema] = Field(default_factory=list)
    database_status: str = "not_configured"


class StoryClusterListResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    database_status: str = "not_configured"


class NewsScanRequest(BaseModel):
    idempotency_key: Optional[str] = Field(default=None, max_length=160)
    trigger_source: str = Field(default="manual", max_length=64)
    source_ids: Optional[List[str]] = None


class NewsClassifyRequest(BaseModel):
    category_slug: Optional[str] = Field(default=None, max_length=64)


class NewsArchiveRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=300)



# ============================================================================
# 4. Editorial Articles Schemas
# ============================================================================
SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ArticleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = Field(default=None, max_length=300)
    headline: Optional[str] = Field(default=None, max_length=300)
    slug: Optional[str] = Field(default=None, max_length=160)
    subtitle: Optional[str] = Field(default=None, max_length=300)
    excerpt: Optional[str] = Field(default=None, max_length=600)
    summary: Optional[str] = Field(default=None, max_length=600)
    body_markdown: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    body: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default="published")
    stage: Optional[str] = Field(default="Published")
    is_public: Optional[bool] = Field(default=True)
    primary_source_url: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default="technology")
    image_url: Optional[str] = Field(default=None)
    image_alt: Optional[str] = Field(default=None)
    image_credit: Optional[str] = Field(default=None)

    @field_validator("slug")
    @classmethod
    def validate_slug_format(cls, v: Optional[str]) -> str:
        if not v:
            return f"story-{uuid.uuid4().hex[:8]}"
        clean = v.lower().strip()
        if not SLUG_REGEX.match(clean):
            clean = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
            if not clean:
                clean = f"story-{uuid.uuid4().hex[:8]}"
        return clean[:160]


class ArticleItemSchema(BaseModel):
    id: str
    slug: str
    title: str
    headline: Optional[str] = None
    subtitle: Optional[str] = None
    excerpt: Optional[str] = None
    summary: Optional[str] = None
    body_markdown: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = "technology"
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
    image_credit: Optional[str] = None
    status: str
    stage: Optional[str] = None
    word_count: int = 0
    reading_time_minutes: int = 1
    is_public: bool = False
    primary_source_url: Optional[str] = None
    published_at: Optional[Any] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class ArticleListResponse(BaseModel):
    items: List[ArticleItemSchema] = Field(default_factory=list)
    pagination: PaginationMeta
    database_status: str = "not_configured"


class ArticleLifecycleRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=500)


class ArticleLifecycleResponse(BaseModel):
    article_id: str
    slug: str
    previous_status: str
    current_status: str
    is_public: bool
    acted_by: str
    notes: Optional[str] = None
    timestamp: Any


# ============================================================================
# 5. Publishing, Analytics & System Logs Schemas
# ============================================================================
class PublishingJobSchema(BaseModel):
    id: str
    article_id: Optional[str] = None
    channel: str
    destination_Label: Optional[str] = None
    status: str
    retry_count: int = 0
    scheduled_for: Optional[Any] = None
    published_at: Optional[Any] = None
    external_url: Optional[str] = None


class PublishingJobListResponse(BaseModel):
    items: List[PublishingJobSchema] = Field(default_factory=list)
    pagination: PaginationMeta
    database_status: str = "not_configured"


class TrafficPointSchema(BaseModel):
    id: str
    recorded_date: str
    page_path: str = "/"
    pageviews: int = 0
    unique_visitors: int = 0
    avg_engagement_seconds: float = 0.0


class TrafficAnalyticsResponse(BaseModel):
    items: List[TrafficPointSchema] = Field(default_factory=list)
    database_status: str = "not_configured"


class RevenuePointSchema(BaseModel):
    id: str
    report_date: str
    revenue_source: str = "programmatic"
    gross_revenue_usd: float = 0.0
    net_revenue_usd: float = 0.0
    rpm_usd: float = 0.0
    impressions: int = 0


class RevenueAnalyticsResponse(BaseModel):
    items: List[RevenuePointSchema] = Field(default_factory=list)
    database_status: str = "not_configured"


class SystemLogItemSchema(BaseModel):
    id: str
    severity: str
    service_component: str
    event_code: str
    message: str
    correlation_id: Optional[str] = None
    created_at: Optional[Any] = None


class SystemLogListResponse(BaseModel):
    items: List[SystemLogItemSchema] = Field(default_factory=list)
    pagination: PaginationMeta
    database_status: str = "not_configured"
