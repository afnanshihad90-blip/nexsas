import React from 'react';
import {
  Pause,
  Play,
  CheckCircle2,
  Clock,
  PauseCircle,
  Power,
  SlidersHorizontal,
} from 'lucide-react';
import { AIAgent } from '../types/dashboard';

interface AgentCardProps {
  agent: AIAgent;
  onTogglePause: (agentId: string) => void;
  onToggleEnabled?: (agentId: string) => void;
  onSelectDetails?: (agentId: string) => void;
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  onTogglePause,
  onToggleEnabled,
  onSelectDetails,
}) => {
  const isEnabled = agent.enabled !== false;
  const isPaused = agent.status === 'Paused' || !isEnabled;
  const isRunning = isEnabled && agent.status === 'Running';
  const successCount = agent.successCount ?? agent.processedToday;
  const failureCount = agent.failureCount ?? 0;

  return (
    <div
      className={`rounded-xl bg-white dark:bg-[#111827] border p-4 flex flex-col justify-between gap-3 transition-colors ${
        agent.isOrchestrator
          ? 'border-blue-500/40 dark:border-blue-500/40'
          : 'border-slate-200 dark:border-slate-800/90'
      } ${!isEnabled ? 'opacity-75' : ''}`}
    >
      <div>
        {/* Header: Agent Name + Enabled/Status indicator */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
                {agent.name}
              </h3>
              <span
                className={`font-mono text-[10px] font-semibold uppercase tracking-wider ${
                  isEnabled
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                {isEnabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {agent.role}
            </div>
          </div>

          <div className="shrink-0">
            {!isEnabled ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 dark:text-rose-400">
                <PauseCircle className="w-3.5 h-3.5" />
                <span>Disabled</span>
              </span>
            ) : isRunning ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Running</span>
              </span>
            ) : agent.status === 'Idle' ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400">
                <Clock className="w-3.5 h-3.5" />
                <span>Idle</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                <PauseCircle className="w-3.5 h-3.5" />
                <span>Paused</span>
              </span>
            )}
          </div>
        </div>

        {/* Current Task */}
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/70">
          <div className="flex items-center justify-between text-[11px] font-medium text-slate-400 dark:text-slate-500 mb-1">
            <span>Current Task (Demo Queue)</span>
            {agent.model && (
              <span className="font-mono text-[10px] text-slate-400">
                {agent.model}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed line-clamp-2">
            {agent.currentTask}
          </p>
        </div>

        {/* Success / Failure & Last Execution Telemetry */}
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
          <span>Last exec: {agent.lastActivity}</span>
          <span>
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
              {successCount} ok
            </span>
            {' / '}
            <span className="text-rose-600 dark:text-rose-400 font-semibold">
              {failureCount} err
            </span>
          </span>
        </div>
      </div>

      {/* Footer Controls: Enable/Disable + Pause/Resume + View Details */}
      <div className="pt-3 border-t border-slate-100 dark:border-slate-800/70 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {onToggleEnabled && (
            <button
              type="button"
              onClick={() => onToggleEnabled(agent.id)}
              aria-label={isEnabled ? `Disable ${agent.name}` : `Enable ${agent.name}`}
              className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                isEnabled
                  ? 'bg-slate-100 dark:bg-slate-800 hover:bg-rose-500/15 text-slate-700 dark:text-slate-300'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white'
              }`}
            >
              <Power className="w-3 h-3" />
              <span>{isEnabled ? 'Disable' : 'Enable'}</span>
            </button>
          )}

          {onSelectDetails && (
            <button
              type="button"
              onClick={() => onSelectDetails(agent.id)}
              aria-label={`View details for ${agent.name}`}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
            >
              <SlidersHorizontal className="w-3 h-3" />
              <span>Details</span>
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={() => onTogglePause(agent.id)}
          disabled={!isEnabled}
          aria-label={isPaused ? `Resume ${agent.name}` : `Pause ${agent.name}`}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap shrink-0 disabled:opacity-40 ${
            isPaused && isEnabled
              ? 'bg-blue-600 hover:bg-blue-500 text-white'
              : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200'
          }`}
        >
          {isPaused ? (
            <>
              <Play className="w-3 h-3" />
              <span>Resume</span>
            </>
          ) : (
            <>
              <Pause className="w-3 h-3" />
              <span>Pause</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
