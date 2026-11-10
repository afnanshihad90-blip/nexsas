-- ============================================================================
-- NEXUS MEDIA AI — STEP 2: SUPABASE POSTGRESQL FOUNDATION MIGRATION
-- Migration ID: 20261109000001_nexus_media_ai_foundation.sql
-- Purpose: Creates all 37 core relational tables across 10 operational domains,
--          foreign keys, indexes, updated_at triggers, and Row Level Security.
-- ============================================================================

BEGIN;

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Shared Trigger Function for updated_at
CREATE OR REPLACE FUNCTION public.trigger_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- ============================================================================
-- DOMAIN 1: USER MANAGEMENT (users, user_roles, user_sessions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id UUID UNIQUE, -- Maps to auth.users(id) when Supabase Auth is active
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  avatar_url TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'invited', 'archived')),
  last_sign_in_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role_name TEXT NOT NULL CHECK (role_name IN ('super_admin', 'managing_editor', 'fact_checker', 'operator', 'viewer')),
  permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
  assigned_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, role_name)
);

CREATE TABLE IF NOT EXISTS public.user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  session_token_hash TEXT NOT NULL UNIQUE,
  ip_address INET,
  user_agent TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 2: AI AGENT MANAGEMENT (agents, agent_configs, agent_activity, agent_tasks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  role_title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'Idle' CHECK (status IN ('Running', 'Idle', 'Paused', 'Standby', 'Error')),
  current_task_summary TEXT,
  last_active_at TIMESTAMPTZ,
  processed_today_count INTEGER NOT NULL DEFAULT 0,
  sla_score_pct NUMERIC(5,2) NOT NULL DEFAULT 100.00,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.agent_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL UNIQUE REFERENCES public.agents(id) ON DELETE CASCADE,
  model_identifier TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
  temperature NUMERIC(3,2) NOT NULL DEFAULT 0.20 CHECK (temperature >= 0.0 AND temperature <= 2.0),
  max_concurrency INTEGER NOT NULL DEFAULT 2 CHECK (max_concurrency >= 1 AND max_concurrency <= 32),
  timeout_seconds INTEGER NOT NULL DEFAULT 120,
  system_directive TEXT NOT NULL,
  safety_thresholds JSONB NOT NULL DEFAULT '{"min_fact_confidence": 95}'::jsonb,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.agent_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  task_type TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
  input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_payload JSONB,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.agent_activity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  task_id UUID REFERENCES public.agent_tasks(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'News discovered',
    'Research completed',
    'Fact-check completed',
    'Article drafted',
    'Article approved',
    'Publishing result',
    'System errors'
  )),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'normal' CHECK (severity IN ('normal', 'success', 'warning', 'error')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 3: NEWS INTELLIGENCE (news_categories, news_sources, trending_topics, news_items)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.news_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  is_public_approved BOOLEAN NOT NULL DEFAULT TRUE,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.news_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  feed_url TEXT NOT NULL UNIQUE,
  protocol TEXT NOT NULL CHECK (protocol IN ('RSS / Atom', 'Wire API', 'Regulatory Filing', 'Social Stream')),
  trust_tier TEXT NOT NULL CHECK (trust_tier IN ('Tier 1 Primary', 'Tier 2 Verified', 'Tier 3 Signal')),
  poll_interval_seconds INTEGER NOT NULL DEFAULT 300,
  status TEXT NOT NULL DEFAULT 'Not Configured' CHECK (status IN ('Connected', 'Disconnected', 'Checking', 'Error', 'Not Configured')),
  last_polled_at TIMESTAMPTZ,
  articles_ingested_24h INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.trending_topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID REFERENCES public.news_categories(id) ON DELETE SET NULL,
  assigned_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  topic_title TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  velocity_score INTEGER NOT NULL DEFAULT 50 CHECK (velocity_score >= 0 AND velocity_score <= 100),
  corroborating_sources_count INTEGER NOT NULL DEFAULT 1,
  verification_state TEXT NOT NULL DEFAULT 'Unverified Signal' CHECK (verification_state IN ('Verified', 'Cross-Checking', 'Unverified Signal')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'drafted', 'archived')),
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.news_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID NOT NULL REFERENCES public.news_sources(id) ON DELETE RESTRICT,
  category_id UUID REFERENCES public.news_categories(id) ON DELETE SET NULL,
  trending_topic_id UUID REFERENCES public.trending_topics(id) ON DELETE SET NULL,
  external_guid TEXT NOT NULL,
  source_url TEXT NOT NULL,
  headline TEXT NOT NULL,
  raw_summary TEXT,
  raw_content TEXT,
  published_by_source_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'ingested' CHECK (status IN ('ingested', 'researching', 'verified', 'discarded')),
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id, external_guid)
);

-- ============================================================================
-- DOMAIN 4: RESEARCH & VERIFICATION (research_sessions, research_sources, fact_checks, verified_claims)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.research_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trending_topic_id UUID REFERENCES public.trending_topics(id) ON DELETE SET NULL,
  lead_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  synthesis_notes TEXT,
  status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'halted')),
  confidence_score NUMERIC(5,2) DEFAULT 0.00,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.research_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  research_session_id UUID NOT NULL REFERENCES public.research_sessions(id) ON DELETE CASCADE,
  news_item_id UUID REFERENCES public.news_items(id) ON DELETE SET NULL,
  citation_title TEXT NOT NULL,
  citation_url TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'primary_filing' CHECK (source_type IN ('primary_filing', 'wire_dispatch', 'institutional_report', 'secondary_media')),
  excerpt TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.fact_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  research_session_id UUID NOT NULL REFERENCES public.research_sessions(id) ON DELETE CASCADE,
  auditor_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  reviewed_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  overall_score NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (overall_score >= 0 AND overall_score <= 100),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'passed', 'flagged', 'rejected')),
  audit_summary TEXT,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.verified_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fact_check_id UUID NOT NULL REFERENCES public.fact_checks(id) ON DELETE CASCADE,
  claim_text TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('Confirmed Primary Source', 'Needs Attribution', 'Disputed Numeric Claim', 'Rejected')),
  sources_checked_count INTEGER NOT NULL DEFAULT 1,
  confidence_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (confidence_pct >= 0 AND confidence_pct <= 100),
  primary_evidence_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 5: CONTENT MANAGEMENT (articles, article_versions, article_categories, article_tags, editorial_quality, seo_metadata)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_code TEXT NOT NULL UNIQUE, -- e.g. NX-4092
  slug TEXT NOT NULL UNIQUE,
  headline TEXT NOT NULL,
  subheadline TEXT,
  summary TEXT NOT NULL,
  body_markdown TEXT NOT NULL,
  primary_category_id UUID REFERENCES public.news_categories(id) ON DELETE SET NULL,
  research_session_id UUID REFERENCES public.research_sessions(id) ON DELETE SET NULL,
  author_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  approved_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  stage TEXT NOT NULL DEFAULT 'Drafts' CHECK (stage IN ('Drafts', 'Awaiting Approval', 'Scheduled', 'Published', 'Failed')),
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  word_count INTEGER NOT NULL DEFAULT 0,
  fact_check_score INTEGER NOT NULL DEFAULT 0 CHECK (fact_check_score >= 0 AND fact_check_score <= 100),
  seo_score INTEGER NOT NULL DEFAULT 0 CHECK (seo_score >= 0 AND seo_score <= 100),
  primary_source_url TEXT,
  scheduled_for TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.article_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  headline TEXT NOT NULL,
  body_markdown TEXT NOT NULL,
  change_reason TEXT,
  created_by_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  created_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (article_id, version_number)
);

CREATE TABLE IF NOT EXISTS public.article_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES public.news_categories(id) ON DELETE CASCADE,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (article_id, category_id)
);

CREATE TABLE IF NOT EXISTS public.article_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  tag_slug TEXT NOT NULL,
  tag_label TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (article_id, tag_slug)
);

CREATE TABLE IF NOT EXISTS public.editorial_quality (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL UNIQUE REFERENCES public.articles(id) ON DELETE CASCADE,
  readability_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
  neutrality_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
  citation_density_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
  originality_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
  reviewer_notes TEXT,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.seo_metadata (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL UNIQUE REFERENCES public.articles(id) ON DELETE CASCADE,
  meta_title TEXT NOT NULL,
  meta_description TEXT NOT NULL,
  canonical_url TEXT,
  focus_keywords TEXT[] NOT NULL DEFAULT '{}',
  schema_org_jsonld JSONB NOT NULL DEFAULT '{}'::jsonb,
  og_image_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 6: MEDIA MANAGEMENT (image_licenses, image_library, media_attributions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.image_licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  license_code TEXT NOT NULL UNIQUE,
  license_name TEXT NOT NULL,
  provider_name TEXT NOT NULL,
  usage_terms_url TEXT,
  allows_commercial BOOLEAN NOT NULL DEFAULT TRUE,
  requires_attribution BOOLEAN NOT NULL DEFAULT TRUE,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.image_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  license_id UUID REFERENCES public.image_licenses(id) ON DELETE SET NULL,
  created_by_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  storage_path TEXT NOT NULL UNIQUE,
  public_url TEXT NOT NULL,
  alt_text TEXT NOT NULL,
  aspect_ratio TEXT NOT NULL DEFAULT '16:9',
  width_px INTEGER,
  height_px INTEGER,
  status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('processing', 'approved', 'archived')),
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.media_attributions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  image_id UUID NOT NULL REFERENCES public.image_library(id) ON DELETE CASCADE,
  article_id UUID REFERENCES public.articles(id) ON DELETE CASCADE,
  credit_line TEXT NOT NULL,
  caption_text TEXT,
  placement_role TEXT NOT NULL DEFAULT 'hero' CHECK (placement_role IN ('hero', 'inline', 'thumbnail', 'social_card')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 7: PUBLISHING (social_accounts, publishing_jobs, social_posts, publishing_logs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.social_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL CHECK (platform IN ('X', 'LinkedIn', 'YouTube', 'Threads', 'Bluesky', 'Telegram')),
  handle TEXT NOT NULL,
  account_display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Disconnected' CHECK (status IN ('Connected', 'Disconnected', 'Checking', 'Error', 'Not Configured')),
  oauth_scopes TEXT[] NOT NULL DEFAULT '{}',
  token_expires_at TIMESTAMPTZ,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (platform, handle)
);

CREATE TABLE IF NOT EXISTS public.publishing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  dispatched_by_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  target_channel TEXT NOT NULL CHECK (target_channel IN ('permanent_website', 'social_syndication', 'youtube_briefing')),
  stage TEXT NOT NULL DEFAULT 'Scheduled' CHECK (stage IN ('Drafts', 'Awaiting Approval', 'Scheduled', 'Published', 'Failed')),
  scheduled_at TIMESTAMPTZ,
  executed_at TIMESTAMPTZ,
  retry_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.social_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  publishing_job_id UUID REFERENCES public.publishing_jobs(id) ON DELETE CASCADE,
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  social_account_id UUID NOT NULL REFERENCES public.social_accounts(id) ON DELETE RESTRICT,
  post_copy TEXT NOT NULL,
  media_url TEXT,
  external_post_id TEXT,
  status TEXT NOT NULL DEFAULT 'staged' CHECK (status IN ('staged', 'scheduled', 'published', 'failed')),
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.publishing_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  publishing_job_id UUID NOT NULL REFERENCES public.publishing_jobs(id) ON DELETE CASCADE,
  log_level TEXT NOT NULL DEFAULT 'info' CHECK (log_level IN ('info', 'warning', 'error')),
  message TEXT NOT NULL,
  response_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 8: WEBSITE MANAGEMENT (site_templates, site_settings, ad_placements)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.site_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  layout_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.site_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  setting_key TEXT NOT NULL UNIQUE,
  setting_value JSONB NOT NULL DEFAULT '{}'::jsonb,
  description TEXT,
  is_public_readable BOOLEAN NOT NULL DEFAULT FALSE,
  updated_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.ad_placements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_code TEXT NOT NULL UNIQUE,
  slot_name TEXT NOT NULL,
  placement_zone TEXT NOT NULL CHECK (placement_zone IN ('header_leaderboard', 'in_article_native', 'sidebar_sticky', 'footer_banner')),
  provider_network TEXT NOT NULL DEFAULT 'direct_programmatic',
  rpm_target_usd NUMERIC(8,2) NOT NULL DEFAULT 12.50,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 9: ANALYTICS (analytics_daily, website_traffic, social_analytics, revenue_reports)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_date DATE NOT NULL UNIQUE,
  total_articles_count INTEGER NOT NULL DEFAULT 0,
  published_articles_count INTEGER NOT NULL DEFAULT 0,
  news_discovered_count INTEGER NOT NULL DEFAULT 0,
  website_views_count BIGINT NOT NULL DEFAULT 0,
  social_reach_count BIGINT NOT NULL DEFAULT 0,
  estimated_revenue_usd NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  failed_jobs_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.website_traffic (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES public.articles(id) ON DELETE SET NULL,
  recorded_date DATE NOT NULL,
  page_views BIGINT NOT NULL DEFAULT 0,
  unique_visitors BIGINT NOT NULL DEFAULT 0,
  avg_read_time_seconds INTEGER NOT NULL DEFAULT 0,
  referral_source TEXT NOT NULL DEFAULT 'direct',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (article_id, recorded_date, referral_source)
);

CREATE TABLE IF NOT EXISTS public.social_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  social_post_id UUID NOT NULL REFERENCES public.social_posts(id) ON DELETE CASCADE,
  recorded_date DATE NOT NULL,
  impressions BIGINT NOT NULL DEFAULT 0,
  engagements BIGINT NOT NULL DEFAULT 0,
  link_clicks BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (social_post_id, recorded_date)
);

CREATE TABLE IF NOT EXISTS public.revenue_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_date DATE NOT NULL,
  ad_placement_id UUID REFERENCES public.ad_placements(id) ON DELETE SET NULL,
  category_id UUID REFERENCES public.news_categories(id) ON DELETE SET NULL,
  impressions BIGINT NOT NULL DEFAULT 0,
  clicks BIGINT NOT NULL DEFAULT 0,
  effective_rpm_usd NUMERIC(8,2) NOT NULL DEFAULT 0.00,
  gross_revenue_usd NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DOMAIN 10: SYSTEM MANAGEMENT (api_connections, system_logs, system_settings, webhook_events)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.api_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_slug TEXT NOT NULL UNIQUE,
  service_name TEXT NOT NULL,
  category TEXT NOT NULL,
  endpoint_target TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Not Configured' CHECK (status IN ('Connected', 'Disconnected', 'Checking', 'Error', 'Not Configured')),
  latency_ms INTEGER,
  last_checked_at TIMESTAMPTZ,
  diagnostic_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.system_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subsystem TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
  message TEXT NOT NULL,
  trace_context JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.system_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  setting_key TEXT NOT NULL UNIQUE,
  setting_value JSONB NOT NULL DEFAULT '{}'::jsonb,
  description TEXT,
  updated_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  event_type TEXT NOT NULL,
  external_event_id TEXT,
  status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'processed', 'failed', 'ignored')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEX DEFINITIONS (Performance for slugs, statuses, timestamps, FKs)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id_status ON public.user_sessions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_agents_status ON public.agents(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent_status_priority ON public.agent_tasks(agent_id, status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activity_created_at ON public.agent_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activity_event_type ON public.agent_activity(event_type);

CREATE INDEX IF NOT EXISTS idx_news_sources_status ON public.news_sources(status);
CREATE INDEX IF NOT EXISTS idx_trending_topics_velocity ON public.trending_topics(velocity_score DESC, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_source_status ON public.news_items(source_id, status);
CREATE INDEX IF NOT EXISTS idx_news_items_ingested_at ON public.news_items(ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_sessions_status ON public.research_sessions(status);
CREATE INDEX IF NOT EXISTS idx_fact_checks_status ON public.fact_checks(status, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_verified_claims_fact_check_id ON public.verified_claims(fact_check_id);

CREATE INDEX IF NOT EXISTS idx_articles_slug ON public.articles(slug);
CREATE INDEX IF NOT EXISTS idx_articles_stage_created_at ON public.articles(stage, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_public_published_at ON public.articles(is_public, published_at DESC) WHERE stage = 'Published' AND is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_articles_category_id ON public.articles(primary_category_id);
CREATE INDEX IF NOT EXISTS idx_article_tags_slug ON public.article_tags(tag_slug);

CREATE INDEX IF NOT EXISTS idx_image_library_status ON public.image_library(status);
CREATE INDEX IF NOT EXISTS idx_publishing_jobs_stage_scheduled ON public.publishing_jobs(stage, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_social_posts_status ON public.social_posts(status, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_publishing_logs_job_created ON public.publishing_logs(publishing_job_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_daily_date ON public.analytics_daily(metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_website_traffic_date ON public.website_traffic(recorded_date DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_reports_date ON public.revenue_reports(report_date DESC);

CREATE INDEX IF NOT EXISTS idx_system_logs_severity_created ON public.system_logs(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_events_status_created ON public.webhook_events(status, created_at DESC);

-- ============================================================================
-- UPDATED_AT TRIGGERS
-- ============================================================================

DO $$
DECLARE
  t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'users', 'user_roles', 'user_sessions',
    'agents', 'agent_configs', 'agent_tasks',
    'news_categories', 'news_sources', 'trending_topics', 'news_items',
    'research_sessions', 'fact_checks', 'verified_claims',
    'articles', 'editorial_quality', 'seo_metadata',
    'image_licenses', 'image_library',
    'social_accounts', 'publishing_jobs', 'social_posts',
    'site_templates', 'site_settings', 'ad_placements',
    'analytics_daily', 'revenue_reports',
    'api_connections', 'system_settings'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_updated_at ON public.%I;', t, t);
    EXECUTE format(
      'CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.trigger_set_updated_at();',
      t, t
    );
  END LOOP;
END;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) & ROLE AUTHORIZATION HELPERS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.has_nexus_role(allowed_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF auth.uid() IS NULL THEN
    RETURN FALSE;
  END IF;

  RETURN EXISTS (
    SELECT 1
    FROM public.users u
    JOIN public.user_roles ur ON ur.user_id = u.id
    WHERE u.auth_user_id = auth.uid()
      AND u.status = 'active'
      AND ur.role_name = ANY(allowed_roles)
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.has_any_role(allowed_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT public.has_nexus_role(allowed_roles);
$$;

CREATE OR REPLACE FUNCTION public.is_nexus_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT public.has_nexus_role(ARRAY['super_admin', 'managing_editor']);
$$;

CREATE OR REPLACE FUNCTION public.is_nexus_staff()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT public.has_nexus_role(ARRAY['super_admin', 'managing_editor', 'fact_checker', 'operator', 'viewer']);
$$;

-- Enable RLS across all 37 tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trending_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verified_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.editorial_quality ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seo_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_attributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.publishing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.publishing_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ad_placements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.website_traffic ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revenue_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

-- 1. PUBLIC READ-ONLY POLICIES (Strictly Published Public Articles & Approved Categories)
CREATE POLICY "Public visitors can read published public articles"
  ON public.articles FOR SELECT
  TO anon, authenticated
  USING (stage = 'Published' AND is_public = TRUE);

CREATE POLICY "Public visitors can read approved public categories"
  ON public.news_categories FOR SELECT
  TO anon, authenticated
  USING (is_public_approved = TRUE);

CREATE POLICY "Public visitors can read categories of published articles"
  ON public.article_categories FOR SELECT
  TO anon, authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.articles a
      WHERE a.id = article_categories.article_id
        AND a.stage = 'Published'
        AND a.is_public = TRUE
    )
  );

CREATE POLICY "Public visitors can read tags of published articles"
  ON public.article_tags FOR SELECT
  TO anon, authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.articles a
      WHERE a.id = article_tags.article_id
        AND a.stage = 'Published'
        AND a.is_public = TRUE
    )
  );

CREATE POLICY "Public visitors can read SEO metadata of published articles"
  ON public.seo_metadata FOR SELECT
  TO anon, authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.articles a
      WHERE a.id = seo_metadata.article_id
        AND a.stage = 'Published'
        AND a.is_public = TRUE
    )
  );

CREATE POLICY "Public visitors can read approved public images"
  ON public.image_library FOR SELECT
  TO anon, authenticated
  USING (status = 'approved' AND is_public = TRUE);

CREATE POLICY "Public visitors can read media attributions for published articles"
  ON public.media_attributions FOR SELECT
  TO anon, authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.articles a
      WHERE a.id = media_attributions.article_id
        AND a.stage = 'Published'
        AND a.is_public = TRUE
    )
  );

-- 2. AUTHENTICATED STAFF & ADMIN POLICIES (Protected Operational Data)
CREATE POLICY "Users can read own user profile or admin can read all"
  ON public.users FOR SELECT
  TO authenticated
  USING (auth_user_id = auth.uid() OR public.is_nexus_admin());

CREATE POLICY "Admins manage users"
  ON public.users FOR ALL
  TO authenticated
  USING (public.is_nexus_admin())
  WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Users can read own roles or admin can read all"
  ON public.user_roles FOR SELECT
  TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.users u WHERE u.id = user_roles.user_id AND u.auth_user_id = auth.uid())
    OR public.is_nexus_admin()
  );

CREATE POLICY "Super admins manage user roles"
  ON public.user_roles FOR ALL
  TO authenticated
  USING (public.has_nexus_role(ARRAY['super_admin']))
  WITH CHECK (public.has_nexus_role(ARRAY['super_admin']));

CREATE POLICY "Users view own sessions or super admin views all"
  ON public.user_sessions FOR SELECT
  TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.users u WHERE u.id = user_sessions.user_id AND u.auth_user_id = auth.uid())
    OR public.has_nexus_role(ARRAY['super_admin'])
  );

-- Protected Agent Configs, API Connections, Analytics, Revenue, System Tables
CREATE POLICY "Staff can read agents, tasks, and activity"
  ON public.agents FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Admins manage agents"
  ON public.agents FOR ALL TO authenticated USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins can access agent_configs"
  ON public.agent_configs FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Staff can read agent_tasks"
  ON public.agent_tasks FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Operators and admins manage agent_tasks"
  ON public.agent_tasks FOR ALL TO authenticated
  USING (public.has_nexus_role(ARRAY['super_admin', 'managing_editor', 'operator']))
  WITH CHECK (public.has_nexus_role(ARRAY['super_admin', 'managing_editor', 'operator']));

CREATE POLICY "Staff can read agent_activity"
  ON public.agent_activity FOR SELECT TO authenticated USING (public.is_nexus_staff());

-- Editorial, Intelligence & Verification Staff Policies
CREATE POLICY "Staff can read all articles and stages"
  ON public.articles FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Editors manage articles"
  ON public.articles FOR ALL TO authenticated
  USING (public.has_nexus_role(ARRAY['super_admin', 'managing_editor', 'fact_checker']))
  WITH CHECK (public.has_nexus_role(ARRAY['super_admin', 'managing_editor', 'fact_checker']));

CREATE POLICY "Staff read intelligence and verification tables"
  ON public.news_sources FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read trending_topics"
  ON public.trending_topics FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read news_items"
  ON public.news_items FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read research_sessions"
  ON public.research_sessions FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read research_sources"
  ON public.research_sources FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read fact_checks"
  ON public.fact_checks FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read verified_claims"
  ON public.verified_claims FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read article_versions"
  ON public.article_versions FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read editorial_quality"
  ON public.editorial_quality FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read image_licenses"
  ON public.image_licenses FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read publishing_jobs"
  ON public.publishing_jobs FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read social_accounts"
  ON public.social_accounts FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read social_posts"
  ON public.social_posts FOR SELECT TO authenticated USING (public.is_nexus_staff());
CREATE POLICY "Staff read publishing_logs"
  ON public.publishing_logs FOR SELECT TO authenticated USING (public.is_nexus_staff());

-- Admin-Only Policies for API Connections, Analytics, Revenue, and System Settings
CREATE POLICY "Only admins access api_connections"
  ON public.api_connections FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access analytics_daily"
  ON public.analytics_daily FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access website_traffic"
  ON public.website_traffic FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access social_analytics"
  ON public.social_analytics FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access revenue_reports"
  ON public.revenue_reports FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access system_logs"
  ON public.system_logs FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access system_settings"
  ON public.system_settings FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access webhook_events"
  ON public.webhook_events FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access site_settings"
  ON public.site_settings FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access site_templates"
  ON public.site_templates FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

CREATE POLICY "Only admins access ad_placements"
  ON public.ad_placements FOR ALL TO authenticated
  USING (public.is_nexus_admin()) WITH CHECK (public.is_nexus_admin());

-- ============================================================================
-- INITIAL SEED DATA (9 Autonomous Agents & Approved Public News Categories)
-- ============================================================================

INSERT INTO public.news_categories (slug, name, description, is_public_approved, display_order)
VALUES
  ('semiconductors', 'Semiconductors', 'Foundry capacity, wafer lithography, and chip supply chains.', TRUE, 1),
  ('energy-infrastructure', 'Energy Infrastructure', 'Grid transmission, HVDC interconnects, and power generation.', TRUE, 2),
  ('cloud-infrastructure', 'Cloud & Infrastructure', 'Hyperscale compute clusters, thermal management, and sovereign AI.', TRUE, 3),
  ('global-trade', 'Global Trade', 'Maritime freight corridors, customs filings, and logistics.', TRUE, 4)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.agents (slug, name, role_title, status, current_task_summary, processed_today_count, sla_score_pct)
VALUES
  ('orchestrator', 'Orchestrator', 'Master Pipeline Coordinator', 'Running', 'Balancing editorial queue priorities across active newsroom threads', 142, 99.60),
  ('trend-scout', 'Trend Scout', 'Global Wire & Signal Discovery', 'Running', 'Scanning RSS/Atom regulatory feeds for export filings', 312, 94.80),
  ('research-agent', 'Research Agent', 'Context & Primary Source Synthesis', 'Running', 'Compiling 10-K historical context for European grid interconnects', 64, 97.20),
  ('fact-checker', 'Fact Checker', 'Claim Verification & Citation Audit', 'Running', 'Cross-verifying numerical claims against primary filings', 58, 99.10),
  ('news-writer', 'News Writer', 'Autonomous Editorial Drafting', 'Running', 'Drafting analysis on lithography supply chain resilience', 48, 96.40),
  ('seo-agent', 'SEO Agent', 'Search Intent & Structured Metadata', 'Idle', 'Awaiting next approved draft from Fact Checker for JSON-LD injection', 44, 95.00),
  ('media-agent', 'Media Agent', 'Editorial Visuals & Alt-Text Packaging', 'Running', 'Generating 16:9 hero crops and WCAG-compliant alt descriptions', 41, 98.00),
  ('publishing-agent', 'Publishing Agent', 'CMS & Social Distribution Dispatch', 'Paused', 'Awaiting Step 4 CMS webhook binding', 34, 100.00),
  ('analytics-agent', 'Analytics Agent', 'Traffic, Reach & RPM Attribution', 'Idle', 'Aggregating cohort retention and RPM benchmarks', 24, 97.80)
ON CONFLICT (slug) DO NOTHING;

COMMIT;
