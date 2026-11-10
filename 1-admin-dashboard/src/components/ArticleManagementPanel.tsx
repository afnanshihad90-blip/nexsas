import React, { useState, useEffect } from 'react';
import {
  FileText,
  CheckCircle,
  UploadCloud,
  Play,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  Clock,
  Sparkles,
} from 'lucide-react';
import { nexusApi } from '../services/apiService';
import { ArticleRecord } from '../types/dashboard';

interface ArticleManagementPanelProps {
  initialArticles?: ArticleRecord[];
}

export const ArticleManagementPanel: React.FC<ArticleManagementPanelProps> = ({
  initialArticles = [],
}) => {
  const [articles, setArticles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);

  const loadArticles = async () => {
    setIsLoading(true);
    try {
      const res = await nexusApi.listArticles(1, 20);
      if (res.ok && res.data && (res.data as any).items?.length > 0) {
        setArticles((res.data as any).items);
      } else {
        // Fallback to initial articles if database/backend has no rows or is offline
        setArticles(
          initialArticles.length > 0
            ? initialArticles
            : [
                {
                  id: 'demo-art-1',
                  title: 'Breakthrough Quantum Computing Benchmark Validated',
                  headline: 'Breakthrough Quantum Computing Benchmark Validated',
                  slug: 'breakthrough-quantum-computing',
                  stage: 'Awaiting Approval',
                  status: 'awaiting_approval',
                  word_count: 540,
                  quality_score: 94,
                  updated_at: new Date().toISOString(),
                },
                {
                  id: 'demo-art-2',
                  title: 'Global Semiconductor Fab Yield Surpasses 85%',
                  headline: 'Global Semiconductor Fab Yield Surpasses 85%',
                  slug: 'semiconductor-fab-yield-milestone',
                  stage: 'Scheduled',
                  status: 'scheduled',
                  word_count: 620,
                  quality_score: 89,
                  updated_at: new Date().toISOString(),
                },
              ]
        );
      }
    } catch {
      setArticles(initialArticles);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadArticles();
  }, []);

  const handleApprove = async (articleId: string) => {
    setActionInProgress(articleId);
    setStatusMessage(null);
    try {
      const res = await nexusApi.approveArticle(articleId, 'Approved by editor in Dashboard');
      if (res.ok) {
        setStatusMessage({
          type: 'success',
          text: `Article '${articleId}' approved successfully. Ready to publish to blog.`,
        });
        await loadArticles();
      } else {
        setStatusMessage({
          type: 'error',
          text: (res.data as any)?.detail?.message || res.errorMessage || 'Approval failed.',
        });
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message });
    } finally {
      setActionInProgress(null);
    }
  };

  const handlePublishToBlog = async (articleId: string) => {
    setActionInProgress(articleId);
    setStatusMessage(null);
    try {
      const res = await nexusApi.publishToBlog(articleId);
      if (res.ok) {
        setStatusMessage({
          type: 'success',
          text: `Article published to blog! Response: ${JSON.stringify((res.data as any)?.blog_response ?? 'OK')}`,
        });
        await loadArticles();
      } else {
        const detail = (res.data as any)?.detail;
        const msg = detail?.message || res.errorMessage || 'Publishing to blog failed.';
        const hint = detail?.hint ? ` Hint: ${detail.hint}` : '';
        setStatusMessage({
          type: 'error',
          text: `${msg}${hint}`,
        });
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message });
    } finally {
      setActionInProgress(null);
    }
  };

  const handleRunPipeline = async () => {
    setActionInProgress('pipeline');
    setStatusMessage({ type: 'info', text: 'Running autonomous news scan -> research -> fact-check -> write pipeline...' });
    try {
      const res = await nexusApi.runAutonomousPipeline();
      if (res.ok && res.data) {
        const data: any = res.data;
        setStatusMessage({
          type: 'success',
          text: `Generated article "${data.headline}" (Score: ${data.quality_score}/100, Stage: ${data.stage})!`,
        });
        await loadArticles();
      } else {
        setStatusMessage({
          type: 'error',
          text: (res.data as any)?.detail?.message || res.errorMessage || 'Pipeline run failed.',
        });
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message });
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/90 p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-base text-slate-900 dark:text-white flex items-center gap-2">
              Editorial Articles & Dispatch
              <span className="text-xs font-mono font-normal text-slate-500 dark:text-slate-400">
                ({articles.length} items)
              </span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Review AI-drafted articles, approve drafts, and push HMAC-signed posts directly to the PHP blog.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadArticles}
            disabled={isLoading}
            className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Refresh articles"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            type="button"
            onClick={handleRunPipeline}
            disabled={actionInProgress !== null}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 shadow-sm"
          >
            {actionInProgress === 'pipeline' ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Run Autonomous Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div
          className={`mt-4 p-3 rounded-lg text-xs flex items-start gap-2 border ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
              : statusMessage.type === 'error'
                ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
                : 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
          ) : statusMessage.type === 'error' ? (
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          ) : (
            <Clock className="w-4 h-4 shrink-0 mt-0.5 animate-pulse" />
          )}
          <span className="flex-1">{statusMessage.text}</span>
        </div>
      )}

      {/* Article List Table */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
              <th className="pb-2.5 font-medium">Headline & Slug</th>
              <th className="pb-2.5 font-medium">Stage</th>
              <th className="pb-2.5 font-medium">Quality Score</th>
              <th className="pb-2.5 font-medium">Word Count</th>
              <th className="pb-2.5 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {articles.map((art) => {
              const headline = art.headline || art.title || 'Untitled';
              const stage = art.stage || (art.status === 'published' ? 'Published' : art.status === 'scheduled' ? 'Scheduled' : 'Awaiting Approval');
              const quality = art.fact_check_score || art.quality_score || 90;
              const words = art.word_count || 500;
              const isWorking = actionInProgress === art.id;

              return (
                <tr key={art.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 pr-4">
                    <p className="font-medium text-slate-900 dark:text-white line-clamp-1">
                      {headline}
                    </p>
                    <p className="font-mono text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                      /{art.slug || 'story'}
                    </p>
                  </td>
                  <td className="py-3 pr-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                        stage === 'Published'
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                          : stage === 'Scheduled'
                            ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                            : 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
                      }`}
                    >
                      {stage}
                    </span>
                  </td>
                  <td className="py-3 pr-4 font-mono whitespace-nowrap">
                    <span className="font-semibold text-slate-900 dark:text-white">{quality}</span>
                    <span className="text-slate-400">/100</span>
                  </td>
                  <td className="py-3 pr-4 font-mono text-slate-600 dark:text-slate-300 whitespace-nowrap">
                    {words} words
                  </td>
                  <td className="py-3 text-right whitespace-nowrap space-x-2">
                    {stage === 'Awaiting Approval' && (
                      <button
                        type="button"
                        onClick={() => handleApprove(art.id)}
                        disabled={isWorking}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 font-medium transition-colors disabled:opacity-50"
                      >
                        <CheckCircle className="w-3 h-3" />
                        <span>{isWorking ? 'Approving...' : 'Approve'}</span>
                      </button>
                    )}

                    {(stage === 'Scheduled' || stage === 'Published' || stage === 'Awaiting Approval') && (
                      <button
                        type="button"
                        onClick={() => handlePublishToBlog(art.id)}
                        disabled={isWorking}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 font-medium transition-colors disabled:opacity-50"
                      >
                        <UploadCloud className="w-3 h-3" />
                        <span>{isWorking ? 'Publishing...' : 'Publish to Blog'}</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
