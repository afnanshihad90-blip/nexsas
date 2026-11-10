import React, { useState } from 'react';
import { Check, RotateCcw, Shield, Sliders } from 'lucide-react';
import { nexusApi } from '../services/apiService';

interface SettingsPageProps {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onResetDemoState: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  darkMode,
  onToggleDarkMode,
  onResetDemoState,
}) => {
  const [organizationName, setOrganizationName] = useState('NEXUS MEDIA AI — Global Desk');
  const [minFactCheckScore, setMinFactCheckScore] = useState(95);
  const [requireHumanApproval, setRequireHumanApproval] = useState(true);
  const [defaultCadenceMinutes, setDefaultCadenceMinutes] = useState(15);
  const [savedBanner, setSavedBanner] = useState(false);

  const integrationMeta = nexusApi.getIntegrationMetadata();

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
          <div>
            <h2 className="font-display font-semibold text-base text-slate-900 dark:text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-500" />
              <span>Platform &amp; Editorial Governance Settings</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Configure newsroom control plane defaults, autonomous verification thresholds, and UI preferences.
            </p>
          </div>

          <button
            type="button"
            onClick={onResetDemoState}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors self-start sm:self-auto"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Local Session Cache</span>
          </button>
        </div>

        {savedBanner && (
          <div className="mt-4 px-4 py-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
            <Check className="w-4 h-4 shrink-0" />
            <span>
              Settings saved to workspace session state.
            </span>
          </div>
        )}

        <form onSubmit={handleSave} className="mt-5 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="org-name-input"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Newsroom Workspace Name
              </label>
              <input
                id="org-name-input"
                type="text"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label
                htmlFor="fact-threshold-input"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Minimum Fact-Check Confidence Gate ({minFactCheckScore}%)
              </label>
              <input
                id="fact-threshold-input"
                type="range"
                min={75}
                max={100}
                value={minFactCheckScore}
                onChange={(e) => setMinFactCheckScore(Number(e.target.value))}
                className="w-full accent-blue-600 mt-2"
              />
              <div className="flex justify-between font-mono text-[11px] text-slate-400 tabular-nums mt-1">
                <span>75% (Permissive)</span>
                <span>Current: {minFactCheckScore}%</span>
                <span>100% (Strict Primary Filing)</span>
              </div>
            </div>

            <div>
              <label
                htmlFor="cadence-select"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Trend Scout Poll Interval (Minutes)
              </label>
              <select
                id="cadence-select"
                value={defaultCadenceMinutes}
                onChange={(e) => setDefaultCadenceMinutes(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value={5}>Every 5 minutes</option>
                <option value={15}>Every 15 minutes</option>
                <option value={30}>Every 30 minutes</option>
                <option value={60}>Every 60 minutes</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200/80 dark:border-slate-800">
              <div>
                <div className="text-xs font-medium text-slate-900 dark:text-slate-100">
                  Require Editorial Sign-Off Before Publishing
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Hold Fact-Checked drafts in &ldquo;Awaiting Approval&rdquo; stage
                </div>
              </div>
              <input
                type="checkbox"
                aria-label="Require Editorial Sign-Off Before Publishing"
                checked={requireHumanApproval}
                onChange={(e) => setRequireHumanApproval(e.target.checked)}
                className="w-4 h-4 accent-blue-600 rounded"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-600 dark:text-slate-400">
                Interface Theme:
              </span>
              <button
                type="button"
                onClick={onToggleDarkMode}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
              >
                {darkMode ? 'Dark Navy / Charcoal (Active)' : 'Light Editorial (Active)'}
              </button>
            </div>

            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors"
            >
              Save Workspace Preferences
            </button>
          </div>
        </form>
      </div>

      {/* API Service Abstraction Status Panel */}
      <div className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-violet-500" />
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
            Prepared API Service Abstraction (Step 2+ Integration Contract)
          </h3>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          No API keys or secrets are stored in frontend code. All future external calls route through server-side proxy endpoints.
        </p>

        <div className="divide-y divide-slate-200/70 dark:divide-slate-800/80">
          {integrationMeta.plannedServices.map((svc) => (
            <div
              key={svc.id}
              className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div>
                <div className="font-semibold text-slate-900 dark:text-slate-100">
                  {svc.name}
                </div>
                <div className="text-slate-500 dark:text-slate-400 font-mono text-[11px] mt-0.5">
                  Binding: {svc.envVarName}
                </div>
              </div>
              <div className="sm:text-right font-mono text-[11px] text-amber-600 dark:text-amber-400">
                <div>{svc.status}</div>
                <div className="text-slate-400">{svc.plannedStep}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
