-- ============================================================================
-- NEXUS MEDIA AI — STEP 5: NEWS INTELLIGENCE ENGINE MIGRATION
-- Migration ID: 20261109000003_nexus_media_ai_news_intelligence_engine.sql
-- Purpose: Reuses and extends Step 2 news tables (news_categories, news_sources,
--          news_items) and creates story_clusters, trend_scores,
--          news_classifications, collection_runs, and source_fetch_logs
--          with indexes and Row Level Security (RLS).
-- ============================================================================

BEGIN;

-- 1. Extend public.news_categories for the 4 Supported News Niches
ALTER TABLE public.news_categories
  ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS topics JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS regions JSONB NOT NULL DEFAULT '["Global"]'::jsonb,
  ADD COLUMN IF NOT EXISTS languages JSONB NOT NULL DEFAULT '["en"]'::jsonb;

-- Seed the 4 required news categories idempotently
INSERT INTO public.news_categories (slug, name, description, is_public_approved, is_enabled, display_order, keywords, topics, regions, languages)
VALUES
  (
    'business-finance',
    'Business & Finance',
    'Global markets, central banks, corporate earnings, M&A filings, supply chains, and macroeconomic policy.',
    TRUE,
    TRUE,
    1,
    '["earnings", "sec filing", "interest rates", "inflation", "central bank", "bond yield", "merger", "acquisition", "supply chain", "gdp", "fiscal"]'::jsonb,
    '["Macroeconomics", "Capital Markets", "Corporate Filings", "Global Trade"]'::jsonb,
    '["Global", "North America", "Europe", "Asia-Pacific"]'::jsonb,
    '["en"]'::jsonb
  ),
  (
    'world-trending-news',
    'World Trending News',
    'Geopolitics, international diplomacy, infrastructure corridors, energy security, and multilateral regulatory developments.',
    TRUE,
    TRUE,
    2,
    '["treaty", "summit", "sanctions", "energy grid", "parliament", "united nations", "maritime", "cross-border", "diplomatic", "election", "minister"]'::jsonb,
    '["Geopolitics", "Energy Security", "International Law", "Infrastructure"]'::jsonb,
    '["Global", "Europe", "Middle East", "Asia-Pacific", "Americas"]'::jsonb,
    '["en"]'::jsonb
  ),
  (
    'ai-technology',
    'AI & Technology',
    'Artificial intelligence models, semiconductor fabrication, cloud compute infrastructure, cybersecurity, and enterprise software.',
    TRUE,
    TRUE,
    3,
    '["artificial intelligence", "llm", "semiconductor", "wafer", "lithography", "gpu", "datacenter", "cybersecurity", "neural network", "cloud compute", "foundry"]'::jsonb,
    '["Artificial Intelligence", "Semiconductors", "Cloud Compute", "Cybersecurity"]'::jsonb,
    '["Global", "North America", "Europe", "East Asia"]'::jsonb,
    '["en"]'::jsonb
  ),
  (
    'science-space',
    'Science & Space',
    'Orbital launch systems, satellite constellations, fusion energy research, climate telemetry, biotechnology, and peer-reviewed discoveries.',
    TRUE,
    TRUE,
    4,
    '["orbital", "satellite", "nasa", "esa", "launch vehicle", "fusion", "telescope", "lunar", "astrophysics", "quantum", "CRISPR", "observatory"]'::jsonb,
    '["Space Exploration", "Orbital Infrastructure", "Physics & Fusion", "Earth Observation"]'::jsonb,
    '["Global"]'::jsonb,
    '["en"]'::jsonb
  )
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  keywords = EXCLUDED.keywords,
  topics = EXCLUDED.topics,
  regions = EXCLUDED.regions,
  languages = EXCLUDED.languages;

-- 2. Extend public.news_sources for Modular Connectors & Reliability
ALTER TABLE public.news_sources
  ADD COLUMN IF NOT EXISTS connector_type TEXT NOT NULL DEFAULT 'rss_feed'
    CHECK (connector_type IN ('rss_feed', 'gdelt_api', 'news_api', 'admin_rss')),
  ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS reliability_score NUMERIC(5,2) NOT NULL DEFAULT 90.00,
  ADD COLUMN IF NOT EXISTS rate_limit_per_minute INTEGER NOT NULL DEFAULT 30,
  ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER NOT NULL DEFAULT 15,
  ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS terms_compliant BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS last_successful_fetch_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_error_message TEXT;

-- 3. Create public.story_clusters for Stage 3 Multi-Report Event Clustering
CREATE TABLE IF NOT EXISTS public.story_clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_code TEXT NOT NULL UNIQUE,
  canonical_slug TEXT NOT NULL UNIQUE,
  main_headline TEXT NOT NULL,
  primary_category TEXT NOT NULL DEFAULT 'World Trending News',
  secondary_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  related_source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  independent_publishers_count INTEGER NOT NULL DEFAULT 1,
  syndicated_copies_count INTEGER NOT NULL DEFAULT 0,
  first_discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  latest_update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'research_queued', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Extend public.news_items with Step 5 Collection & Deduplication Metadata
ALTER TABLE public.news_items
  ADD COLUMN IF NOT EXISTS canonical_url TEXT,
  ADD COLUMN IF NOT EXISTS normalized_headline TEXT,
  ADD COLUMN IF NOT EXISTS source_name TEXT,
  ADD COLUMN IF NOT EXISTS author TEXT,
  ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'en',
  ADD COLUMN IF NOT EXISTS category_name TEXT,
  ADD COLUMN IF NOT EXISTS short_description TEXT,
  ADD COLUMN IF NOT EXISTS image_url TEXT,
  ADD COLUMN IF NOT EXISTS image_license_verified BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS source_reliability_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS is_syndicated_copy BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS story_cluster_id UUID REFERENCES public.story_clusters(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS first_discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS collection_status TEXT NOT NULL DEFAULT 'collected'
    CHECK (collection_status IN ('collected', 'duplicate', 'classified', 'archived', 'rejected'));

-- 5. Create public.trend_scores for Configurable Weighted Trend Scoring
CREATE TABLE IF NOT EXISTS public.trend_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_cluster_id UUID NOT NULL UNIQUE REFERENCES public.story_clusters(id) ON DELETE CASCADE,
  trend_score NUMERIC(5,2) NOT NULL CHECK (trend_score >= 0 AND trend_score <= 100),
  trend_level TEXT NOT NULL CHECK (trend_level IN ('High', 'Normal', 'Low', 'Ignore')),
  score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
  popularity_measurement_status TEXT NOT NULL DEFAULT 'estimated_from_coverage'
    CHECK (popularity_measurement_status IN ('connected_live', 'estimated_from_coverage', 'unavailable')),
  confidence NUMERIC(4,2) NOT NULL DEFAULT 0.85,
  trend_category TEXT NOT NULL,
  supporting_source_count INTEGER NOT NULL DEFAULT 1,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  trend_status TEXT NOT NULL DEFAULT 'emerging' CHECK (trend_status IN ('emerging', 'peaking', 'stable', 'cooling', 'ignored')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Create public.news_classifications for Rule-Based + AI Topic Classification
CREATE TABLE IF NOT EXISTS public.news_classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  news_item_id UUID REFERENCES public.news_items(id) ON DELETE CASCADE,
  story_cluster_id UUID REFERENCES public.story_clusters(id) ON DELETE CASCADE,
  primary_category TEXT NOT NULL,
  secondary_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  classification_method TEXT NOT NULL DEFAULT 'rule_based' CHECK (classification_method IN ('rule_based', 'hybrid_ai')),
  confidence NUMERIC(4,2) NOT NULL DEFAULT 0.80,
  reasoning TEXT NOT NULL,
  needs_review BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Create public.collection_runs for Scheduled & Cloudflare Worker Triggered Scans
CREATE TABLE IF NOT EXISTS public.collection_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key TEXT NOT NULL UNIQUE,
  trigger_source TEXT NOT NULL DEFAULT 'manual_operator' CHECK (trigger_source IN ('manual_operator', 'cloudflare_worker_cron', 'scheduled_interval')),
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'partial_failure', 'failed')),
  scan_interval_seconds INTEGER NOT NULL DEFAULT 300,
  total_discovered INTEGER NOT NULL DEFAULT 0,
  new_stories_count INTEGER NOT NULL DEFAULT 0,
  duplicate_stories_count INTEGER NOT NULL DEFAULT 0,
  failed_sources_count INTEGER NOT NULL DEFAULT 0,
  error_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  next_scheduled_scan_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Create public.source_fetch_logs for Per-Source Telemetry & Error Tracking
CREATE TABLE IF NOT EXISTS public.source_fetch_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  collection_run_id UUID REFERENCES public.collection_runs(id) ON DELETE CASCADE,
  source_id UUID REFERENCES public.news_sources(id) ON DELETE SET NULL,
  source_name TEXT NOT NULL,
  connector_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('success', 'timeout', 'rate_limited', 'invalid_feed', 'ssrf_blocked', 'error')),
  items_fetched INTEGER NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  retry_attempts INTEGER NOT NULL DEFAULT 0,
  error_detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Triggers for updated_at
DROP TRIGGER IF EXISTS trg_story_clusters_updated_at ON public.story_clusters;
CREATE TRIGGER trg_story_clusters_updated_at
  BEFORE UPDATE ON public.story_clusters
  FOR EACH ROW
  EXECUTE FUNCTION public.trigger_set_updated_at();

DROP TRIGGER IF EXISTS trg_trend_scores_updated_at ON public.trend_scores;
CREATE TRIGGER trg_trend_scores_updated_at
  BEFORE UPDATE ON public.trend_scores
  FOR EACH ROW
  EXECUTE FUNCTION public.trigger_set_updated_at();

-- 10. Indexes for Step 5 Queries
CREATE INDEX IF NOT EXISTS idx_news_items_canonical_url ON public.news_items(canonical_url);
CREATE INDEX IF NOT EXISTS idx_news_items_cluster_id ON public.news_items(story_cluster_id);
CREATE INDEX IF NOT EXISTS idx_story_clusters_category_status ON public.story_clusters(primary_category, status, latest_update_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_scores_score_desc ON public.trend_scores(trend_score DESC, trend_level);
CREATE INDEX IF NOT EXISTS idx_news_classifications_review ON public.news_classifications(needs_review, primary_category);
CREATE INDEX IF NOT EXISTS idx_collection_runs_started ON public.collection_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_fetch_logs_created ON public.source_fetch_logs(created_at DESC, status);

-- 11. Row Level Security (RLS)
ALTER TABLE public.story_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trend_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collection_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_fetch_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins and operators manage story_clusters" ON public.story_clusters;
CREATE POLICY "Admins and operators manage story_clusters"
  ON public.story_clusters
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator', 'fact_checker', 'viewer']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

DROP POLICY IF EXISTS "Admins and operators manage trend_scores" ON public.trend_scores;
CREATE POLICY "Admins and operators manage trend_scores"
  ON public.trend_scores
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator', 'fact_checker', 'viewer']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

DROP POLICY IF EXISTS "Admins and operators manage news_classifications" ON public.news_classifications;
CREATE POLICY "Admins and operators manage news_classifications"
  ON public.news_classifications
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator', 'fact_checker']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

DROP POLICY IF EXISTS "Admins and operators manage collection_runs" ON public.collection_runs;
CREATE POLICY "Admins and operators manage collection_runs"
  ON public.collection_runs
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

DROP POLICY IF EXISTS "Admins and operators manage source_fetch_logs" ON public.source_fetch_logs;
CREATE POLICY "Admins and operators manage source_fetch_logs"
  ON public.source_fetch_logs
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

COMMIT;
