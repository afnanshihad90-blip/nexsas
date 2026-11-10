import React from 'react';
import { AnalyticsPoint, DateRangeOption } from '../types/dashboard';
import { summarizeAnalyticsSeries } from '../utils/dashboardLogic';

interface AnalyticsChartsProps {
  series: AnalyticsPoint[];
  dateRange: DateRangeOption;
}

interface MiniChartCardProps {
  title: string;
  subtitle: string;
  summaryValue: string;
  points: { label: string; value: number }[];
  formatValue: (v: number) => string;
  strokeClass: string;
  fillClass: string;
  barMode?: boolean;
}

const MiniChartCard: React.FC<MiniChartCardProps> = ({
  title,
  subtitle,
  summaryValue,
  points,
  formatValue,
  strokeClass,
  fillClass,
  barMode = false,
}) => {
  const maxVal = Math.max(...points.map((p) => p.value), 1);
  const width = 360;
  const height = 120;
  const padX = 16;
  const padY = 16;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  const coords = points.map((pt, idx) => {
    const x =
      points.length === 1
        ? width / 2
        : padX + (idx / (points.length - 1)) * innerW;
    const y = padY + innerH - (pt.value / maxVal) * innerH;
    return { x, y, ...pt };
  });

  const polylinePoints = coords.map((c) => `${c.x},${c.y}`).join(' ');
  const areaPoints =
    coords.length > 1
      ? `${coords[0].x},${padY + innerH} ${polylinePoints} ${
          coords[coords.length - 1].x
        },${padY + innerH}`
      : '';

  return (
    <div className="rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 p-4 flex flex-col justify-between">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h3 className="font-display font-semibold text-xs sm:text-sm text-slate-900 dark:text-white">
            {title}
          </h3>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">
            {subtitle}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono font-semibold text-sm sm:text-base text-slate-900 dark:text-white tabular-nums">
            {summaryValue}
          </div>
          <div className="font-mono text-[10px] text-slate-400 dark:text-slate-500">
            DEMO SERIES
          </div>
        </div>
      </div>

      {/* Pure SVG Chart Viewport */}
      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-28 overflow-visible"
          role="img"
          aria-label={`${title} demo chart`}
        >
          {/* Subtle Horizontal Grid Lines */}
          {[0.2, 0.6, 1].map((ratio, i) => {
            const y = padY + innerH * ratio;
            return (
              <line
                key={i}
                x1={padX}
                y1={y}
                x2={width - padX}
                y2={y}
                className="stroke-slate-200 dark:stroke-slate-800"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
            );
          })}

          {barMode ? (
            coords.map((c, idx) => {
              const barW = Math.max(14, Math.floor(innerW / (coords.length * 1.8)));
              const barH = Math.max(4, padY + innerH - c.y);
              return (
                <g key={idx}>
                  <rect
                    x={c.x - barW / 2}
                    y={c.y}
                    width={barW}
                    height={barH}
                    rx={3}
                    className={fillClass}
                  />
                </g>
              );
            })
          ) : (
            <>
              {areaPoints && (
                <polygon points={areaPoints} className={`${fillClass} opacity-15`} />
              )}
              <polyline
                fill="none"
                points={polylinePoints}
                className={strokeClass}
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {coords.map((c, idx) => (
                <circle
                  key={idx}
                  cx={c.x}
                  cy={c.y}
                  r="3"
                  className={`${fillClass} stroke-white dark:stroke-slate-900`}
                  strokeWidth="1.5"
                >
                  <title>{`${c.label}: ${formatValue(c.value)} (Demo Data)`}</title>
                </circle>
              ))}
            </>
          )}
        </svg>

        {/* X-Axis Labels */}
        <div className="flex items-center justify-between px-2 mt-1 font-mono text-[10px] text-slate-400 dark:text-slate-500 tabular-nums">
          {points.map((pt) => (
            <span key={pt.label}>{pt.label}</span>
          ))}
        </div>
      </div>
    </div>
  );
};

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  series,
  dateRange,
}) => {
  const summary = summarizeAnalyticsSeries(series);

  return (
    <section
      aria-labelledby="analytics-preview-heading"
      className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-200 dark:border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2
              id="analytics-preview-heading"
              className="font-display font-semibold text-base text-slate-900 dark:text-white"
            >
              Analytics Preview ({dateRange})
            </h2>
            <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
              ·
            </span>
            <span className="font-mono text-xs text-amber-600 dark:text-amber-400">
              DEMO DATA — NOT CONNECTED TO LIVE ANALYTICS
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Simulated time-series trajectories for Step 1 architecture verification. Live telemetry connects in Step 4+.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <MiniChartCard
          title="Website Views Over Time"
          subtitle="Simulated reader sessions across news portal"
          summaryValue={summary.totalViews.toLocaleString('en-US')}
          points={series.map((s) => ({ label: s.label, value: s.websiteViews }))}
          formatValue={(v) => `${v.toLocaleString('en-US')} views`}
          strokeClass="stroke-blue-500"
          fillClass="fill-blue-500"
        />

        <MiniChartCard
          title="Articles Published Over Time"
          subtitle="Autonomous & editor-approved dispatches"
          summaryValue={`${summary.totalArticles.toLocaleString('en-US')} articles`}
          points={series.map((s) => ({
            label: s.label,
            value: s.articlesPublished,
          }))}
          formatValue={(v) => `${v} articles`}
          strokeClass="stroke-violet-500"
          fillClass="fill-violet-500"
          barMode
        />

        <MiniChartCard
          title="Social Media Reach"
          subtitle="Cross-channel syndicated impressions"
          summaryValue={summary.totalReach.toLocaleString('en-US')}
          points={series.map((s) => ({ label: s.label, value: s.socialReach }))}
          formatValue={(v) => `${v.toLocaleString('en-US')} reach`}
          strokeClass="stroke-indigo-500"
          fillClass="fill-indigo-500"
        />

        <MiniChartCard
          title="Revenue Over Time"
          subtitle="Estimated programmatic & syndication yield"
          summaryValue={`$${summary.totalRevenue.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`}
          points={series.map((s) => ({ label: s.label, value: s.revenueUsd }))}
          formatValue={(v) => `$${v.toFixed(2)}`}
          strokeClass="stroke-emerald-500"
          fillClass="fill-emerald-500"
        />
      </div>
    </section>
  );
};
