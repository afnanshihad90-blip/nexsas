import React from 'react';
import {
  ActivityEvent,
  AIAgent,
  AnalyticsPoint,
  ArticleRecord,
  DateRangeOption,
  KPIMetric,
  NavPageId,
  PublishingStageKey,
  PublishingStageMetric,
  SystemConnectionState,
  SystemHealthNode,
} from '../types/dashboard';
import { KPICard } from './KPICard';
import { SystemHealth } from './SystemHealth';
import { AgentCard } from './AgentCard';
import { PublishingOverview } from './PublishingOverview';
import { AnalyticsCharts } from './AnalyticsCharts';
import { ActivityTimeline } from './ActivityTimeline';
import { DatabaseStatusPanel } from './DatabaseStatusPanel';
import { BlogIntegrationPanel } from './BlogIntegrationPanel';
import { ArticleManagementPanel } from './ArticleManagementPanel';
import {
  DatabaseLiveSnapshot,
  SupabaseEnvValidationResult,
} from '../services/supabaseClient';

interface DashboardPageProps {
  kpis: KPIMetric[];
  healthNodes: SystemHealthNode[];
  isRefreshingHealth: boolean;
  lastProbeNotice: string | null;
  onRefreshHealth: () => void;
  onChangeHealthNodeState: (nodeId: string, nextState: SystemConnectionState) => void;
  agents: AIAgent[];
  onToggleAgentPause: (agentId: string) => void;
  onToggleAgentEnabled?: (agentId: string) => void;
  onPauseAllAgents: () => void;
  onResumeAllAgents: () => void;
  publishingStages: PublishingStageMetric[];
  articles: ArticleRecord[];
  selectedStage: PublishingStageKey | 'ALL';
  onSelectStage: (stage: PublishingStageKey | 'ALL') => void;
  analyticsSeries: AnalyticsPoint[];
  dateRange: DateRangeOption;
  activityEvents: ActivityEvent[];
  onNavigate: (page: NavPageId) => void;
  dbDiagnostics: SupabaseEnvValidationResult;
  dbSnapshot: DatabaseLiveSnapshot;
  isProbingDb: boolean;
  onProbeDatabase: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  kpis,
  healthNodes,
  isRefreshingHealth,
  lastProbeNotice,
  onRefreshHealth,
  onChangeHealthNodeState,
  agents,
  onToggleAgentPause,
  onToggleAgentEnabled,
  onPauseAllAgents,
  onResumeAllAgents,
  publishingStages,
  articles,
  selectedStage,
  onSelectStage,
  analyticsSeries,
  dateRange,
  activityEvents,
  onNavigate,
  dbDiagnostics,
  dbSnapshot,
  isProbingDb,
  onProbeDatabase,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Architecture Disclosure Banner */}
      <div className="rounded-xl bg-gradient-to-r from-blue-600/10 via-violet-600/10 to-transparent border border-blue-500/20 dark:border-blue-500/30 px-4 py-3 flex flex-col lg:flex-row lg:items-center justify-between gap-2">
        <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
          <span className="font-semibold text-slate-900 dark:text-white">
            NEXUS MEDIA AI · Step 4 Multi-Agent Intelligence System:
          </span>{' '}
          FastAPI status:{' '}
          <span className="font-mono font-semibold text-amber-600 dark:text-amber-400">
            BACKEND NOT CONNECTED
          </span>{' '}
          · Database status:{' '}
          <span className="font-mono font-semibold text-amber-600 dark:text-amber-400">
            {dbSnapshot.statusLabel}
          </span>
          . Displaying clearly labeled{' '}
          <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
            DEMO DATA
          </span>{' '}
          until backend &amp; database credentials are connected.
        </div>
        <div className="flex flex-wrap items-center gap-3 shrink-0 self-start lg:self-auto">
          <button
            type="button"
            onClick={() => onNavigate('ai-agents')}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
          >
            Open Agent Control Center (10 Agents) →
          </button>
          <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
            ·
          </span>
          <button
            type="button"
            onClick={() => onNavigate('api-connections')}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
          >
            Inspect FastAPI Routes →
          </button>
          <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
            ·
          </span>
          <button
            type="button"
            onClick={() => onNavigate('database-status')}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
          >
            Inspect Supabase Schema →
          </button>
        </div>
      </div>

      {/* 8 KPI Cards Grid */}
      <section aria-label="Key Performance Indicators">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((metric) => (
            <KPICard
              key={metric.id}
              metric={metric}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      </section>

      {/* Step 2 Database Connection & 6 Real Status Interfaces Panel */}
      <DatabaseStatusPanel
        diagnostics={dbDiagnostics}
        snapshot={dbSnapshot}
        isProbing={isProbingDb}
        onProbeDatabase={onProbeDatabase}
        compactMode
        onNavigate={onNavigate}
      />

      {/* InfinityFree Blog Integration Panel (Step 9) */}
      <BlogIntegrationPanel />

      {/* Editorial Article Management & Direct Blog Dispatch (Step 9) */}
      <ArticleManagementPanel initialArticles={articles} />

      {/* System Health + Publishing Overview Split */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        <div className="xl:col-span-6 flex flex-col">
          <SystemHealth
            nodes={healthNodes}
            isRefreshing={isRefreshingHealth}
            lastProbeNotice={lastProbeNotice}
            onRefreshAll={onRefreshHealth}
            onChangeNodeState={onChangeHealthNodeState}
          />
        </div>

        <div className="xl:col-span-6 flex flex-col">
          <PublishingOverview
            stages={publishingStages}
            articles={articles}
            selectedStage={selectedStage}
            onSelectStage={onSelectStage}
            onNavigate={onNavigate}
          />
        </div>
      </div>

      {/* AI Agent Overview Section (Central Orchestrator + All 9 Specialist Agents) */}
      <section
        aria-labelledby="ai-agents-overview-heading"
        className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <h2
                id="ai-agents-overview-heading"
                className="font-display font-semibold text-base text-slate-900 dark:text-white"
              >
                AI Agent Overview
              </h2>
              <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
                ·
              </span>
              <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                1 Central Orchestrator + 9 Specialist Agents (Step 4 Control Plane)
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Enable, disable, pause, or resume agents, or open the Agent Control Center to configure models and inspect execution history.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onNavigate('ai-agents')}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors whitespace-nowrap"
            >
              Agent Control Center →
            </button>
            <button
              type="button"
              onClick={onResumeAllAgents}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors whitespace-nowrap"
            >
              Resume All
            </button>
            <button
              type="button"
              onClick={onPauseAllAgents}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors whitespace-nowrap"
            >
              Pause All
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-4">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onTogglePause={onToggleAgentPause}
              onToggleEnabled={onToggleAgentEnabled}
              onSelectDetails={() => onNavigate('ai-agents')}
            />
          ))}
        </div>
      </section>

      {/* Analytics Preview (4 Required Demo Charts) */}
      <AnalyticsCharts series={analyticsSeries} dateRange={dateRange} />

      {/* Recent Activity Timeline */}
      <ActivityTimeline events={activityEvents} />
    </div>
  );
};
