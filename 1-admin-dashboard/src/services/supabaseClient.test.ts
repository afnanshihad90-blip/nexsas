import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SUPABASE_DISCONNECTED_BANNER,
  supabaseService,
  validateSupabaseCredentials,
} from './supabaseClient';
import {
  SUPABASE_KEY_INDEXES,
  SUPABASE_RLS_POLICIES,
  SUPABASE_SCHEMA_TABLES,
} from '../data/supabaseSchemaRegistry';

test('validateSupabaseCredentials returns NOT CONNECTED when env vars are empty or placeholders', () => {
  const emptyResult = validateSupabaseCredentials('', '');
  assert.equal(emptyResult.isConfigured, false);
  assert.equal(emptyResult.statusLabel, SUPABASE_DISCONNECTED_BANNER);
  assert.equal(emptyResult.connectionState, 'Not Configured');

  const placeholderResult = validateSupabaseCredentials(
    'https://your-project.supabase.co',
    'MY_SUPABASE_PUBLISHABLE_KEY'
  );
  assert.equal(placeholderResult.isConfigured, false);
  assert.equal(placeholderResult.statusLabel, SUPABASE_DISCONNECTED_BANNER);
});

test('validateSupabaseCredentials blocks secret or service_role keys in frontend variables', () => {
  const secretAttempt = validateSupabaseCredentials(
    'https://xyzcompany.supabase.co',
    'sb_secret_1234567890abcdefghijklmnop'
  );
  assert.equal(secretAttempt.isConfigured, false);
  assert.equal(secretAttempt.connectionState, 'Error');
  assert.ok(secretAttempt.securityViolation?.includes('SECURITY BLOCK'));
});

test('validateSupabaseCredentials accepts valid https URL and publishable anon key', () => {
  const valid = validateSupabaseCredentials(
    'https://nexusmedia.supabase.co',
    'sb_publishable_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9_anon_key'
  );
  assert.equal(valid.isConfigured, true);
  assert.equal(valid.connectionState, 'Connected');
  assert.equal(valid.securityViolation, null);
});

test('supabaseService safely handles disconnected state without throwing', async () => {
  const snapshot = await supabaseService.fetchDashboardDatabaseSnapshot();
  assert.equal(snapshot.isConnected, false);
  assert.equal(snapshot.statusLabel, SUPABASE_DISCONNECTED_BANNER);
  assert.equal(snapshot.isDemoFallback, true);
  assert.equal(snapshot.articleCount, null);
  assert.equal(snapshot.publishedArticleCount, null);
});

test('SUPABASE_SCHEMA_TABLES includes all 37 required tables across 10 domains', () => {
  const requiredTables = [
    // User Management
    'users',
    'user_roles',
    'user_sessions',
    // AI Agent Management
    'agents',
    'agent_configs',
    'agent_activity',
    'agent_tasks',
    // News Intelligence
    'news_sources',
    'news_items',
    'news_categories',
    'trending_topics',
    // Research & Verification
    'research_sessions',
    'research_sources',
    'fact_checks',
    'verified_claims',
    // Content Management
    'articles',
    'article_versions',
    'article_categories',
    'article_tags',
    'editorial_quality',
    'seo_metadata',
    // Media Management
    'image_library',
    'image_licenses',
    'media_attributions',
    // Publishing
    'publishing_jobs',
    'social_accounts',
    'social_posts',
    'publishing_logs',
    // Website Management
    'site_templates',
    'site_settings',
    'ad_placements',
    // Analytics
    'analytics_daily',
    'website_traffic',
    'social_analytics',
    'revenue_reports',
    // System Management
    'api_connections',
    'system_logs',
    'system_settings',
    'webhook_events',
  ];

  assert.equal(SUPABASE_SCHEMA_TABLES.length, 39);
  const actualNames = new Set(SUPABASE_SCHEMA_TABLES.map((t) => t.tableName));
  for (const reqTable of requiredTables) {
    assert.ok(actualNames.has(reqTable), `Missing required table: ${reqTable}`);
  }
  assert.ok(SUPABASE_RLS_POLICIES.length >= 7);
  assert.ok(SUPABASE_KEY_INDEXES.length >= 7);
});
