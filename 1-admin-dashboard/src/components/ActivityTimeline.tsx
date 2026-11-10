import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  FileEdit,
  Flame,
  Layers,
  Send,
} from 'lucide-react';
import { ActivityEvent, ActivityEventType } from '../types/dashboard';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

type FilterCategory = 'all' | 'discovery' | 'editorial' | 'publishing' | 'errors';

function getEventIcon(type: ActivityEventType) {
  switch (type) {
    case 'News discovered':
      return Flame;
    case 'Research completed':
      return Layers;
    case 'Fact-check completed':
      return CheckCircle2;
    case 'Article drafted':
      return FileEdit;
    case 'Article approved':
      return FileCheck2;
    case 'Publishing result':
      return Send;
    case 'System errors':
      return AlertTriangle;
  }
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ events }) => {
  const [filter, setFilter] = useState<FilterCategory>('all');

  const filteredEvents = events.filter((ev) => {
    if (filter === 'all') return true;
    if (filter === 'discovery')
      return ev.type === 'News discovered' || ev.type === 'Research completed';
    if (filter === 'editorial')
      return (
        ev.type === 'Fact-check completed' ||
        ev.type === 'Article drafted' ||
        ev.type === 'Article approved'
      );
    if (filter === 'publishing') return ev.type === 'Publishing result';
    if (filter === 'errors') return ev.type === 'System errors';
    return true;
  });

  const filterButtons: { id: FilterCategory; label: string }[] = [
    { id: 'all', label: 'All Events' },
    { id: 'discovery', label: 'Intelligence' },
    { id: 'editorial', label: 'Editorial' },
    { id: 'publishing', label: 'Publishing' },
    { id: 'errors', label: 'Errors' },
  ];

  return (
    <section
      aria-labelledby="recent-activity-heading"
      className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2
              id="recent-activity-heading"
              className="font-display font-semibold text-base text-slate-900 dark:text-white"
            >
              Recent Activity Timeline
            </h2>
            <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
              ·
            </span>
            <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
              DEMO STREAM
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Simulated chronological log across discovery, research, fact-checking, drafting, approval, and publishing.
          </p>
        </div>

        {/* Interactive Filter Segmented Control */}
        <div
          role="group"
          aria-label="Filter activity events"
          className="flex flex-wrap items-center gap-1 p-1 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800"
        >
          {filterButtons.map((btn) => (
            <button
              key={btn.id}
              type="button"
              onClick={() => setFilter(btn.id)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                filter === btn.id
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-2xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {filteredEvents.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
          No activity events match the selected filter.
        </div>
      ) : (
        <div className="mt-4 divide-y divide-slate-200/70 dark:divide-slate-800/80">
          {filteredEvents.map((ev) => {
            const Icon = getEventIcon(ev.type);
            const iconColor =
              ev.severity === 'error'
                ? 'text-rose-600 dark:text-rose-400'
                : ev.severity === 'warning'
                  ? 'text-amber-600 dark:text-amber-400'
                  : ev.severity === 'success'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-blue-600 dark:text-blue-400';

            return (
              <div
                key={ev.id}
                className="py-3.5 first:pt-0 last:pb-0 flex items-start gap-3.5"
              >
                <div className="mt-0.5 p-2 rounded-lg bg-slate-100 dark:bg-slate-800/90 shrink-0">
                  <Icon className={`w-4 h-4 ${iconColor}`} />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {ev.type}
                      </span>
                      <span aria-hidden="true" className="text-slate-300 dark:text-slate-700">
                        ·
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">
                        {ev.agentName}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-slate-400 dark:text-slate-500 tabular-nums shrink-0">
                      {ev.timestamp}
                    </span>
                  </div>

                  <div className="font-display font-medium text-xs sm:text-sm text-slate-800 dark:text-slate-200 mt-1">
                    {ev.title}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                    {ev.summary}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
