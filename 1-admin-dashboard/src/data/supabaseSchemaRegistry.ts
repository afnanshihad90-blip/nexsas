export interface DatabaseTableSpec {
  tableName: string;
  domain: string;
  primaryKey: string;
  foreignKeys: string[];
  indexedColumns: string[];
  rlsPolicySummary: string;
  publicReadAllowed: boolean;
  retentionRule: string;
}

export interface RlsPolicySpec {
  policyName: string;
  tableName: string;
  operation: 'SELECT' | 'INSERT' | 'UPDATE' | 'DELETE' | 'ALL';
  targetRoles: string;
  usingExpression: string;
}

export interface DatabaseIndexSpec {
  indexName: string;
  tableName: string;
  columns: string;
  purpose: string;
}

export const SUPABASE_SCHEMA_TABLES: DatabaseTableSpec[] = [
  // 1. User Management
  {
    tableName: 'users',
    domain: 'User Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['auth_user_id -> auth.users(id)'],
    indexedColumns: ['email (UNIQUE)', 'auth_user_id (UNIQUE)', 'status'],
    rlsPolicySummary: 'Self profile read or Admin full access; no public access.',
    publicReadAllowed: false,
    retentionRule: 'Soft archive via status = archived',
  },
  {
    tableName: 'user_roles',
    domain: 'User Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['user_id -> users(id) ON DELETE CASCADE', 'assigned_by -> users(id) ON DELETE SET NULL'],
    indexedColumns: ['user_id', '(user_id, role_name) UNIQUE'],
    rlsPolicySummary: 'Users read own roles; only super_admin can mutate.',
    publicReadAllowed: false,
    retentionRule: 'Cascade delete with parent user',
  },
  {
    tableName: 'user_sessions',
    domain: 'User Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['user_id -> users(id) ON DELETE CASCADE'],
    indexedColumns: ['(user_id, status)', 'session_token_hash (UNIQUE)'],
    rlsPolicySummary: 'Users read own sessions; super_admin audit access.',
    publicReadAllowed: false,
    retentionRule: 'Purge expired sessions after 90 days',
  },

  // 2. AI Agent Management
  {
    tableName: 'agents',
    domain: 'AI Agent Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['slug (UNIQUE)', 'name (UNIQUE)', 'status'],
    rlsPolicySummary: 'Authenticated staff read; Admins manage.',
    publicReadAllowed: false,
    retentionRule: 'Permanent core registry (9 newsroom roles)',
  },
  {
    tableName: 'agent_configs',
    domain: 'AI Agent Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['agent_id -> agents(id) ON DELETE CASCADE', 'updated_by -> users(id) ON DELETE SET NULL'],
    indexedColumns: ['agent_id (UNIQUE)'],
    rlsPolicySummary: 'Strictly protected: Admin-only read/write.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with agent record',
  },
  {
    tableName: 'agent_activity',
    domain: 'AI Agent Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['agent_id -> agents(id) ON DELETE CASCADE', 'task_id -> agent_tasks(id) ON DELETE SET NULL'],
    indexedColumns: ['created_at DESC', 'event_type'],
    rlsPolicySummary: 'Authenticated staff read; FastAPI backend writes.',
    publicReadAllowed: false,
    retentionRule: 'Rolling 180-day operational telemetry retention',
  },
  {
    tableName: 'agent_tasks',
    domain: 'AI Agent Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['agent_id -> agents(id) ON DELETE CASCADE'],
    indexedColumns: ['(agent_id, status, priority DESC)'],
    rlsPolicySummary: 'Authenticated staff read; Operators & Admins manage.',
    publicReadAllowed: false,
    retentionRule: 'Archive completed tasks after 90 days',
  },

  // 3. News Intelligence
  {
    tableName: 'news_sources',
    domain: 'News Intelligence',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['name (UNIQUE)', 'feed_url (UNIQUE)', 'status'],
    rlsPolicySummary: 'Authenticated staff read; Admins manage.',
    publicReadAllowed: false,
    retentionRule: 'ON DELETE RESTRICT when news_items exist',
  },
  {
    tableName: 'news_items',
    domain: 'News Intelligence',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'source_id -> news_sources(id) ON DELETE RESTRICT',
      'category_id -> news_categories(id) ON DELETE SET NULL',
      'trending_topic_id -> trending_topics(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['(source_id, status)', 'ingested_at DESC', '(source_id, external_guid) UNIQUE'],
    rlsPolicySummary: 'Authenticated staff read; internal ingestion only.',
    publicReadAllowed: false,
    retentionRule: 'Retain verified items; prune discarded items after 30 days',
  },
  {
    tableName: 'news_categories',
    domain: 'News Intelligence',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['slug (UNIQUE)', 'name (UNIQUE)'],
    rlsPolicySummary: 'Public SELECT allowed when is_public_approved = TRUE.',
    publicReadAllowed: true,
    retentionRule: 'Permanent taxonomy table',
  },
  {
    tableName: 'trending_topics',
    domain: 'News Intelligence',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'category_id -> news_categories(id) ON DELETE SET NULL',
      'assigned_agent_id -> agents(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['slug (UNIQUE)', '(velocity_score DESC, discovered_at DESC)'],
    rlsPolicySummary: 'Authenticated staff read; internal signal scoring.',
    publicReadAllowed: false,
    retentionRule: 'Archive after 60 days',
  },

  // 4. Research & Verification
  {
    tableName: 'research_sessions',
    domain: 'Research & Verification',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'trending_topic_id -> trending_topics(id) ON DELETE SET NULL',
      'lead_agent_id -> agents(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['status'],
    rlsPolicySummary: 'Authenticated staff read; internal research dossier.',
    publicReadAllowed: false,
    retentionRule: 'Retain permanently for editorial auditability',
  },
  {
    tableName: 'research_sources',
    domain: 'Research & Verification',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'research_session_id -> research_sessions(id) ON DELETE CASCADE',
      'news_item_id -> news_items(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['research_session_id'],
    rlsPolicySummary: 'Authenticated staff read.',
    publicReadAllowed: false,
    retentionRule: 'Cascade delete with research_session',
  },
  {
    tableName: 'fact_checks',
    domain: 'Research & Verification',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'research_session_id -> research_sessions(id) ON DELETE CASCADE',
      'auditor_agent_id -> agents(id) ON DELETE SET NULL',
      'reviewed_by_user_id -> users(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['(status, checked_at DESC)'],
    rlsPolicySummary: 'Authenticated staff read; Fact Checkers & Editors manage.',
    publicReadAllowed: false,
    retentionRule: 'Permanent compliance audit trail',
  },
  {
    tableName: 'verified_claims',
    domain: 'Research & Verification',
    primaryKey: 'id (UUID)',
    foreignKeys: ['fact_check_id -> fact_checks(id) ON DELETE CASCADE'],
    indexedColumns: ['fact_check_id'],
    rlsPolicySummary: 'Authenticated staff read.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with fact_checks',
  },

  // 5. Content Management
  {
    tableName: 'articles',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'primary_category_id -> news_categories(id) ON DELETE SET NULL',
      'research_session_id -> research_sessions(id) ON DELETE SET NULL',
      'author_agent_id -> agents(id) ON DELETE SET NULL',
      'approved_by_user_id -> users(id) ON DELETE SET NULL',
    ],
    indexedColumns: [
      'article_code (UNIQUE)',
      'slug (UNIQUE)',
      '(stage, created_at DESC)',
      '(is_public, published_at DESC) PARTIAL',
    ],
    rlsPolicySummary: 'Public SELECT only when stage = Published AND is_public = TRUE; Staff read all.',
    publicReadAllowed: true,
    retentionRule: 'Permanent editorial archive',
  },
  {
    tableName: 'article_versions',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'article_id -> articles(id) ON DELETE CASCADE',
      'created_by_agent_id -> agents(id) ON DELETE SET NULL',
      'created_by_user_id -> users(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['(article_id, version_number) UNIQUE'],
    rlsPolicySummary: 'Authenticated staff read; internal revision history.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with parent article',
  },
  {
    tableName: 'article_categories',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'article_id -> articles(id) ON DELETE CASCADE',
      'category_id -> news_categories(id) ON DELETE CASCADE',
    ],
    indexedColumns: ['(article_id, category_id) UNIQUE'],
    rlsPolicySummary: 'Public SELECT when parent article is Published & Public.',
    publicReadAllowed: true,
    retentionRule: 'Cascade with article or category',
  },
  {
    tableName: 'article_tags',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['article_id -> articles(id) ON DELETE CASCADE'],
    indexedColumns: ['tag_slug', '(article_id, tag_slug) UNIQUE'],
    rlsPolicySummary: 'Public SELECT when parent article is Published & Public.',
    publicReadAllowed: true,
    retentionRule: 'Cascade with parent article',
  },
  {
    tableName: 'editorial_quality',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['article_id -> articles(id) ON DELETE CASCADE'],
    indexedColumns: ['article_id (UNIQUE)'],
    rlsPolicySummary: 'Authenticated staff read; internal quality scorecard.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with parent article',
  },
  {
    tableName: 'seo_metadata',
    domain: 'Content Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['article_id -> articles(id) ON DELETE CASCADE'],
    indexedColumns: ['article_id (UNIQUE)'],
    rlsPolicySummary: 'Public SELECT when parent article is Published & Public.',
    publicReadAllowed: true,
    retentionRule: 'Cascade with parent article',
  },

  // 6. Media Management
  {
    tableName: 'image_library',
    domain: 'Media Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'license_id -> image_licenses(id) ON DELETE SET NULL',
      'created_by_agent_id -> agents(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['storage_path (UNIQUE)', 'status'],
    rlsPolicySummary: 'Public SELECT when status = approved AND is_public = TRUE.',
    publicReadAllowed: true,
    retentionRule: 'Soft archive via status = archived',
  },
  {
    tableName: 'image_licenses',
    domain: 'Media Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['license_code (UNIQUE)'],
    rlsPolicySummary: 'Authenticated staff read; Admin manage.',
    publicReadAllowed: false,
    retentionRule: 'Permanent rights compliance record',
  },
  {
    tableName: 'media_attributions',
    domain: 'Media Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'image_id -> image_library(id) ON DELETE CASCADE',
      'article_id -> articles(id) ON DELETE CASCADE',
    ],
    indexedColumns: ['image_id', 'article_id'],
    rlsPolicySummary: 'Public SELECT for published public articles.',
    publicReadAllowed: true,
    retentionRule: 'Cascade with image or article',
  },

  // 7. Publishing
  {
    tableName: 'publishing_jobs',
    domain: 'Publishing',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'article_id -> articles(id) ON DELETE CASCADE',
      'dispatched_by_agent_id -> agents(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['(stage, scheduled_at)'],
    rlsPolicySummary: 'Authenticated staff read; Operators & Admins manage.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with parent article',
  },
  {
    tableName: 'social_accounts',
    domain: 'Publishing',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['(platform, handle) UNIQUE'],
    rlsPolicySummary: 'Authenticated staff read; Admins manage.',
    publicReadAllowed: false,
    retentionRule: 'ON DELETE RESTRICT when social_posts exist',
  },
  {
    tableName: 'social_posts',
    domain: 'Publishing',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'publishing_job_id -> publishing_jobs(id) ON DELETE CASCADE',
      'article_id -> articles(id) ON DELETE CASCADE',
      'social_account_id -> social_accounts(id) ON DELETE RESTRICT',
    ],
    indexedColumns: ['(status, published_at DESC)'],
    rlsPolicySummary: 'Authenticated staff read.',
    publicReadAllowed: false,
    retentionRule: 'Retain for social analytics attribution',
  },
  {
    tableName: 'publishing_logs',
    domain: 'Publishing',
    primaryKey: 'id (UUID)',
    foreignKeys: ['publishing_job_id -> publishing_jobs(id) ON DELETE CASCADE'],
    indexedColumns: ['(publishing_job_id, created_at DESC)'],
    rlsPolicySummary: 'Authenticated staff read.',
    publicReadAllowed: false,
    retentionRule: 'Rolling 90-day dispatch log retention',
  },

  // 8. Website Management
  {
    tableName: 'site_templates',
    domain: 'Website Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['template_key (UNIQUE)'],
    rlsPolicySummary: 'Admin-only management.',
    publicReadAllowed: false,
    retentionRule: 'Permanent layout registry',
  },
  {
    tableName: 'site_settings',
    domain: 'Website Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['updated_by -> users(id) ON DELETE SET NULL'],
    indexedColumns: ['setting_key (UNIQUE)'],
    rlsPolicySummary: 'Admin-only management.',
    publicReadAllowed: false,
    retentionRule: 'Permanent site configuration',
  },
  {
    tableName: 'ad_placements',
    domain: 'Website Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['slot_code (UNIQUE)'],
    rlsPolicySummary: 'Admin-only management.',
    publicReadAllowed: false,
    retentionRule: 'Permanent ad inventory definitions',
  },

  // 9. Analytics
  {
    tableName: 'analytics_daily',
    domain: 'Analytics',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['metric_date DESC (UNIQUE)'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Permanent daily rollup',
  },
  {
    tableName: 'website_traffic',
    domain: 'Analytics',
    primaryKey: 'id (UUID)',
    foreignKeys: ['article_id -> articles(id) ON DELETE SET NULL'],
    indexedColumns: ['recorded_date DESC', '(article_id, recorded_date, referral_source) UNIQUE'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Retain 24 months of daily article granularity',
  },
  {
    tableName: 'social_analytics',
    domain: 'Analytics',
    primaryKey: 'id (UUID)',
    foreignKeys: ['social_post_id -> social_posts(id) ON DELETE CASCADE'],
    indexedColumns: ['(social_post_id, recorded_date) UNIQUE'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Cascade with social_post',
  },
  {
    tableName: 'revenue_reports',
    domain: 'Analytics',
    primaryKey: 'id (UUID)',
    foreignKeys: [
      'ad_placement_id -> ad_placements(id) ON DELETE SET NULL',
      'category_id -> news_categories(id) ON DELETE SET NULL',
    ],
    indexedColumns: ['report_date DESC'],
    rlsPolicySummary: 'Protected financial data: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Permanent financial ledger retention (7 years)',
  },

  // 10. System Management
  {
    tableName: 'api_connections',
    domain: 'System Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['service_slug (UNIQUE)'],
    rlsPolicySummary: 'Protected infrastructure metadata: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Permanent service registry (no secrets stored)',
  },
  {
    tableName: 'system_logs',
    domain: 'System Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['(severity, created_at DESC)'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Rolling 90-day log retention',
  },
  {
    tableName: 'system_settings',
    domain: 'System Management',
    primaryKey: 'id (UUID)',
    foreignKeys: ['updated_by -> users(id) ON DELETE SET NULL'],
    indexedColumns: ['setting_key (UNIQUE)'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Permanent platform configuration',
  },
  {
    tableName: 'webhook_events',
    domain: 'System Management',
    primaryKey: 'id (UUID)',
    foreignKeys: [],
    indexedColumns: ['(status, created_at DESC)'],
    rlsPolicySummary: 'Protected: Admin-only access.',
    publicReadAllowed: false,
    retentionRule: 'Purge processed webhook payloads after 30 days',
  },
];

export const SUPABASE_RLS_POLICIES: RlsPolicySpec[] = [
  {
    policyName: 'Public visitors can read published public articles',
    tableName: 'articles',
    operation: 'SELECT',
    targetRoles: 'anon, authenticated',
    usingExpression: "stage = 'Published' AND is_public = TRUE",
  },
  {
    policyName: 'Public visitors can read approved public categories',
    tableName: 'news_categories',
    operation: 'SELECT',
    targetRoles: 'anon, authenticated',
    usingExpression: 'is_public_approved = TRUE',
  },
  {
    policyName: 'Public visitors can read SEO metadata of published articles',
    tableName: 'seo_metadata',
    operation: 'SELECT',
    targetRoles: 'anon, authenticated',
    usingExpression: "EXISTS (SELECT 1 FROM articles a WHERE a.id = seo_metadata.article_id AND a.stage = 'Published' AND a.is_public = TRUE)",
  },
  {
    policyName: 'Only admins can access agent_configs',
    tableName: 'agent_configs',
    operation: 'ALL',
    targetRoles: 'authenticated',
    usingExpression: 'public.is_nexus_admin()',
  },
  {
    policyName: 'Only admins access api_connections',
    tableName: 'api_connections',
    operation: 'ALL',
    targetRoles: 'authenticated',
    usingExpression: 'public.is_nexus_admin()',
  },
  {
    policyName: 'Only admins access revenue_reports & analytics_daily',
    tableName: 'revenue_reports',
    operation: 'ALL',
    targetRoles: 'authenticated',
    usingExpression: 'public.is_nexus_admin()',
  },
  {
    policyName: 'Super admins manage user roles',
    tableName: 'user_roles',
    operation: 'ALL',
    targetRoles: 'authenticated',
    usingExpression: "public.has_nexus_role(ARRAY['super_admin'])",
  },
];

export const SUPABASE_KEY_INDEXES: DatabaseIndexSpec[] = [
  {
    indexName: 'idx_articles_slug',
    tableName: 'articles',
    columns: '(slug)',
    purpose: 'O(log n) lookup for permanent news website article routing',
  },
  {
    indexName: 'idx_articles_public_published_at',
    tableName: 'articles',
    columns: '(is_public, published_at DESC) WHERE stage = Published',
    purpose: 'Partial index accelerating public reader feed queries',
  },
  {
    indexName: 'idx_articles_stage_created_at',
    tableName: 'articles',
    columns: '(stage, created_at DESC)',
    purpose: 'Publishing queue stage filtering and dashboard sorting',
  },
  {
    indexName: 'idx_agent_tasks_agent_status_priority',
    tableName: 'agent_tasks',
    columns: '(agent_id, status, priority DESC)',
    purpose: 'Fast worker task acquisition by priority queue',
  },
  {
    indexName: 'idx_agent_activity_created_at',
    tableName: 'agent_activity',
    columns: '(created_at DESC)',
    purpose: 'Chronological Recent Activity timeline queries',
  },
  {
    indexName: 'idx_trending_topics_velocity',
    tableName: 'trending_topics',
    columns: '(velocity_score DESC, discovered_at DESC)',
    purpose: 'High-velocity news discovery ranking',
  },
  {
    indexName: 'idx_analytics_daily_date',
    tableName: 'analytics_daily',
    columns: '(metric_date DESC)',
    purpose: 'Date-range KPI rollups (24h, 7d, 30d, 90d)',
  },
];
