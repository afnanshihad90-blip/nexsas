import test from 'node:test';
import assert from 'node:assert/strict';
import {
  BACKEND_CONNECTED_BANNER,
  BACKEND_DISCONNECTED_BANNER,
  FASTAPI_ENDPOINT_REGISTRY,
  nexusApi,
  validateFastApiEnv,
} from './apiService';

test('validateFastApiEnv returns BACKEND NOT CONNECTED when VITE_FASTAPI_BASE_URL is empty', () => {
  const result = validateFastApiEnv({});
  assert.equal(result.isConfigured, false);
  assert.equal(result.statusLabel, BACKEND_DISCONNECTED_BANNER);
  assert.equal(result.connectionState, 'Not Configured');
  assert.equal(result.securityViolation, null);
});

test('validateFastApiEnv rejects leaked backend secret keys in VITE_* variables', () => {
  const result = validateFastApiEnv({
    VITE_FASTAPI_BASE_URL: 'http://localhost:8000',
    VITE_JWT_SECRET: 'leaked-secret',
  });
  assert.equal(result.isConfigured, false);
  assert.equal(result.statusLabel, BACKEND_DISCONNECTED_BANNER);
  assert.equal(result.connectionState, 'Error');
  assert.ok(result.securityViolation?.includes('VITE_JWT_SECRET'));
});

test('validateFastApiEnv accepts valid http/https FastAPI base URL and strips trailing slash', () => {
  const result = validateFastApiEnv({
    VITE_FASTAPI_BASE_URL: 'https://nexus-media-ai-backend.onrender.com/',
  });
  assert.equal(result.isConfigured, true);
  assert.equal(result.baseUrl, 'https://nexus-media-ai-backend.onrender.com');
  assert.equal(result.statusLabel, BACKEND_CONNECTED_BANNER);
  assert.equal(result.connectionState, 'Connected');
});

test('FASTAPI_ENDPOINT_REGISTRY documents all required Step 3, Step 4, and Step 5 FastAPI routes', () => {
  const requiredPaths = [
    'GET /api/system/health',
    'GET /api/system/health/database',
    'GET /api/agents',
    'GET /api/agents/orchestrator/status',
    'GET /api/agents/{agent_id}',
    'POST /api/agents/{agent_id}/enable',
    'POST /api/agents/{agent_id}/disable',
    'POST /api/agents/{agent_id}/pause',
    'POST /api/agents/{agent_id}/resume',
    'PATCH /api/agents/{agent_id}/config',
    'GET /api/agents/{agent_id}/history',
    'GET /api/news',
    'GET /api/news/trending',
    'GET /api/news/categories',
    'GET /api/news/sources',
    'GET /api/news/clusters',
    'GET /api/news/collection/status',
    'POST /api/news/scan',
    'POST /api/news/sources',
    'PATCH /api/news/sources/{source_id}',
    'POST /api/news/{news_id}/classify',
    'POST /api/news/{news_id}/archive',
    'GET /api/news/{news_id}',
    'GET /api/articles',
    'GET /api/articles/{article_id}',
    'POST /api/articles',
    'POST /api/articles/{article_id}/approve',
    'POST /api/articles/{article_id}/publish',
    'GET /api/publishing/jobs',
    'GET /api/analytics/traffic',
    'GET /api/analytics/revenue',
    'GET /api/logs',
  ];

  const registered = FASTAPI_ENDPOINT_REGISTRY.map((ep) => `${ep.method} ${ep.path}`);
  for (const route of requiredPaths) {
    assert.ok(registered.includes(route), `Missing required route in frontend client registry: ${route}`);
  }
});

test('nexusApi Step 4 & Step 5 methods return BACKEND NOT CONNECTED when unconfigured without simulating live backend execution', async () => {
  const snap = await nexusApi.probeFastApiBackend();
  assert.equal(snap.backendConnected, false);
  assert.equal(snap.statusLabel, BACKEND_DISCONNECTED_BANNER);

  const enableRes = await nexusApi.enableAgent('agent-trend-scout');
  assert.equal(enableRes.ok, false);
  assert.ok(enableRes.errorMessage?.includes(BACKEND_DISCONNECTED_BANNER));

  const scanRes = await nexusApi.triggerNewsScan({ trigger_source: 'unit_test' });
  assert.equal(scanRes.ok, false);
  assert.ok(scanRes.errorMessage?.includes(BACKEND_DISCONNECTED_BANNER));

  const sourceRes = await nexusApi.createNewsSource({
    name: 'Test RSS Feed',
    endpoint_url: 'https://feeds.reuters.com/reuters/businessNews',
  });
  assert.equal(sourceRes.ok, false);
  assert.ok(sourceRes.errorMessage?.includes(BACKEND_DISCONNECTED_BANNER));
});
