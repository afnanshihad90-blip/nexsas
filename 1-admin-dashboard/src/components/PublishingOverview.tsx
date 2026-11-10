import React from 'react';
import { ArrowRight } from 'lucide-react';
import {
  ArticleRecord,
  NavPageId,
  PublishingStageKey,
  PublishingStageMetric,
} from '../types/dashboard';
import { calculatePublishingTotals } from '../utils/dashboardLogic';

interface PublishingOverviewProps {
  stages: PublishingStageMetric[];
  articles: ArticleRecord[];
  selectedStage: PublishingStageKey | 'ALL';
  onSelectStage: (stage: PublishingStageKey | 'ALL') => void;
  onNavigate: (page: NavPageId) => void;
}

export const PublishingOverview: React.FC<PublishingOverviewProps> = ({
  stages,
  articles,
  selectedStage,
  onSelectStage,
  onNavigate,
}) => {
  const { total, publishedRatioPct } = calculatePublishingTotals(stages);

  const filteredPreview = articles
    .filter((a) => selectedStage === 'ALL' || a.stage === selectedStage)
    .slice(0, 5);

  return (
    <section
      aria-labelledby="publishing-overview-heading"
      className="h-full rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5 flex flex-col justify-between"
    >
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-200 dark:border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <h2
                id="publishing-overview-heading"
                className="font-display font-semibold text-base text-slate-900 dark:text-white"
              >
                Publishing Overview
              </h2>
              <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
                ·
              </span>
              <span className="font-mono text-xs text-slate-500 dark:text-slate-400 tabular-nums">
                {total} Total Items (DEMO)
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Select any stage below to filter the live queue preview. Completion rate: {publishedRatioPct}% published.
            </p>
          </div>

          <button
            type="button"
            onClick={() => onNavigate('publishing-queue')}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap shrink-0 self-start sm:self-auto"
          >
            <span>Open Publishing Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 5 Required Stages Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mt-4">
          {stages.map((item) => {
            const isSelected = selectedStage === item.stage;
            return (
              <button
                key={item.stage}
                type="button"
                onClick={() =>
                  onSelectStage(isSelected ? 'ALL' : item.stage)
                }
                className={`text-left p-3 rounded-lg border transition-colors ${
                  isSelected
                    ? 'bg-blue-600/10 border-blue-500 text-slate-900 dark:text-white'
                    : 'bg-slate-50/80 dark:bg-slate-900/70 border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-medium text-slate-600 dark:text-slate-300 truncate">
                  {item.stage}
                </div>
                <div className="font-mono font-semibold text-lg sm:text-xl text-slate-900 dark:text-white tabular-nums mt-1">
                  {item.count}
                </div>
                <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400 tabular-nums mt-0.5 truncate">
                  {item.changeLabel}
                </div>
              </button>
            );
          })}
        </div>

        {/* Filtered Article Stage List */}
        <div className="mt-4 pt-4 border-t border-slate-200/70 dark:border-slate-800/80">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {selectedStage === 'ALL'
                ? 'Recent Pipeline Items (All Stages)'
                : `Filtered Stage: ${selectedStage}`}
            </span>
            {selectedStage !== 'ALL' && (
              <button
                type="button"
                onClick={() => onSelectStage('ALL')}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Show all stages
              </button>
            )}
          </div>

          <div className="divide-y divide-slate-200/60 dark:divide-slate-800/70">
            {filteredPreview.map((art) => (
              <div
                key={art.id}
                className="py-2.5 first:pt-0 last:pb-0 flex items-center justify-between gap-3 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                    {art.headline}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <span className="font-mono tabular-nums">{art.id}</span>
                    <span aria-hidden="true">·</span>
                    <span>{art.category}</span>
                    <span aria-hidden="true">·</span>
                    <span>{art.stage}</span>
                  </div>
                </div>
                <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400 tabular-nums shrink-0 text-right">
                  <div>SEO {art.seoScore}%</div>
                  <div>{art.updatedAt}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
