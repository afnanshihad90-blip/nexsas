import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { SystemConnectionState, SystemHealthNode } from '../types/dashboard';

interface SystemHealthProps {
  nodes: SystemHealthNode[];
  isRefreshing: boolean;
  lastProbeNotice: string | null;
  onRefreshAll: () => void;
  onChangeNodeState: (nodeId: string, nextState: SystemConnectionState) => void;
}

const ALL_CONNECTION_STATES: SystemConnectionState[] = [
  'Connected',
  'Disconnected',
  'Checking',
  'Error',
  'Not Configured',
];

export function renderStatusIndicator(status: SystemConnectionState) {
  switch (status) {
    case 'Connected':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>Connected</span>
        </span>
      );
    case 'Disconnected':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
          <XCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Disconnected</span>
        </span>
      );
    case 'Checking':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400">
          <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
          <span>Checking</span>
        </span>
      );
    case 'Error':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-600 dark:text-rose-400">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>Error</span>
        </span>
      );
    case 'Not Configured':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
          <HelpCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Not Configured</span>
        </span>
      );
  }
}

export const SystemHealth: React.FC<SystemHealthProps> = ({
  nodes,
  isRefreshing,
  lastProbeNotice,
  onRefreshAll,
  onChangeNodeState,
}) => {
  return (
    <section
      aria-labelledby="system-health-heading"
      className="h-full rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5 flex flex-col justify-between"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2
              id="system-health-heading"
              className="font-display font-semibold text-base text-slate-900 dark:text-white"
            >
              System Health Panel
            </h2>
            <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
              ·
            </span>
            <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
              Live Diagnostics
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Honest infrastructure states across all 6 platform tiers. Use the state selector on any row to test UI handling.
          </p>
        </div>

        <button
          type="button"
          onClick={onRefreshAll}
          disabled={isRefreshing}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white transition-colors whitespace-nowrap shrink-0 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>{isRefreshing ? 'Probing Nodes...' : 'Refresh Health'}</span>
        </button>
      </div>

      {lastProbeNotice && (
        <div className="mt-3 px-3.5 py-2 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 flex items-center justify-between gap-2">
          <span>{lastProbeNotice}</span>
          <span className="font-mono text-[11px] text-slate-400 shrink-0">DEMO PROBE</span>
        </div>
      )}

      <div className="mt-4 divide-y divide-slate-200/70 dark:divide-slate-800/80">
        {nodes.map((node) => {
          const effectiveStatus: SystemConnectionState = isRefreshing
            ? 'Checking'
            : node.status;

          return (
            <div
              key={node.id}
              className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-display font-semibold text-xs sm:text-sm text-slate-900 dark:text-slate-100">
                    {node.name}
                  </span>
                  <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
                    ·
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {node.category}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                  {node.endpointOrTarget} — {node.note}
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                <div className="text-left sm:text-right">
                  <div>{renderStatusIndicator(effectiveStatus)}</div>
                  <div className="font-mono text-[10px] text-slate-400 dark:text-slate-500 tabular-nums">
                    {node.latencyMs !== null ? `${node.latencyMs}ms · ` : ''}
                    {node.lastChecked}
                  </div>
                </div>

                <div className="shrink-0">
                  <label htmlFor={`state-select-${node.id}`} className="sr-only">
                    Simulate status for {node.name}
                  </label>
                  <select
                    id={`state-select-${node.id}`}
                    aria-label={`Simulate status for ${node.name}`}
                    value={node.status}
                    onChange={(e) =>
                      onChangeNodeState(node.id, e.target.value as SystemConnectionState)
                    }
                    className="px-2 py-1 rounded-lg text-xs bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {ALL_CONNECTION_STATES.map((st) => (
                      <option key={st} value={st}>
                        State: {st}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
