"""SQLAlchemy 2.x declarative models mapped to the Step 2 & Step 4 Supabase PostgreSQL schema."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID
import uuid

try:
    from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, func
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class Base(DeclarativeBase):
        pass

    class AgentModel(Base):
        __tablename__ = "agents"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        role_title: Mapped[str] = mapped_column(String, nullable=False)
        description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        status: Mapped[str] = mapped_column(String, default="Idle", nullable=False)
        is_orchestrator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        current_task_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        processed_today_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        sla_score_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=100.0, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class AgentConfigModel(Base):
        __tablename__ = "agent_configs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, nullable=False)
        provider_name: Mapped[str] = mapped_column(String, default="unconfigured", nullable=False)
        model_identifier: Mapped[str] = mapped_column(String, default="gemini-2.5-pro", nullable=False)
        temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.20, nullable=False)
        max_concurrency: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
        max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
        timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
        system_directive: Mapped[str] = mapped_column(Text, nullable=False)
        safety_thresholds: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        allow_image_generation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        updated_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class WorkflowRunModel(Base):
        __tablename__ = "workflow_runs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        orchestrator_agent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        topic_headline: Mapped[str] = mapped_column(Text, nullable=False)
        current_stage: Mapped[str] = mapped_column(String, default="trend_discovery", nullable=False)
        status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
        stage_results: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        failure_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        initiated_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class AgentTaskModel(Base):
        __tablename__ = "agent_tasks"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
        workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        idempotency_key: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
        task_type: Mapped[str] = mapped_column(String, nullable=False)
        priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
        status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
        input_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        output_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
        error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
        timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
        dead_letter_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class AgentActivityModel(Base):
        __tablename__ = "agent_activity"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
        task_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        event_type: Mapped[str] = mapped_column(String, nullable=False)
        title: Mapped[str] = mapped_column(Text, nullable=False)
        summary: Mapped[str] = mapped_column(Text, nullable=False)
        severity: Mapped[str] = mapped_column(String, default="normal", nullable=False)
        metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class AgentExecutionLogModel(Base):
        __tablename__ = "agent_execution_logs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        task_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
        agent_slug: Mapped[str] = mapped_column(String, nullable=False)
        stage_name: Mapped[str] = mapped_column(String, nullable=False)
        attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
        status: Mapped[str] = mapped_column(String, nullable=False)
        input_envelope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        output_envelope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        execution_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class NewsCategoryModel(Base):
        __tablename__ = "news_categories"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        is_public_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        topics: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        regions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class NewsSourceModel(Base):
        __tablename__ = "news_sources"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        protocol: Mapped[str] = mapped_column(String, nullable=False)
        connector_type: Mapped[str] = mapped_column(String, default="rss_feed", nullable=False)
        endpoint_url: Mapped[str] = mapped_column("feed_url", Text, nullable=False)
        trust_tier: Mapped[str] = mapped_column(String, default="Tier 2 Verified", nullable=False)
        reliability_score: Mapped[float] = mapped_column(Numeric(5, 2), default=85.0, nullable=False)
        poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
        timeout_seconds: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
        rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
        max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
        status: Mapped[str] = mapped_column(String, default="Not Configured", nullable=False)
        is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        terms_approved: Mapped[bool] = mapped_column("terms_compliant", Boolean, default=True, nullable=False)
        last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        last_success_at: Mapped[Optional[datetime]] = mapped_column("last_successful_fetch_at", DateTime(timezone=True), nullable=True)
        last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        articles_ingested_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class StoryClusterModel(Base):
        __tablename__ = "story_clusters"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        story_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        cluster_key: Mapped[str] = mapped_column("canonical_slug", String, unique=True, nullable=False)
        main_headline: Mapped[str] = mapped_column(Text, nullable=False)
        category_slug: Mapped[str] = mapped_column("primary_category", String, default="World Trending News", nullable=False)
        secondary_tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        related_source_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        independent_publishers_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
        syndicated_copies_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        cluster_status: Mapped[str] = mapped_column("status", String, default="active", nullable=False)
        first_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        latest_update_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class NewsItemModel(Base):
        __tablename__ = "news_items"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        source_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
        category_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        story_cluster_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        external_guid: Mapped[str] = mapped_column(String, nullable=False)
        source_url: Mapped[str] = mapped_column(Text, nullable=False)
        canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        source_name: Mapped[str] = mapped_column(String, default="Unknown Source", nullable=False)
        headline: Mapped[str] = mapped_column(Text, nullable=False)
        normalized_headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        raw_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        short_metadata_description: Mapped[Optional[str]] = mapped_column("short_description", Text, nullable=True)
        author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        language: Mapped[str] = mapped_column(String, default="en", nullable=False)
        category_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        image_legally_usable: Mapped[bool] = mapped_column("image_license_verified", Boolean, default=False, nullable=False)
        source_reliability_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        is_syndicated_copy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        collection_status: Mapped[str] = mapped_column(String, default="collected", nullable=False)
        status: Mapped[str] = mapped_column(String, default="ingested", nullable=False)
        published_at: Mapped[Optional[datetime]] = mapped_column("published_by_source_at", DateTime(timezone=True), nullable=True)
        first_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class TrendScoreModel(Base):
        __tablename__ = "trend_scores"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        story_cluster_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, nullable=False)
        trend_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
        trend_level: Mapped[str] = mapped_column(String, default="Ignore", nullable=False)
        score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
        trend_category: Mapped[str] = mapped_column(String, nullable=False)
        supporting_source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
        popularity_estimate_mode: Mapped[str] = mapped_column("popularity_measurement_status", String, default="estimated_from_coverage", nullable=False)
        trend_status: Mapped[str] = mapped_column(String, default="emerging", nullable=False)
        first_seen: Mapped[datetime] = mapped_column("first_seen_at", DateTime(timezone=True), server_default=func.now())
        last_updated: Mapped[datetime] = mapped_column("last_updated_at", DateTime(timezone=True), server_default=func.now())
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class NewsClassificationModel(Base):
        __tablename__ = "news_classifications"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        news_item_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        story_cluster_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        primary_category_slug: Mapped[str] = mapped_column("primary_category", String, nullable=False)
        secondary_tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        classification_method: Mapped[str] = mapped_column(String, default="rule_based", nullable=False)
        confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=80.0, nullable=False)
        reasoning: Mapped[str] = mapped_column(Text, nullable=False)
        needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class CollectionRunModel(Base):
        __tablename__ = "collection_runs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        run_key: Mapped[str] = mapped_column("idempotency_key", String, unique=True, nullable=False)
        trigger_source: Mapped[str] = mapped_column(String, default="manual_operator", nullable=False)
        status: Mapped[str] = mapped_column(String, default="running", nullable=False)
        scan_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
        total_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        new_stories_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        duplicate_stories_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        failed_sources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        error_summary: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
        started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        next_scheduled_at: Mapped[Optional[datetime]] = mapped_column("next_scheduled_scan_at", DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class SourceFetchLogModel(Base):
        __tablename__ = "source_fetch_logs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        collection_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        source_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        source_name: Mapped[str] = mapped_column(String, default="Unknown", nullable=False)
        connector_type: Mapped[str] = mapped_column(String, nullable=False)
        status: Mapped[str] = mapped_column(String, default="success", nullable=False)
        items_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        retry_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        error_message: Mapped[Optional[str]] = mapped_column("error_detail", Text, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class ArticleModel(Base):
        __tablename__ = "articles"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        article_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        headline: Mapped[str] = mapped_column(Text, nullable=False)
        summary: Mapped[str] = mapped_column(Text, nullable=False)
        body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
        stage: Mapped[str] = mapped_column(String, default="Drafts", nullable=False)
        is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        fact_check_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        seo_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        primary_source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class PublishingJobModel(Base):
        __tablename__ = "publishing_jobs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        article_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
        target_channel: Mapped[str] = mapped_column(String, nullable=False)
        stage: Mapped[str] = mapped_column(String, default="Scheduled", nullable=False)
        scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class WebsiteTrafficModel(Base):
        __tablename__ = "website_traffic"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
        page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        unique_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        avg_read_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        referral_source: Mapped[str] = mapped_column(String, default="direct", nullable=False)

    class RevenueReportModel(Base):
        __tablename__ = "revenue_reports"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        report_date: Mapped[date] = mapped_column(Date, nullable=False)
        impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        effective_rpm_usd: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0, nullable=False)
        gross_revenue_usd: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)

    class SystemLogModel(Base):
        __tablename__ = "system_logs"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        subsystem: Mapped[str] = mapped_column(String, nullable=False)
        severity: Mapped[str] = mapped_column(String, default="info", nullable=False)
        message: Mapped[str] = mapped_column(Text, nullable=False)
        trace_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class SystemSettingModel(Base):
        __tablename__ = "system_settings"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        setting_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        setting_value: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
        description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        updated_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

except ImportError:  # pragma: no cover

    class Base:  # type: ignore
        metadata = None
