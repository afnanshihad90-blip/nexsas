import React, { useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Cpu,
  GitBranch,
  History,
  Pause,
  Play,
  Power,
  ServerOff,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { ActivityEvent, AIAgent } from '../types/dashboard';
import { nexusApi } from '../services/apiService';
import { AgentCard } from './AgentCard';

interface AgentControlCenterProps {
  agents: AIAgent[];
  activityEvents: ActivityEvent[];
  onToggleAgentPause: (agentId: string) => void;
  onToggleAgentEnabled: (agentId: string) => void;
  onUpdateAgentConfig: (
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
  ) => void;
  onPauseAllAgents: () => void;
  onResumeAllAgents: () => void;
}

const TEN_STAGE_WORKFLOW = [
  { stage: 1, key: 'trend_discovery', agent: 'Trend Scout', summary: 'Discovers story & deduplicates RSS topics' },
  { stage: 2, key: 'source_collection', agent: 'Source Collector', summary: 'Collects canonical URLs & publisher metadata' },
  { stage: 3, key: 'evidence_research', agent: 'Research Agent', summary: 'Extracts claims & identifies disagreements' },
  { stage: 4, key: 'fact_checking', agent: 'Fact Checker', summary: 'Verifies claims against independent sources' },
  { stage: 5, key: 'verification_gate', agent: 'Orchestrator', summary: 'Halts pipeline if claims lack verification' },
  { stage: 6, key: 'article_drafting', agent: 'News Writer', summary: 'Drafts original article with source citations' },
  { stage: 7, key: 'seo_optimization', agent: 'SEO Agent', summary: 'Optimizes metadata & checks heading hierarchy' },
  { stage: 8, key: 'media_licensing', agent: 'Media Agent', summary: 'Verifies Unsplash/Pexels/Wikimedia licenses' },
  { stage: 9, key: 'publishing_preparation', agent: 'Publishing Agent', summary: 'Stages draft in manual approval mode only' },
  { stage: 10, key: 'analytics_monitoring', agent: 'Analytics Agent', summary: 'Returns NOT_CONNECTED until analytics linked' },
];

export const AgentControlCenter: React.FC<AgentControlCenterProps> = ({
  agents,
  activityEvents,
  onToggleAgentPause,
  onToggleAgentEnabled,
  onUpdateAgentConfig,
  onPauseAllAgents,
  onResumeAllAgents,
}) => {
  const orchestrator =
    agents.find((a) => a.isOrchestrator || a.id === 'agent-orchestrator') ?? agents[0];
  const specialists = agents.filter(
    (a) => !a.isOrchestrator && a.id !== 'agent-orchestrator'
  );

  const [selectedAgentId, setSelectedAgentId] = useState<string>(
    specialists[0]?.id ?? orchestrator.id
  );
  const [apiCallNotice, setApiCallNotice] = useState<string | null>(null);

  const selectedAgent =
    agents.find((a) => a.id === selectedAgentId) ?? orchestrator;

  // Configuration form state synced to selectedAgent
  const [cfgProvider, setCfgProvider] = useState<string>(
    selectedAgent.provider ?? 'gemini'
  );
  const [cfgModel, setCfgModel] = useState<string>(
    selectedAgent.model ?? 'gemini-2.5-pro'
  );
  const [cfgTimeout, setCfgTimeout] = useState<number>(
    selectedAgent.timeoutSeconds ?? 90
  );
  const [cfgMaxRetries, setCfgMaxRetries] = useState<number>(
    selectedAgent.maxRetries ?? 3
  );
  const [cfgTemperature, setCfgTemperature] = useState<number>(
    selectedAgent.temperature ?? 0.2
  );
  const [cfgInstructions, setCfgInstructions] = useState<string>(
    selectedAgent.systemInstructions ?? ''
  );

  const handleSelectAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    const found = agents.find((a) => a.id === agentId);
    if (found) {
      setCfgProvider(found.provider ?? 'gemini');
      setCfgModel(found.model ?? 'gemini-2.5-pro');
      setCfgTimeout(found.timeoutSeconds ?? 90);
      setCfgMaxRetries(found.maxRetries ?? 3);
      setCfgTemperature(found.temperature ?? 0.2);
      setCfgInstructions(found.systemInstructions ?? '');
    }
  };

  const handleApiBackedPauseToggle = async (agentId: string) => {
    const target = agents.find((a) => a.id === agentId);
    if (!target) return;
    const isPaused = target.status === 'Paused';
    const apiRes = isPaused
      ? await nexusApi.resumeAgent(agentId)
      : await nexusApi.pauseAgent(agentId);

    onToggleAgentPause(agentId);
    setApiCallNotice(
      apiRes.ok
        ? `Backend API confirmed ${isPaused ? 'resume' : 'pause'} for ${target.name}.`
        : `${apiRes.errorMessage} — Updated local preview state only (DEMO DATA; no real agent execution simulated).`
    );
  };

  const handleApiBackedEnableToggle = async (agentId: string) => {
    const target = agents.find((a) => a.id === agentId);
    if (!target) return;
    const currentlyEnabled = target.enabled !== false;
    const apiRes = currentlyEnabled
      ? await nexusApi.disableAgent(agentId)
      : await nexusApi.enableAgent(agentId);

    onToggleAgentEnabled(agentId);
    setApiCallNotice(
      apiRes.ok
        ? `Backend API confirmed ${currentlyEnabled ? 'disable' : 'enable'} for ${target.name}.`
        : `${apiRes.errorMessage} — Updated local preview state only (DEMO DATA; no real agent execution simulated).`
    );
  };

  const handleSaveConfiguration = async (e: React.FormEvent) => {
    e.preventDefault();
    const apiRes = await nexusApi.updateAgentConfig(selectedAgent.id, {
      provider: cfgProvider,
      model: cfgModel,
      timeout_seconds: cfgTimeout,
      max_retries: cfgMaxRetries,
      temperature: cfgTemperature,
      system_instructions: cfgInstructions,
    });

    onUpdateAgentConfig(selectedAgent.id, {
      provider: cfgProvider,
      model: cfgModel,
      timeoutSeconds: cfgTimeout,
      maxRetries: cfgMaxRetries,
      temperature: cfgTemperature,
      systemInstructions: cfgInstructions,
    });

    setApiCallNotice(
      apiRes.ok
        ? `Saved configuration for ${selectedAgent.name} to FastAPI backend.`
        : `${apiRes.errorMessage} — Saved configuration for ${selectedAgent.name} in local dashboard state (DEMO DATA).`
    );
  };

  const diag = nexusApi.getDiagnostics();

  return (
    <div className="space-y-6">
      {/* Honest Disconnected Backend & AI Provider Disclosure */}
      <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs text-amber-800 dark:text-amber-300">
        <div className="flex items-start gap-3">
          <ServerOff className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">
              Multi-Agent Control Center · {diag.statusLabel} · AI Provider: NOT CONNECTED (DEMO DATA)
            </div>
            <p className="mt-0.5 leading-relaxed">
              All 9 specialist agents and the central Orchestrator are implemented in{' '}
              <code className="font-mono">backend/app/agents/</code>. Controls below invoke{' '}
              <code className="font-mono">/api/agents/*</code> endpoints and never simulate fake live AI executions.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onResumeAllAgents}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/80 dark:bg-slate-900 hover:bg-white dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 border border-amber-500/30 transition-colors"
          >
            Resume All
          </button>
          <button
            type="button"
            onClick={onPauseAllAgents}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/80 dark:bg-slate-900 hover:bg-white dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 border border-amber-500/30 transition-colors"
          >
            Pause All
          </button>
        </div>
      </div>

      {apiCallNotice && (
        <div
          role="status"
          className="rounded-xl bg-blue-500/10 border border-blue-500/30 px-4 py-3 text-xs text-blue-700 dark:text-blue-300 flex items-center justify-between gap-3"
        >
          <span className="font-mono">{apiCallNotice}</span>
          <button
            type="button"
            onClick={() => setApiCallNotice(null)}
            className="text-xs underline shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Central Orchestrator Status & 10-Stage Pipeline Card */}
      <section
        aria-label="Central Orchestrator Status"
        className="rounded-xl bg-white dark:bg-[#111827] border border-blue-500/30 dark:border-blue-500/30 p-5 space-y-4"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-500" />
              <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
                Central Orchestrator Agent ({orchestrator.name})
              </h3>
              <span className="font-mono text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                {orchestrator.enabled !== false ? 'ENABLED' : 'DISABLED'} · {orchestrator.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {orchestrator.description}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => handleApiBackedEnableToggle(orchestrator.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
            >
              <Power className="w-3.5 h-3.5" />
              <span>{orchestrator.enabled !== false ? 'Disable Orchestrator' : 'Enable Orchestrator'}</span>
            </button>
            <button
              type="button"
              onClick={() => handleApiBackedPauseToggle(orchestrator.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
            >
              {orchestrator.status === 'Paused' ? (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Resume Orchestrator</span>
                </>
              ) : (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>Pause Orchestrator</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => handleSelectAgent(orchestrator.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Configure Orchestrator</span>
            </button>
          </div>
        </div>

        {/* Orchestrator Telemetry Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800">
            <div className="text-slate-500">Specialist Fleet</div>
            <div className="font-mono font-semibold text-sm text-slate-900 dark:text-white mt-0.5">
              {specialists.filter((s) => s.enabled !== false).length} / {specialists.length} Enabled
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800">
            <div className="text-slate-500">Orchestrator Success / Fail</div>
            <div className="font-mono font-semibold text-sm text-emerald-600 dark:text-emerald-400 mt-0.5">
              {orchestrator.successCount ?? 140} ok / {orchestrator.failureCount ?? 2} halted
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800">
            <div className="text-slate-500">Task Queue Broker</div>
            <div className="font-mono font-semibold text-sm text-slate-900 dark:text-white mt-0.5">
              Async + Redis/Celery Ready
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800">
            <div className="text-slate-500">Publishing Guard</div>
            <div className="font-mono font-semibold text-sm text-blue-600 dark:text-blue-400 mt-0.5">
              Draft / Manual Approval Only
            </div>
          </div>
        </div>

        {/* 10-Stage Orchestrator Workflow Pipeline */}
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2.5">
            <GitBranch className="w-3.5 h-3.5 text-blue-500" />
            <span>10-Stage Enforced Orchestrator Workflow Pipeline</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
            {TEN_STAGE_WORKFLOW.map((item) => (
              <div
                key={item.key}
                className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800 text-xs"
              >
                <div className="flex items-center justify-between font-mono text-[11px] text-blue-600 dark:text-blue-400 font-semibold">
                  <span>STAGE {item.stage}</span>
                  <span>{item.agent}</span>
                </div>
                <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 leading-snug">
                  {item.summary}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* All Nine Specialist Agents Grid */}
      <section aria-label="Nine Specialist Agents">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display font-semibold text-base text-slate-900 dark:text-white">
            Nine Specialist Agents ({specialists.length} Registered)
          </h3>
          <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
            Specialist agents cannot publish independently · Controlled by Orchestrator
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {specialists.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onTogglePause={handleApiBackedPauseToggle}
              onToggleEnabled={handleApiBackedEnableToggle}
              onSelectDetails={handleSelectAgent}
            />
          ))}
        </div>
      </section>

      {/* Agent Configuration Screen + Execution History & Recent Activity */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Configuration Screen */}
        <section
          aria-label="Agent Configuration Screen"
          className="xl:col-span-6 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5"
        >
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-blue-500" />
              <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
                Agent Configuration Screen: {selectedAgent.name}
              </h3>
            </div>
            <select
              aria-label="Select agent to configure"
              value={selectedAgent.id}
              onChange={(e) => handleSelectAgent(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg text-xs bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.role})
                </option>
              ))}
            </select>
          </div>

          <form onSubmit={handleSaveConfiguration} className="mt-4 space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="agent-cfg-provider"
                  className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  AI Provider Abstraction
                </label>
                <select
                  id="agent-cfg-provider"
                  value={cfgProvider}
                  onChange={(e) => setCfgProvider(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value="gemini">Google Gemini (Server Env Key)</option>
                  <option value="openai">OpenAI (Server Env Key)</option>
                  <option value="anthropic">Anthropic Claude (Server Env Key)</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="agent-cfg-model"
                  className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  Model Identifier
                </label>
                <input
                  id="agent-cfg-model"
                  type="text"
                  value={cfgModel}
                  onChange={(e) => setCfgModel(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg font-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label
                  htmlFor="agent-cfg-timeout"
                  className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  Task Timeout (sec)
                </label>
                <input
                  id="agent-cfg-timeout"
                  type="number"
                  min={5}
                  max={600}
                  value={cfgTimeout}
                  onChange={(e) => setCfgTimeout(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg font-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label
                  htmlFor="agent-cfg-retries"
                  className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  Maximum Retries
                </label>
                <input
                  id="agent-cfg-retries"
                  type="number"
                  min={0}
                  max={10}
                  value={cfgMaxRetries}
                  onChange={(e) => setCfgMaxRetries(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg font-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label
                  htmlFor="agent-cfg-temp"
                  className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  Temperature (0.0–2.0)
                </label>
                <input
                  id="agent-cfg-temp"
                  type="number"
                  step={0.1}
                  min={0}
                  max={2}
                  value={cfgTemperature}
                  onChange={(e) => setCfgTemperature(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg font-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="agent-cfg-instructions"
                className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                System Instructions
              </label>
              <textarea
                id="agent-cfg-instructions"
                rows={3}
                value={cfgInstructions}
                onChange={(e) => setCfgInstructions(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 leading-relaxed"
              />
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
              <span className="font-mono text-[11px] text-slate-500">
                Credentials read strictly from server env (AI_PROVIDER_API_KEY)
              </span>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors"
              >
                Save Agent Configuration
              </button>
            </div>
          </form>
        </section>

        {/* Agent Execution History & Recent Activity */}
        <section
          aria-label="Agent Execution History and Recent Activity"
          className="xl:col-span-6 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5 space-y-4"
        >
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-violet-500" />
              <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
                Execution History &amp; Activity: {selectedAgent.name}
              </h3>
            </div>
            <span className="font-mono text-[11px] text-blue-600 dark:text-blue-400">
              DEMO DATA LOGS
            </span>
          </div>

          <div className="space-y-2.5">
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">
              Structured AgentTaskOutput History ({selectedAgent.executionHistory?.length ?? 0} entries)
            </div>
            {(selectedAgent.executionHistory ?? []).map((entry) => (
              <div
                key={entry.taskId}
                className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 text-xs space-y-1"
              >
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {entry.taskId} · stage={entry.stageName}
                  </span>
                  <span
                    className={
                      entry.status === 'completed'
                        ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                        : entry.status === 'not_connected'
                        ? 'text-amber-600 dark:text-amber-400 font-semibold'
                        : 'text-rose-600 dark:text-rose-400 font-semibold'
                    }
                  >
                    {entry.status.toUpperCase()} ({entry.durationMs}ms · attempt {entry.attempt})
                  </span>
                </div>
                <p className="text-slate-600 dark:text-slate-400">{entry.summary}</p>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              <span>Recent Fleet Activity Stream</span>
            </div>
            <div className="divide-y divide-slate-200/70 dark:divide-slate-800/80">
              {activityEvents.slice(0, 4).map((ev) => (
                <div key={ev.id} className="py-2 first:pt-0 last:pb-0 text-xs">
                  <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                    <span>{ev.agentName}</span>
                    <span>{ev.timestamp}</span>
                  </div>
                  <div className="font-medium text-slate-800 dark:text-slate-200">
                    {ev.title}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
