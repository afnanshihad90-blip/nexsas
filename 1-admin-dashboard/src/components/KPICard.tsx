import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { KPIMetric, NavPageId } from '../types/dashboard';

interface KPICardProps {
  metric: KPIMetric;
  onNavigate: (page: NavPageId) => void;
}

export const KPICard: React.FC<KPICardProps> = ({ metric, onNavigate }) => {
  return (
    <button
      type="button"
      onClick={() => onNavigate(metric.targetNav)}
      className="group w-full text-left p-4 sm:p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 hover:border-blue-500/50 dark:hover:border-blue-500/50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      {/* Top Row: Label + Unboxed Demo Data disclosure */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">
          {metric.label}
        </span>
        <span className="font-mono text-[11px] text-slate-400 dark:text-slate-500 whitespace-nowrap shrink-0">
          DEMO DATA
        </span>
      </div>

      {/* Main Value Row */}
      <div className="flex items-baseline justify-between gap-2 my-1">
        <span className="font-mono font-semibold text-xl sm:text-2xl text-slate-900 dark:text-white tabular-nums tracking-tight">
          {metric.value}
        </span>
        <span
          className={`font-mono text-xs font-medium tabular-nums whitespace-nowrap ${
            metric.deltaTrend === 'up'
              ? 'text-emerald-600 dark:text-emerald-400'
              : metric.deltaTrend === 'down'
                ? 'text-rose-600 dark:text-rose-400'
                : 'text-amber-600 dark:text-amber-400'
          }`}
        >
          {metric.delta}
        </span>
      </div>

      {/* Bottom Subtitle + Drilldown Affordance */}
      <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800/70 flex items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span className="truncate">{metric.subtitle}</span>
        <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 transition-colors shrink-0" />
      </div>
    </button>
  );
};
