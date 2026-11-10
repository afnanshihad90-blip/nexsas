import React, { useState, useEffect } from 'react';
import { ShieldAlert, PauseCircle, PlayCircle, RefreshCw } from 'lucide-react';
import { nexusApi } from '../services/apiService';

interface EmergencyStopBannerProps {
  onStatusChange?: (engaged: boolean) => void;
}

export const EmergencyStopBanner: React.FC<EmergencyStopBannerProps> = ({ onStatusChange }) => {
  const [isEngaged, setIsEngaged] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastCheck, setLastCheck] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await nexusApi.getKillSwitch();
      if (res.ok && res.data) {
        const engaged = Boolean((res.data as any).kill_switch_engaged);
        setIsEngaged(engaged);
        onStatusChange?.(engaged);
      }
      setLastCheck(new Date().toLocaleTimeString());
    } catch {
      // Offline fallback
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async () => {
    setIsLoading(true);
    try {
      const nextState = !isEngaged;
      const res = await nexusApi.setKillSwitch(
        nextState,
        nextState ? 'Emergency Stop clicked by operator in Dashboard' : 'Operator resumed publishing from Dashboard'
      );
      if (res.ok && res.data) {
        const engaged = Boolean((res.data as any).kill_switch_engaged);
        setIsEngaged(engaged);
        onStatusChange?.(engaged);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isEngaged) {
    return (
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/40 dark:bg-slate-950/40 border-b border-slate-200/50 dark:border-slate-800/50 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Publishing Pipeline: <span className="text-emerald-500 font-semibold">Active</span></span>
        </div>
        <button
          type="button"
          onClick={handleToggle}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-600/10 hover:bg-rose-600/20 text-rose-500 hover:text-rose-400 border border-rose-500/30 transition-colors font-medium text-[11px]"
        >
          <PauseCircle className="w-3.5 h-3.5" />
          <span>{isLoading ? 'Updating...' : 'Engage Emergency Stop'}</span>
        </button>
      </div>
    );
  }

  return (
    <aside
      aria-label="Emergency Stop Alert Banner"
      className="px-4 py-3 bg-rose-600 text-white font-sans flex flex-col sm:flex-row items-center justify-between gap-3 shadow-md animate-in slide-in-from-top duration-300"
    >
      <div className="flex items-center gap-2.5">
        <ShieldAlert className="w-5 h-5 shrink-0 animate-bounce" />
        <div className="text-xs">
          <span className="font-bold uppercase tracking-wider text-[11px] px-2 py-0.5 rounded bg-black/20 mr-2">
            Emergency Stop Active
          </span>
          <span className="font-medium">
            All automatic publishing, agent task execution, and blog posts are PAUSED by global kill switch.
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={handleToggle}
        disabled={isLoading}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white text-rose-700 hover:bg-rose-50 font-semibold text-xs transition-colors shrink-0 shadow-sm"
      >
        {isLoading ? (
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <PlayCircle className="w-3.5 h-3.5" />
        )}
        <span>Resume Publishing System</span>
      </button>
    </aside>
  );
};
