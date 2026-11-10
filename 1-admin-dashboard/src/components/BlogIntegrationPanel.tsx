import React, { useState } from 'react';
import { Globe, CheckCircle2, AlertTriangle, RefreshCw, Send, ShieldCheck, HelpCircle } from 'lucide-react';
import { nexusApi } from '../services/apiService';

export const BlogIntegrationPanel: React.FC = () => {
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    httpStatus?: number;
    error?: string;
    hint?: string;
    blogResponse?: any;
    checkedAt?: string;
  } | null>(null);

  const handleRunIntegrationTest = async () => {
    setIsRunningTest(true);
    try {
      const res = await nexusApi.testBlogIntegration();
      const checkedAt = new Date().toLocaleTimeString();
      if (res.ok && res.data) {
        const payload: any = res.data;
        setTestResult({
          ok: Boolean(payload.ok),
          httpStatus: payload.http_status ?? (payload.ok ? 200 : undefined),
          error: payload.error,
          hint: payload.hint ?? (payload.ok ? 'Draft landed in blog DB without duplication (Idempotent).' : undefined),
          blogResponse: payload.blog_response,
          checkedAt,
        });
      } else {
        setTestResult({
          ok: false,
          httpStatus: res.status,
          error: (res.data as any)?.detail?.message ?? res.errorMessage ?? 'Connection failed',
          hint: (res.data as any)?.detail?.hint ?? 'Verify BLOG_ENDPOINT and BLOG_SIGNING_SECRET on Render.',
          checkedAt,
        });
      }
    } catch (err: any) {
      setTestResult({
        ok: false,
        error: err.message,
        hint: 'Check network connectivity to FastAPI backend.',
        checkedAt: new Date().toLocaleTimeString(),
      });
    } finally {
      setIsRunningTest(false);
    }
  };

  return (
    <div className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-base text-slate-900 dark:text-white flex items-center gap-2">
              InfinityFree Blog Integration
              <span className="inline-flex items-center gap-1 text-[11px] font-normal px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                HMAC-SHA256 Protected
              </span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live link between Render FastAPI backend and PHP 8 blog (Push & Pull Sync).
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleRunIntegrationTest}
          disabled={isRunningTest}
          className="inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition-colors shrink-0 shadow-sm"
        >
          {isRunningTest ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Verifying Connection...</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Test Connection (POST /api/blog/test)</span>
            </>
          )}
        </button>
      </div>

      {/* Integration Test Outcome */}
      {testResult ? (
        <div
          className={`mt-4 p-4 rounded-xl border ${
            testResult.ok
              ? 'bg-emerald-50/60 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/60 text-emerald-900 dark:text-emerald-300'
              : 'bg-rose-50/60 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/60 text-rose-900 dark:text-rose-300'
          }`}
        >
          <div className="flex items-start gap-3">
            {testResult.ok ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-sm">
                  {testResult.ok ? 'Connection Verified: Blog Responded OK' : 'Integration Test Failed'}
                </span>
                <span className="font-mono text-[11px] opacity-75">{testResult.checkedAt}</span>
              </div>

              {testResult.httpStatus !== undefined && (
                <p className="mt-1 font-mono">
                  HTTP Status: <span className="font-bold">{testResult.httpStatus}</span>
                </p>
              )}

              {testResult.error && (
                <p className="mt-1 text-rose-700 dark:text-rose-400 font-medium">
                  Error: {testResult.error}
                </p>
              )}

              {testResult.hint && (
                <div className="mt-2 p-2.5 rounded-lg bg-white/60 dark:bg-black/20 border border-slate-200/50 dark:border-slate-800/50 flex items-start gap-1.5 text-[11px]">
                  <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 opacity-75" />
                  <span>{testResult.hint}</span>
                </div>
              )}

              {testResult.blogResponse && (
                <pre className="mt-2 p-2 rounded bg-slate-900 text-slate-100 font-mono text-[10px] overflow-x-auto">
                  {JSON.stringify(testResult.blogResponse, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 flex items-center justify-between">
          <span>Click the test button above to send an HMAC-signed test draft to the blog.</span>
          <span className="font-mono text-[11px] text-slate-400">Target: /api/publish.php</span>
        </div>
      )}
    </div>
  );
};
