import {
  AIAgent,
  AnalyticsPoint,
  ArticleRecord,
  DateRangeOption,
  KPIMetric,
  PublishingStageMetric,
  SystemConnectionState,
  SystemHealthNode,
} from '../types/dashboard';

/**
 * Toggles an AI agent between Paused and Running/Idle demo state.
 */
export function toggleAgentStatus(agents: AIAgent[], agentId: string): AIAgent[] {
  return agents.map((agent) => {
    if (agent.id !== agentId) return agent;
    const isCurrentlyPaused = agent.status === 'Paused';
    const nextStatus = isCurrentlyPaused ? 'Running' : 'Paused';
    return {
      ...agent,
      status: nextStatus,
      currentTask: isCurrentlyPaused
        ? `Resumed pipeline queue (${agent.role})`
        : 'Execution paused by operator (Demo Mode)',
      lastActivity: 'Just now',
    };
  });
}

/**
 * Toggles an AI agent's enabled/disabled configuration state.
 */
export function toggleAgentEnabled(agents: AIAgent[], agentId: string): AIAgent[] {
  return agents.map((agent) => {
    if (agent.id !== agentId) return agent;
    const currentlyEnabled = agent.enabled !== false;
    const nextEnabled = !currentlyEnabled;
    return {
      ...agent,
      enabled: nextEnabled,
      status: nextEnabled ? 'Idle' : 'Paused',
      currentTask: nextEnabled
        ? `Enabled and standing by (${agent.role})`
        : 'Agent disabled by operator — Orchestrator will not assign tasks',
      lastActivity: 'Just now',
    };
  });
}

/**
 * Updates an AI agent's model, timeout, retries, temperature, and system instructions.
 */
export function updateAgentConfiguration(
  agents: AIAgent[],
  agentId: string,
  updates: {
    enabled?: boolean;
    provider?: string;
    model?: string;
    timeoutSeconds?: number;
    maxRetries?: number;
    temperature?: number;
    systemInstructions?: string;
  }
): AIAgent[] {
  return agents.map((agent) => {
    if (agent.id !== agentId) return agent;
    const nextEnabled = updates.enabled !== undefined ? updates.enabled : agent.enabled !== false;
    return {
      ...agent,
      ...updates,
      enabled: nextEnabled,
      status: nextEnabled ? agent.status : 'Paused',
      lastActivity: 'Config updated just now',
    };
  });
}

/**
 * Computes how many AI agents are currently active (enabled and Running or Idle).
 */
export function computeActiveAgentCount(agents: AIAgent[]): number {
  return agents.filter(
    (a) => a.enabled !== false && (a.status === 'Running' || a.status === 'Idle')
  ).length;
}

/**
 * Computes the 8 KPI metrics dynamically for the selected date range and active agent count.
 */
export function getMetricsForDateRange(
  range: DateRangeOption,
  activeAgents: number,
  totalAgents: number,
  backendConnected?: boolean
): KPIMetric[] {
  if (backendConnected === false) {
    return [
      {
        id: 'kpi-total-articles',
        label: 'Total Articles',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect FastAPI backend to load live count',
        targetNav: 'articles',
      },
      {
        id: 'kpi-published-articles',
        label: 'Published Articles',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect FastAPI backend to load live count',
        targetNav: 'publishing-queue',
      },
      {
        id: 'kpi-news-discovered',
        label: 'News Discovered',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect FastAPI backend to load signals',
        targetNav: 'trending-news',
      },
      {
        id: 'kpi-active-agents',
        label: 'Active AI Agents',
        value: `${activeAgents} / ${totalAgents}`,
        delta: activeAgents === totalAgents ? 'All Nominal' : `${totalAgents - activeAgents} Paused`,
        deltaTrend: activeAgents === totalAgents ? 'up' : 'neutral',
        subtitle: 'Autonomous editorial fleet',
        targetNav: 'ai-agents',
      },
      {
        id: 'kpi-website-views',
        label: 'Total Website Views',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect live analytics telemetry',
        targetNav: 'website-traffic',
      },
      {
        id: 'kpi-social-reach',
        label: 'Social Media Reach',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect live social telemetry',
        targetNav: 'social-reach',
      },
      {
        id: 'kpi-estimated-revenue',
        label: 'Estimated Revenue',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect AdSense/sponsorship telemetry',
        targetNav: 'revenue-analytics',
      },
      {
        id: 'kpi-failed-jobs',
        label: 'Failed Jobs',
        value: 'Not connected',
        delta: 'Offline',
        deltaTrend: 'neutral',
        subtitle: 'Connect publishing queue telemetry',
        targetNav: 'activity-logs',
      },
    ];
  }

  const multiplierMap: Record<DateRangeOption, number> = {
    '24h': 1,
    '7d': 6.4,
    '30d': 26.5,
    '90d': 74.2,
  };
  const m = multiplierMap[range];

  const totalArticles = Math.round(48 * m);
  const publishedArticles = Math.round(34 * m);
  const newsDiscovered = Math.round(312 * m);
  const websiteViews = Math.round(42800 * m);
  const socialReach = Math.round(118400 * m);
  const estimatedRevenue = (642.5 * m).toFixed(2);
  const failedJobs = range === '24h' ? 2 : range === '7d' ? 5 : range === '30d' ? 14 : 29;

  return [
    {
      id: 'kpi-total-articles',
      label: 'Total Articles',
      value: totalArticles.toLocaleString('en-US'),
      delta: '+14.2%',
      deltaTrend: 'up',
      subtitle: `Drafted & queued (${range} demo window)`,
      targetNav: 'articles',
    },
    {
      id: 'kpi-published-articles',
      label: 'Published Articles',
      value: publishedArticles.toLocaleString('en-US'),
      delta: '+11.8%',
      deltaTrend: 'up',
      subtitle: `Verified & live (${range} demo window)`,
      targetNav: 'publishing-queue',
    },
    {
      id: 'kpi-news-discovered',
      label: 'News Discovered',
      value: newsDiscovered.toLocaleString('en-US'),
      delta: '+22.4%',
      deltaTrend: 'up',
      subtitle: 'Ingested wire & RSS signals',
      targetNav: 'trending-news',
    },
    {
      id: 'kpi-active-agents',
      label: 'Active AI Agents',
      value: `${activeAgents} / ${totalAgents}`,
      delta: activeAgents === totalAgents ? 'All Nominal' : `${totalAgents - activeAgents} Paused`,
      deltaTrend: activeAgents === totalAgents ? 'up' : 'neutral',
      subtitle: 'Autonomous editorial fleet',
      targetNav: 'ai-agents',
    },
    {
      id: 'kpi-website-views',
      label: 'Total Website Views',
      value: websiteViews.toLocaleString('en-US'),
      delta: '+18.6%',
      deltaTrend: 'up',
      subtitle: `Simulated traffic (${range} window)`,
      targetNav: 'website-traffic',
    },
    {
      id: 'kpi-social-reach',
      label: 'Social Media Reach',
      value: socialReach.toLocaleString('en-US'),
      delta: '+9.4%',
      deltaTrend: 'up',
      subtitle: 'Cross-channel impressions (Demo)',
      targetNav: 'social-reach',
    },
    {
      id: 'kpi-estimated-revenue',
      label: 'Estimated Revenue',
      value: `$${Number(estimatedRevenue).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      delta: '+7.9%',
      deltaTrend: 'up',
      subtitle: 'Programmatic display & syndication',
      targetNav: 'revenue-analytics',
    },
    {
      id: 'kpi-failed-jobs',
      label: 'Failed Jobs',
      value: String(failedJobs),
      delta: '-31.0%',
      deltaTrend: 'up',
      subtitle: 'Dead-letter & timeout retries',
      targetNav: 'activity-logs',
    },
  ];
}

/**
 * Cycles or updates a System Health node's status for interactive testing.
 */
export function updateHealthNodeStatus(
  nodes: SystemHealthNode[],
  nodeId: string,
  nextStatus: SystemConnectionState
): SystemHealthNode[] {
  return nodes.map((node) => {
    if (node.id !== nodeId) return node;
    return {
      ...node,
      status: nextStatus,
      latencyMs: nextStatus === 'Connected' ? 18 : nextStatus === 'Checking' ? null : null,
      lastChecked: 'Updated just now',
    };
  });
}

/**
 * Calculates total items and completion ratios across publishing stages.
 */
export function calculatePublishingTotals(stages: PublishingStageMetric[]): {
  total: number;
  publishedRatioPct: number;
} {
  const total = stages.reduce((acc, item) => acc + item.count, 0);
  if (total === 0) return { total: 0, publishedRatioPct: 0 };
  const published = stages.find((s) => s.stage === 'Published')?.count ?? 0;
  return {
    total,
    publishedRatioPct: Math.round((published / total) * 100),
  };
}

/**
 * Validates an article draft in the interactive Article Editor.
 */
export function validateArticleDraft(draft: {
  headline: string;
  category: string;
  body: string;
  primarySourceUrl: string;
}): { valid: boolean; errors: string[]; wordCount: number; estimatedSeoScore: number } {
  const errors: string[] = [];
  const trimmedHeadline = draft.headline.trim();
  const trimmedBody = draft.body.trim();
  const words = trimmedBody ? trimmedBody.split(/\s+/).length : 0;

  if (trimmedHeadline.length < 12) {
    errors.push('Headline must be at least 12 characters for editorial clarity.');
  }
  if (!draft.category.trim()) {
    errors.push('Select an editorial sector category.');
  }
  if (words < 20) {
    errors.push(`Article body requires at least 20 words (currently ${words}).`);
  }
  if (!draft.primarySourceUrl.trim().startsWith('https://')) {
    errors.push('Primary verification source URL must start with https://');
  }

  let seo = 55;
  if (trimmedHeadline.length >= 35 && trimmedHeadline.length <= 75) seo += 18;
  if (words >= 80) seo += 15;
  if (draft.primarySourceUrl.startsWith('https://')) seo += 10;

  return {
    valid: errors.length === 0,
    errors,
    wordCount: words,
    estimatedSeoScore: Math.min(98, seo),
  };
}

/**
 * Filters articles by search query and stage.
 */
export function filterArticles(
  articles: ArticleRecord[],
  query: string,
  stageFilter: string
): ArticleRecord[] {
  const q = query.trim().toLowerCase();
  return articles.filter((art) => {
    const matchesStage = stageFilter === 'ALL' || art.stage === stageFilter;
    const matchesQuery =
      !q ||
      art.headline.toLowerCase().includes(q) ||
      art.category.toLowerCase().includes(q) ||
      art.authorAgent.toLowerCase().includes(q);
    return matchesStage && matchesQuery;
  });
}

/**
 * Computes summary totals for Analytics Preview charts.
 */
export function summarizeAnalyticsSeries(series: AnalyticsPoint[]): {
  totalViews: number;
  totalArticles: number;
  totalReach: number;
  totalRevenue: number;
} {
  return series.reduce(
    (acc, pt) => ({
      totalViews: acc.totalViews + pt.websiteViews,
      totalArticles: acc.totalArticles + pt.articlesPublished,
      totalReach: acc.totalReach + pt.socialReach,
      totalRevenue: Math.round((acc.totalRevenue + pt.revenueUsd) * 100) / 100,
    }),
    { totalViews: 0, totalArticles: 0, totalReach: 0, totalRevenue: 0 }
  );
}
