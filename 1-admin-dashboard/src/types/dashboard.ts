export type NavPageId =
  | 'dashboard'
  | 'system-health'
  | 'trending-news'
  | 'news-sources'
  | 'research-center'
  | 'fact-checking'
  | 'articles'
  | 'article-editor'
  | 'seo-analysis'
  | 'media-library'
  | 'ai-agents'
  | 'workflow-manager'
  | 'publishing-queue'
  | 'scheduler'
  | 'social-accounts'
  | 'social-publishing'
  | 'youtube-publishing'
  | 'website-traffic'
  | 'social-reach'
  | 'revenue-analytics'
  | 'api-connections'
  | 'database-status'
  | 'activity-logs'
  | 'settings';

export type NavSectionName =
  | 'Overview'
  | 'Intelligence'
  | 'Content'
  | 'Automation'
  | 'Distribution'
  | 'Analytics'
  | 'System';

export interface NavItem {
  id: NavPageId;
  label: string;
  section: NavSectionName;
  description: string;
}

export type DateRangeOption = '24h' | '7d' | '30d' | '90d';

export type SystemConnectionState =
  | 'Connected'
  | 'Disconnected'
  | 'Checking'
  | 'Error'
  | 'Not Configured';

export interface SystemHealthNode {
  id: string;
  name: string;
  category: string;
  status: SystemConnectionState;
  endpointOrTarget: string;
  latencyMs: number | null;
  lastChecked: string;
  note: string;
}

export type AgentExecutionStatus = 'Running' | 'Idle' | 'Paused' | 'Standby';

export interface AgentExecutionLogEntry {
  taskId: string;
  stageName: string;
  status: 'completed' | 'failed' | 'cancelled' | 'dead_letter' | 'not_connected';
  startedAt: string;
  completedAt: string;
  durationMs: number;
  attempt: number;
  summary: string;
}

export interface AIAgent {
  id: string;
  slug?: string;
  name: string;
  role: string;
  description?: string;
  isOrchestrator?: boolean;
  enabled?: boolean;
  status: AgentExecutionStatus;
  currentTask: string;
  lastActivity: string;
  processedToday: number;
  successCount?: number;
  failureCount?: number;
  accuracyOrScore: string;
  provider?: string;
  model?: string;
  timeoutSeconds?: number;
  maxRetries?: number;
  temperature?: number;
  systemInstructions?: string;
  executionHistory?: AgentExecutionLogEntry[];
}

export type ActivityEventType =
  | 'News discovered'
  | 'Research completed'
  | 'Fact-check completed'
  | 'Article drafted'
  | 'Article approved'
  | 'Publishing result'
  | 'System errors';

export interface ActivityEvent {
  id: string;
  type: ActivityEventType;
  title: string;
  summary: string;
  agentName: string;
  timestamp: string;
  severity: 'normal' | 'success' | 'warning' | 'error';
}

export type PublishingStageKey =
  | 'Drafts'
  | 'Awaiting Approval'
  | 'Scheduled'
  | 'Published'
  | 'Failed';

export interface PublishingStageMetric {
  stage: PublishingStageKey;
  count: number;
  changeLabel: string;
  description: string;
}

export interface KPIMetric {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTrend: 'up' | 'down' | 'neutral';
  subtitle: string;
  targetNav: NavPageId;
}

export interface AnalyticsPoint {
  label: string;
  websiteViews: number;
  articlesPublished: number;
  socialReach: number;
  revenueUsd: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  read: boolean;
  category: 'system' | 'agent' | 'editorial';
  targetPage: NavPageId;
}

export interface ArticleRecord {
  id: string;
  headline: string;
  category: string;
  stage: PublishingStageKey;
  authorAgent: string;
  factCheckScore: number;
  seoScore: number;
  wordCount: number;
  updatedAt: string;
  summary: string;
}

export interface TrendingSignal {
  id: string;
  topic: string;
  sector: string;
  velocityScore: number;
  sourcesCount: number;
  verificationState: 'Verified' | 'Cross-Checking' | 'Unverified Signal';
  discoveredAt: string;
  assignedAgent: string;
}

export interface NewsSourceFeed {
  id: string;
  name: string;
  protocol: 'RSS / Atom' | 'Wire API' | 'Regulatory Filing' | 'Social Stream';
  trustTier: 'Tier 1 Primary' | 'Tier 2 Verified' | 'Tier 3 Signal';
  pollInterval: string;
  status: SystemConnectionState;
  articlesIngested24h: number;
}

export interface FactCheckClaim {
  id: string;
  claimText: string;
  articleHeadline: string;
  verdict: 'Confirmed Primary Source' | 'Needs Attribution' | 'Disputed Numeric Claim';
  sourcesChecked: number;
  confidencePct: number;
  timestamp: string;
}
