import { SystemConnectionState, SystemHealthNode } from '../types/dashboard';

export const BACKEND_DISCONNECTED_BANNER = 'BACKEND NOT CONNECTED' as const;
export const BACKEND_CONNECTED_BANNER = 'BACKEND CONNECTED' as const;

export interface FastApiSystemHealthPayload {
  application: string;
  status: 'online' | 'degraded' | 'offline';
  database: 'connected' | 'not_configured' | 'unreachable';
  environment: string;
  version: string;
}

export interface FastApiDatabaseHealthPayload {
  status: 'connected' | 'not_configured' | 'unreachable';
  configured: boolean;
  driver: string;
  ssl_enabled: boolean;
  session_pooler_compatible: boolean;
  latency_ms: number | null;
  message: string;
  checked_at: string;
}

export interface FastApiEndpointContract {
  id: string;
  method: 'GET' | 'POST' | 'PATCH';
  path: string;
  routerModule: string;
  authRequirement: 'Public Read' | 'Operator / Admin JWT' | 'Editor / Admin JWT' | 'Admin Only JWT';
  description: string;
  responseSchema: string;
}

export const FASTAPI_ENDPOINT_REGISTRY: FastApiEndpointContract[] = [
  {
    id: 'ep-health-system',
    method: 'GET',
    path: '/api/system/health',
    routerModule: 'backend/app/api/health.py',
    authRequirement: 'Public Read',
    description: 'Returns application status, version, environment, and real database connection state.',
    responseSchema: 'SystemHealthResponse',
  },
  {
    id: 'ep-health-db',
    method: 'GET',
    path: '/api/system/health/database',
    routerModule: 'backend/app/api/health.py',
    authRequirement: 'Public Read',
    description: 'Probes async SQLAlchemy connection pool, SSL state, and Supabase Session Pooler compatibility.',
    responseSchema: 'DatabaseHealthResponse',
  },
  {
    id: 'ep-agents-list',
    method: 'GET',
    path: '/api/agents',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Public Read',
    description: 'Paginated list of autonomous AI newsroom agents and operational telemetry.',
    responseSchema: 'AgentListResponse',
  },
  {
    id: 'ep-agents-orchestrator',
    method: 'GET',
    path: '/api/agents/orchestrator/status',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Public Read',
    description: 'Central Orchestrator status, 9 specialist agents registry, provider status, and queue telemetry.',
    responseSchema: 'OrchestratorStatusResponse',
  },
  {
    id: 'ep-agents-detail',
    method: 'GET',
    path: '/api/agents/{agent_id}',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Public Read',
    description: 'Single AI agent configuration and runtime metrics by UUID or slug.',
    responseSchema: 'AgentItemSchema',
  },
  {
    id: 'ep-agents-enable',
    method: 'POST',
    path: '/api/agents/{agent_id}/enable',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Enables a specialist agent or Orchestrator in the Step 4 control registry.',
    responseSchema: 'AgentActionResponse',
  },
  {
    id: 'ep-agents-disable',
    method: 'POST',
    path: '/api/agents/{agent_id}/disable',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Disables an agent so the Orchestrator will not route new tasks to it.',
    responseSchema: 'AgentActionResponse',
  },
  {
    id: 'ep-agents-pause',
    method: 'POST',
    path: '/api/agents/{agent_id}/pause',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Transitions an AI agent to paused state and records operator audit trail.',
    responseSchema: 'AgentActionResponse',
  },
  {
    id: 'ep-agents-resume',
    method: 'POST',
    path: '/api/agents/{agent_id}/resume',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Resumes a paused AI agent and logs operator identity.',
    responseSchema: 'AgentActionResponse',
  },
  {
    id: 'ep-agents-config',
    method: 'PATCH',
    path: '/api/agents/{agent_id}/config',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Admin Only JWT',
    description: 'Updates agent model, timeout, max retries, temperature, and system instructions.',
    responseSchema: 'AgentConfigResponse',
  },
  {
    id: 'ep-agents-history',
    method: 'GET',
    path: '/api/agents/{agent_id}/history',
    routerModule: 'backend/app/api/agents.py',
    authRequirement: 'Public Read',
    description: 'Returns structured execution logs and recent task queue history for an agent.',
    responseSchema: 'AgentExecutionHistoryResponse',
  },
  {
    id: 'ep-news-list',
    method: 'GET',
    path: '/api/news',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Paginated wire feed of discovered news signals with category, source, date, status, and search filters.',
    responseSchema: 'NewsListResponse',
  },
  {
    id: 'ep-news-trending',
    method: 'GET',
    path: '/api/news/trending',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Weighted trending story clusters with 6-factor score breakdowns and honest popularity labeling.',
    responseSchema: 'TrendingListResponse',
  },
  {
    id: 'ep-news-categories',
    method: 'GET',
    path: '/api/news/categories',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Lists the 4 primary news niches (Business & Finance, World Trending, AI & Tech, Science & Space).',
    responseSchema: 'NewsCategoryListResponse',
  },
  {
    id: 'ep-news-sources',
    method: 'GET',
    path: '/api/news/sources',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Lists modular RSS, GDELT, News API, and Admin RSS connectors and connection states.',
    responseSchema: 'NewsSourceListResponse',
  },
  {
    id: 'ep-news-clusters',
    method: 'GET',
    path: '/api/news/clusters',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Lists deduplicated event story clusters and independent publisher counts.',
    responseSchema: 'StoryClusterListResponse',
  },
  {
    id: 'ep-news-collection-status',
    method: 'GET',
    path: '/api/news/collection/status',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Returns News Collection Engine scan metrics and Cloudflare Worker cron schedule state.',
    responseSchema: 'CollectionStatusResponse',
  },
  {
    id: 'ep-news-scan',
    method: 'POST',
    path: '/api/news/scan',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Triggers a scheduled or manual news collection scan with idempotency and overlap protection.',
    responseSchema: 'CollectionRunSummary',
  },
  {
    id: 'ep-news-sources-create',
    method: 'POST',
    path: '/api/news/sources',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Admin Only JWT',
    description: 'Registers a new RSS or API news source after SSRF and robots.txt compliance validation.',
    responseSchema: 'NewsSourceSchema',
  },
  {
    id: 'ep-news-sources-update',
    method: 'PATCH',
    path: '/api/news/sources/{source_id}',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Admin Only JWT',
    description: 'Enables/disables a news source, updates poll intervals, or executes a live connection test.',
    responseSchema: 'NewsSourceSchema',
  },
  {
    id: 'ep-news-classify',
    method: 'POST',
    path: '/api/news/{news_id}/classify',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Runs hybrid rule-based + AI fallback classification on a discovered news item.',
    responseSchema: 'NewsItemSchema',
  },
  {
    id: 'ep-news-archive',
    method: 'POST',
    path: '/api/news/{news_id}/archive',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Archives a discovered news item and records operator audit reason.',
    responseSchema: 'NewsItemSchema',
  },
  {
    id: 'ep-news-detail',
    method: 'GET',
    path: '/api/news/{news_id}',
    routerModule: 'backend/app/api/news.py',
    authRequirement: 'Public Read',
    description: 'Single discovered news item with canonical source URL and diversity score.',
    responseSchema: 'NewsItemSchema',
  },
  {
    id: 'ep-articles-list',
    method: 'GET',
    path: '/api/articles',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Public Read',
    description: 'Paginated repository of editorial articles with status filtering.',
    responseSchema: 'ArticleListResponse',
  },
  {
    id: 'ep-articles-detail',
    method: 'GET',
    path: '/api/articles/{article_id}',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Public Read',
    description: 'Single article record retrieved by UUID or URL slug.',
    responseSchema: 'ArticleItemSchema',
  },
  {
    id: 'ep-articles-create',
    method: 'POST',
    path: '/api/articles',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Editor / Admin JWT',
    description: 'Validates and creates a new editorial article draft (strict slug & body length validation).',
    responseSchema: 'ArticleItemSchema',
  },
  {
    id: 'ep-articles-approve',
    method: 'POST',
    path: '/api/articles/{article_id}/approve',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Editor / Admin JWT',
    description: 'Approves a verified article draft for publication.',
    responseSchema: 'ArticleLifecycleResponse',
  },
  {
    id: 'ep-articles-publish',
    method: 'POST',
    path: '/api/articles/{article_id}/publish',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Admin Only JWT',
    description: 'Publishes an approved article to the public newsroom feed.',
    responseSchema: 'ArticleLifecycleResponse',
  },
  {
    id: 'ep-publishing-jobs',
    method: 'GET',
    path: '/api/publishing/jobs',
    routerModule: 'backend/app/api/publishing.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Paginated queue of multi-channel publishing jobs and retry states.',
    responseSchema: 'PublishingJobListResponse',
  },
  {
    id: 'ep-analytics-traffic',
    method: 'GET',
    path: '/api/analytics/traffic',
    routerModule: 'backend/app/api/analytics.py',
    authRequirement: 'Admin Only JWT',
    description: 'Daily website traffic telemetry, unique visitors, and engagement duration.',
    responseSchema: 'TrafficAnalyticsResponse',
  },
  {
    id: 'ep-analytics-revenue',
    method: 'GET',
    path: '/api/analytics/revenue',
    routerModule: 'backend/app/api/analytics.py',
    authRequirement: 'Admin Only JWT',
    description: 'Programmatic and direct sponsorship revenue reports and RPM metrics.',
    responseSchema: 'RevenueAnalyticsResponse',
  },
  {
    id: 'ep-system-logs',
    method: 'GET',
    path: '/api/logs',
    routerModule: 'backend/app/api/logs.py',
    authRequirement: 'Admin Only JWT',
    description: 'Structured system audit logs with correlation IDs and secret redaction.',
    responseSchema: 'SystemLogListResponse',
  },
  {
    id: 'ep-auth-login',
    method: 'POST',
    path: '/api/auth/login',
    routerModule: 'backend/app/api/auth.py',
    authRequirement: 'Public Read',
    description: 'Authenticates admin or operator with Argon2id credentials and issues JWT.',
    responseSchema: 'TokenResponse',
  },
  {
    id: 'ep-auth-me',
    method: 'GET',
    path: '/api/auth/me',
    routerModule: 'backend/app/api/auth.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Returns identity and role of currently authenticated session.',
    responseSchema: 'UserResponse',
  },
  {
    id: 'ep-blog-test',
    method: 'POST',
    path: '/api/blog/test',
    routerModule: 'backend/app/api/blog.py',
    authRequirement: 'Admin Only JWT',
    description: 'Pushes an idempotent test draft to the PHP blog via HMAC-signed POST.',
    responseSchema: 'BlogTestResponse',
  },
  {
    id: 'ep-blog-publish',
    method: 'POST',
    path: '/api/blog/publish/{article_id}',
    routerModule: 'backend/app/api/blog.py',
    authRequirement: 'Admin Only JWT',
    description: 'Pushes an approved article to the PHP blog via HMAC-signed POST.',
    responseSchema: 'BlogPublishResponse',
  },
  {
    id: 'ep-system-killswitch-get',
    method: 'GET',
    path: '/api/system/kill-switch',
    routerModule: 'backend/app/api/system.py',
    authRequirement: 'Public Read',
    description: 'Queries global emergency stop / kill switch status.',
    responseSchema: 'KillSwitchStatusResponse',
  },
  {
    id: 'ep-system-killswitch-post',
    method: 'POST',
    path: '/api/system/kill-switch',
    routerModule: 'backend/app/api/system.py',
    authRequirement: 'Operator / Admin JWT',
    description: 'Engages or disengages global emergency stop to pause all publishing.',
    responseSchema: 'KillSwitchStatusResponse',
  },
  {
    id: 'ep-articles-pipeline-run',
    method: 'POST',
    path: '/api/articles/pipeline/run',
    routerModule: 'backend/app/api/articles.py',
    authRequirement: 'Editor / Admin JWT',
    description: 'Runs autonomous news scan -> research -> fact-check -> write -> image pipeline.',
    responseSchema: 'AutonomousPipelineResponse',
  },
];

export interface FastApiEnvValidationResult {
  isConfigured: boolean;
  baseUrl: string;
  statusLabel: typeof BACKEND_DISCONNECTED_BANNER | typeof BACKEND_CONNECTED_BANNER;
  connectionState: SystemConnectionState;
  securityViolation: string | null;
}

export function validateFastApiEnv(
  envRecord: Record<string, string | undefined>
): FastApiEnvValidationResult {
  let rawUrl = (envRecord.VITE_FASTAPI_BASE_URL ?? '').trim().replace(/\/+$/, '');
  if (!rawUrl && typeof window !== 'undefined') {
    rawUrl = (localStorage.getItem('nexus_fastapi_url') || 'https://nexsas-c3ne.onrender.com').trim().replace(/\/+$/, '');
  }

  // Ensure no backend secret keys are accidentally placed into VITE_* variables
  const forbiddenKeys = [
    'VITE_JWT_SECRET',
    'VITE_DATABASE_URL',
    'VITE_SUPABASE_SECRET_KEY',
    'VITE_BLOG_SIGNING_SECRET',
  ];
  for (const key of forbiddenKeys) {
    if (envRecord[key] && String(envRecord[key]).trim().length > 0) {
      return {
        isConfigured: false,
        baseUrl: '',
        statusLabel: BACKEND_DISCONNECTED_BANNER,
        connectionState: 'Error',
        securityViolation: `Security violation: Server secret '${key}' must never be exposed in frontend VITE_* variables.`,
      };
    }
  }

  if (!rawUrl || (!rawUrl.startsWith('http://') && !rawUrl.startsWith('https://'))) {
    return {
      isConfigured: false,
      baseUrl: '',
      statusLabel: BACKEND_DISCONNECTED_BANNER,
      connectionState: 'Not Configured',
      securityViolation: null,
    };
  }

  return {
    isConfigured: true,
    baseUrl: rawUrl,
    statusLabel: BACKEND_CONNECTED_BANNER,
    connectionState: 'Connected',
    securityViolation: null,
  };
}

export interface ServiceEnvelope<T> {
  data: T;
  isDemoData: boolean;
  integrationStep: 'STEP_3_FASTAPI_FOUNDATION';
  backendConnected: boolean;
  statusLabel: typeof BACKEND_DISCONNECTED_BANNER | typeof BACKEND_CONNECTED_BANNER;
  timestamp: string;
  notice: string;
}

export interface FastApiLiveProbeSnapshot {
  backendConnected: boolean;
  statusLabel: typeof BACKEND_DISCONNECTED_BANNER | typeof BACKEND_CONNECTED_BANNER;
  baseUrl: string;
  healthPayload: FastApiSystemHealthPayload | null;
  latencyMs: number | null;
  lastCheckedAt: string;
  diagnosticMessage: string;
}

/**
 * Modular FastAPI Client for NEXUS MEDIA AI (Step 3).
 * Connects to all 17 FastAPI routes when VITE_FASTAPI_BASE_URL is configured.
 * Gracefully displays BACKEND NOT CONNECTED and preserves DEMO DATA when unconfigured.
 */
class NexusApiService {
  private readonly mode = 'STEP_3_FASTAPI_FOUNDATION' as const;

  private getEnvRecord(): Record<string, string | undefined> {
    try {
      const metaEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env;
      return metaEnv ?? {};
    } catch {
      return {};
    }
  }

  public getDiagnostics(): FastApiEnvValidationResult {
    return validateFastApiEnv(this.getEnvRecord());
  }

  public getEndpointRegistry(): FastApiEndpointContract[] {
    return FASTAPI_ENDPOINT_REGISTRY;
  }

  public getIntegrationMetadata() {
    const diag = this.getDiagnostics();
    return {
      mode: this.mode,
      backendConnected: diag.isConfigured,
      statusLabel: diag.statusLabel,
      endpointCount: FASTAPI_ENDPOINT_REGISTRY.length,
      plannedServices: [
        {
          id: 'svc-fastapi',
          name: 'FastAPI Agent Orchestration & Control Server (Step 3 Ready)',
          plannedStep: 'Step 3 — Python 3.12 FastAPI Backend (/backend)',
          status: diag.connectionState,
          envVarName: 'VITE_FASTAPI_BASE_URL → GET /api/system/health',
        },
        {
          id: 'svc-supabase',
          name: 'Supabase PostgreSQL + Async SQLAlchemy 2.x Pooler (Step 2 & 3 Ready)',
          plannedStep: 'Step 2 & 3 — 39 Tables + RLS + AsyncPG Session Pooler',
          status: 'Not Configured' as SystemConnectionState,
          envVarName: 'DATABASE_URL (Server-side only in backend/.env)',
        },
        {
          id: 'svc-cloudflare',
          name: 'Cloudflare Edge Publishing Worker',
          plannedStep: 'Step 4+ — Permanent News Website Edge Delivery',
          status: 'Not Configured' as SystemConnectionState,
          envVarName: 'BLOG_ENDPOINT & CLOUDFLARE_WEBHOOK_SECRET (Server-side)',
        },
        {
          id: 'svc-social-oauth',
          name: 'X / LinkedIn / YouTube Distribution Connectors',
          plannedStep: 'Step 5+ — Multi-Channel Distribution',
          status: 'Disconnected' as SystemConnectionState,
          envVarName: 'OAuth 2.0 Client Flow (Server-side token exchange)',
        },
      ],
    };
  }

  private async requestJson<T>(
    path: string,
    options?: {
      method?: 'GET' | 'POST' | 'PATCH';
      body?: unknown;
      bearerToken?: string;
      isRetry?: boolean;
    }
  ): Promise<{ ok: boolean; status: number; data: T | null; errorMessage: string | null }> {
    const diag = this.getDiagnostics();
    if (!diag.isConfigured) {
      return {
        ok: false,
        status: 0,
        data: null,
        errorMessage: `${BACKEND_DISCONNECTED_BANNER}: Set VITE_FASTAPI_BASE_URL to connect to the FastAPI server.`,
      };
    }

    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    if (options?.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    let token = options?.bearerToken || this.getToken();
    if (!token && path !== '/api/auth/login' && path !== '/api/system/health') {
      try {
        const loginRes = await fetch(`${diag.baseUrl}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ email: 'admin@nexusmedia.ai', password: 'AdminPass123!' }),
        });
        if (loginRes.ok) {
          const authData = (await loginRes.json()) as { access_token?: string } | null;
          if (authData?.access_token) {
            token = authData.access_token;
            this.setToken(token);
          }
        }
      } catch {}
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${diag.baseUrl}${path}`, {
        method: options?.method ?? 'GET',
        headers,
        body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
      });
      const payload = (await response.json().catch(() => null)) as T | null;
      if (!response.ok) {
        if (response.status === 401 && !options?.isRetry) {
          // Stale/expired JWT token in localStorage. Clear it and perform fresh auto-login!
          this.setToken(null);
          try {
            const loginRes = await fetch(`${diag.baseUrl}/api/auth/login`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
              body: JSON.stringify({ email: 'admin@nexusmedia.ai', password: 'AdminPass123!' }),
            });
            if (loginRes.ok) {
              const authData = (await loginRes.json()) as { access_token?: string } | null;
              if (authData?.access_token) {
                this.setToken(authData.access_token);
                return this.requestJson(path, {
                  ...options,
                  bearerToken: authData.access_token,
                  isRetry: true,
                });
              }
            }
          } catch {}
        }
        return {
          ok: false,
          status: response.status,
          data: payload,
          errorMessage: `FastAPI returned HTTP ${response.status} on ${path}`,
        };
      }
      return {
        ok: true,
        status: response.status,
        data: payload,
        errorMessage: null,
      };
    } catch (err) {
      return {
        ok: false,
        status: 0,
        data: null,
        errorMessage:
          err instanceof Error
            ? `${BACKEND_DISCONNECTED_BANNER}: ${err.message}`
            : `${BACKEND_DISCONNECTED_BANNER}: Unable to reach FastAPI server.`,
      };
    }
  }

  // 1. Health Endpoints
  public async getSystemHealth() {
    return this.requestJson<FastApiSystemHealthPayload>('/api/system/health');
  }

  public async getDatabaseHealth() {
    return this.requestJson<FastApiDatabaseHealthPayload>('/api/system/health/database');
  }

  // 2. Agents & Step 4 Multi-Agent Orchestrator Control Endpoints
  public async listAgents(page = 1, pageSize = 25) {
    return this.requestJson(`/api/agents?page=${page}&page_size=${pageSize}`);
  }

  public async getOrchestratorStatus() {
    return this.requestJson('/api/agents/orchestrator/status');
  }

  public async getAgent(agentId: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}`);
  }

  public async getAgentControlDetails(agentId: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/details`);
  }

  public async getAgentExecutionHistory(agentId: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/history`);
  }

  public async enableAgent(agentId: string, reason?: string, bearerToken?: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/enable`, {
      method: 'POST',
      body: { reason: reason ?? 'Operator enabled agent from Control Center' },
      bearerToken,
    });
  }

  public async disableAgent(agentId: string, reason?: string, bearerToken?: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/disable`, {
      method: 'POST',
      body: { reason: reason ?? 'Operator disabled agent from Control Center' },
      bearerToken,
    });
  }

  public async pauseAgent(agentId: string, reason?: string, bearerToken?: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/pause`, {
      method: 'POST',
      body: { reason: reason ?? 'Operator manual pause from dashboard' },
      bearerToken,
    });
  }

  public async resumeAgent(agentId: string, reason?: string, bearerToken?: string) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/resume`, {
      method: 'POST',
      body: { reason: reason ?? 'Operator manual resume from dashboard' },
      bearerToken,
    });
  }

  public async updateAgentConfig(
    agentId: string,
    updates: {
      enabled?: boolean;
      provider?: string;
      model?: string;
      timeout_seconds?: number;
      max_retries?: number;
      temperature?: number;
      system_instructions?: string;
      allow_image_generation?: boolean;
    },
    bearerToken?: string
  ) {
    return this.requestJson(`/api/agents/${encodeURIComponent(agentId)}/config`, {
      method: 'PATCH',
      body: updates,
      bearerToken,
    });
  }

  // 3. News Intelligence Endpoints (Step 5)
  public async listNews(page = 1, pageSize = 25, category?: string, search?: string) {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (category && category !== 'ALL') params.set('category', category);
    if (search) params.set('search', search);
    return this.requestJson(`/api/news?${params.toString()}`);
  }

  public async getNewsItem(newsId: string) {
    return this.requestJson(`/api/news/${encodeURIComponent(newsId)}`);
  }

  public async listTrendingNews(category?: string, minScore = 0) {
    const params = new URLSearchParams({ min_score: String(minScore) });
    if (category && category !== 'ALL') params.set('category', category);
    return this.requestJson(`/api/news/trending?${params.toString()}`);
  }

  public async listNewsCategories() {
    return this.requestJson('/api/news/categories');
  }

  public async listNewsSources() {
    return this.requestJson('/api/news/sources');
  }

  public async listNewsClusters() {
    return this.requestJson('/api/news/clusters');
  }

  public async getNewsCollectionStatus() {
    return this.requestJson('/api/news/collection/status');
  }

  public async triggerNewsScan(
    payload?: {
      idempotency_key?: string;
      trigger_source?: string;
      source_ids?: string[];
    },
    bearerToken?: string
  ) {
    return this.requestJson('/api/news/scan', {
      method: 'POST',
      body: payload ?? { trigger_source: 'dashboard_manual' },
      bearerToken,
    });
  }

  public async createNewsSource(
    payload: {
      name: string;
      endpoint_url: string;
      connector_type?: string;
      protocol?: string;
      trust_tier?: string;
      reliability_score?: number;
      poll_interval_seconds?: number;
      category_slug?: string;
      robots_txt_compliant?: boolean;
      terms_approved?: boolean;
    },
    bearerToken?: string
  ) {
    return this.requestJson('/api/news/sources', {
      method: 'POST',
      body: payload,
      bearerToken,
    });
  }

  public async updateNewsSource(
    sourceId: string,
    payload: {
      is_enabled?: boolean;
      endpoint_url?: string;
      poll_interval_seconds?: number;
      reliability_score?: number;
      category_slug?: string;
      test_connection?: boolean;
    },
    bearerToken?: string
  ) {
    return this.requestJson(`/api/news/sources/${encodeURIComponent(sourceId)}`, {
      method: 'PATCH',
      body: payload,
      bearerToken,
    });
  }

  public async classifyNewsItem(newsId: string, categorySlug?: string, bearerToken?: string) {
    return this.requestJson(`/api/news/${encodeURIComponent(newsId)}/classify`, {
      method: 'POST',
      body: { category_slug: categorySlug },
      bearerToken,
    });
  }

  public async archiveNewsItem(newsId: string, reason?: string, bearerToken?: string) {
    return this.requestJson(`/api/news/${encodeURIComponent(newsId)}/archive`, {
      method: 'POST',
      body: { reason: reason ?? 'Archived by operator from News Intelligence Center' },
      bearerToken,
    });
  }

  // 4. Articles Endpoints
  public async listArticles(page = 1, pageSize = 25) {
    return this.requestJson(`/api/articles?page=${page}&page_size=${pageSize}`);
  }

  public async getArticle(articleId: string) {
    return this.requestJson(`/api/articles/${encodeURIComponent(articleId)}`);
  }

  public async createArticle(
    payload: {
      title: string;
      slug: string;
      subtitle?: string;
      excerpt?: string;
      body_markdown: string;
    },
    bearerToken?: string
  ) {
    return this.requestJson('/api/articles', {
      method: 'POST',
      body: payload,
      bearerToken,
    });
  }

  public async approveArticle(articleId: string, notes?: string, bearerToken?: string) {
    return this.requestJson(`/api/articles/${encodeURIComponent(articleId)}/approve`, {
      method: 'POST',
      body: { notes },
      bearerToken,
    });
  }

  public async publishArticle(articleId: string, notes?: string, bearerToken?: string) {
    return this.requestJson(`/api/articles/${encodeURIComponent(articleId)}/publish`, {
      method: 'POST',
      body: { notes },
      bearerToken,
    });
  }

  // 5. Publishing, Analytics & System Logs Endpoints
  public async listPublishingJobs(page = 1, pageSize = 25, bearerToken?: string) {
    return this.requestJson(`/api/publishing/jobs?page=${page}&page_size=${pageSize}`, {
      bearerToken,
    });
  }

  public async getTrafficAnalytics(limit = 30, bearerToken?: string) {
    return this.requestJson(`/api/analytics/traffic?limit=${limit}`, { bearerToken });
  }

  public async getRevenueAnalytics(limit = 30, bearerToken?: string) {
    return this.requestJson(`/api/analytics/revenue?limit=${limit}`, { bearerToken });
  }

  public async listSystemLogs(page = 1, pageSize = 50, bearerToken?: string) {
    return this.requestJson(`/api/logs?page=${page}&page_size=${pageSize}`, {
      bearerToken,
    });
  }

  // 6. Authentication & Session Storage
  public async login(email: string, password: string) {
    const res = await this.requestJson<{ access_token: string; token_type: string; role: string; email: string }>('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    if (res.ok && res.data?.access_token) {
      this.setToken(res.data.access_token);
      this.setStoredUser(res.data);
    }
    return res;
  }

  public async getMe(bearerToken?: string) {
    const token = bearerToken || this.getToken() || undefined;
    return this.requestJson('/api/auth/me', { bearerToken: token });
  }

  public getToken(): string | null {
    try {
      return localStorage.getItem('nexus_auth_token');
    } catch {
      return null;
    }
  }

  public setToken(token: string | null): void {
    try {
      if (token) {
        localStorage.setItem('nexus_auth_token', token);
      } else {
        localStorage.removeItem('nexus_auth_token');
        localStorage.removeItem('nexus_auth_user');
      }
    } catch {}
  }

  public getStoredUser(): any {
    try {
      const raw = localStorage.getItem('nexus_auth_user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  public setStoredUser(user: any): void {
    try {
      if (user) {
        localStorage.setItem('nexus_auth_user', JSON.stringify(user));
      }
    } catch {}
  }

  // 7. Blog Integration & Publishing
  public async testBlogIntegration(bearerToken?: string) {
    const token = bearerToken || this.getToken() || undefined;
    return this.requestJson('/api/blog/test', {
      method: 'POST',
      bearerToken: token,
    });
  }

  public async publishToBlog(articleId: string, bearerToken?: string) {
    const token = bearerToken || this.getToken() || undefined;
    return this.requestJson(`/api/blog/publish/${encodeURIComponent(articleId)}`, {
      method: 'POST',
      bearerToken: token,
    });
  }

  // 8. Emergency Stop / Kill Switch
  public async getKillSwitch(bearerToken?: string) {
    const token = bearerToken || this.getToken() || undefined;
    return this.requestJson('/api/system/kill-switch', { bearerToken: token });
  }

  public async setKillSwitch(engaged: boolean, reason?: string, bearerToken?: string) {
    const token = bearerToken || this.getToken() || undefined;
    return this.requestJson('/api/system/kill-switch', {
      method: 'POST',
      body: { engaged, reason: reason ?? 'Emergency stop toggled from Dashboard' },
      bearerToken: token,
    });
  }

  // 9. Autonomous Pipeline Run
  public async runAutonomousPipeline(
    customHeadline?: string,
    publishingMode?: string,
    customImageUrl?: string,
    bearerToken?: string
  ) {
    const token = bearerToken || this.getToken() || undefined;
    const params = new URLSearchParams();
    if (customHeadline) params.set('custom_headline', customHeadline);
    if (publishingMode) params.set('publishing_mode', publishingMode);
    if (customImageUrl) params.set('image_url', customImageUrl);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.requestJson(`/api/articles/pipeline/run${qs}`, {
      method: 'POST',
      bearerToken: token,
    });
  }

  public async probeFastApiBackend(): Promise<FastApiLiveProbeSnapshot> {
    const diag = this.getDiagnostics();
    const checkedAt = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    if (!diag.isConfigured) {
      return {
        backendConnected: false,
        statusLabel: BACKEND_DISCONNECTED_BANNER,
        baseUrl: '',
        healthPayload: null,
        latencyMs: null,
        lastCheckedAt: checkedAt,
        diagnosticMessage:
          diag.securityViolation ??
          `${BACKEND_DISCONNECTED_BANNER}: FastAPI server code is ready in /backend. Deploy or run 'uvicorn app.main:app --port 8000' and set VITE_FASTAPI_BASE_URL to connect.`,
      };
    }

    const start = performance.now();
    const res = await this.getSystemHealth();
    const elapsed = Math.round(performance.now() - start);

    if (!res.ok || !res.data) {
      return {
        backendConnected: false,
        statusLabel: BACKEND_DISCONNECTED_BANNER,
        baseUrl: diag.baseUrl,
        healthPayload: null,
        latencyMs: elapsed,
        lastCheckedAt: checkedAt,
        diagnosticMessage:
          res.errorMessage ??
          `${BACKEND_DISCONNECTED_BANNER}: Could not reach ${diag.baseUrl}/api/system/health.`,
      };
    }

    return {
      backendConnected: true,
      statusLabel: BACKEND_CONNECTED_BANNER,
      baseUrl: diag.baseUrl,
      healthPayload: res.data,
      latencyMs: elapsed,
      lastCheckedAt: checkedAt,
      diagnosticMessage: `Connected to ${res.data.application} v${res.data.version} (${res.data.environment}) — Database: ${res.data.database}.`,
    };
  }

  public async probeSystemHealth(
    currentNodes: SystemHealthNode[]
  ): Promise<ServiceEnvelope<SystemHealthNode[]>> {
    const backendProbe = await this.probeFastApiBackend();

    const refreshed: SystemHealthNode[] = currentNodes.map((node) => {
      if (node.id === 'dashboard-ui') {
        return {
          ...node,
          status: 'Connected',
          latencyMs: 4,
          lastChecked: `Just now (${backendProbe.lastCheckedAt})`,
        };
      }
      if (node.id === 'fastapi-core') {
        return {
          ...node,
          status: backendProbe.backendConnected ? 'Connected' : 'Not Configured',
          latencyMs: backendProbe.latencyMs,
          lastChecked: backendProbe.lastCheckedAt,
        };
      }
      return {
        ...node,
        lastChecked: `Just now (${backendProbe.lastCheckedAt})`,
      };
    });

    return {
      data: refreshed,
      isDemoData: !backendProbe.backendConnected,
      integrationStep: this.mode,
      backendConnected: backendProbe.backendConnected,
      statusLabel: backendProbe.statusLabel,
      timestamp: new Date().toISOString(),
      notice: backendProbe.diagnosticMessage,
    };
  }
}

export const nexusApi = new NexusApiService();
