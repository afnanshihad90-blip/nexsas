import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculatePublishingTotals,
  computeActiveAgentCount,
  filterArticles,
  getMetricsForDateRange,
  summarizeAnalyticsSeries,
  toggleAgentStatus,
  updateHealthNodeStatus,
  validateArticleDraft,
} from './dashboardLogic';
import { AIAgent, ArticleRecord, PublishingStageMetric, SystemHealthNode } from '../types/dashboard';

const sampleAgents: AIAgent[] = [
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    role: 'Pipeline Supervisor',
    status: 'Running',
    currentTask: 'Dispatching tasks',
    lastActivity: '1m ago',
    processedToday: 140,
    accuracyOrScore: '99.4%',
  },
  {
    id: 'trend-scout',
    name: 'Trend Scout',
    role: 'Signal Discovery',
    status: 'Paused',
    currentTask: 'Paused',
    lastActivity: '10m ago',
    processedToday: 85,
    accuracyOrScore: '96.1%',
  },
];

test('toggleAgentStatus switches Running to Paused and back', () => {
  const afterPause = toggleAgentStatus(sampleAgents, 'orchestrator');
  assert.equal(afterPause[0].status, 'Paused');
  assert.equal(computeActiveAgentCount(afterPause), 0);

  const afterResume = toggleAgentStatus(afterPause, 'trend-scout');
  assert.equal(afterResume[1].status, 'Running');
  assert.equal(computeActiveAgentCount(afterResume), 1);
});

test('getMetricsForDateRange scales values by date window and reflects active agent count', () => {
  const kpis24h = getMetricsForDateRange('24h', 7, 9);
  const kpis30d = getMetricsForDateRange('30d', 9, 9);
  assert.equal(kpis24h.length, 8);
  assert.equal(kpis24h[3].value, '7 / 9');
  assert.equal(kpis30d[3].value, '9 / 9');
  assert.notEqual(kpis24h[0].value, kpis30d[0].value);
});

test('updateHealthNodeStatus updates only the targeted system node', () => {
  const nodes: SystemHealthNode[] = [
    {
      id: 'backend-api',
      name: 'Backend API status',
      category: 'Core Compute',
      status: 'Not Configured',
      endpointOrTarget: 'FastAPI Service (Step 2)',
      latencyMs: null,
      lastChecked: '5m ago',
      note: 'Awaiting Step 2 integration',
    },
  ];
  const updated = updateHealthNodeStatus(nodes, 'backend-api', 'Connected');
  assert.equal(updated[0].status, 'Connected');
  assert.equal(updated[0].latencyMs, 18);
});

test('calculatePublishingTotals computes sum and published percentage', () => {
  const stages: PublishingStageMetric[] = [
    { stage: 'Drafts', count: 10, changeLabel: '+2', description: 'In progress' },
    { stage: 'Published', count: 30, changeLabel: '+5', description: 'Live' },
  ];
  const totals = calculatePublishingTotals(stages);
  assert.equal(totals.total, 40);
  assert.equal(totals.publishedRatioPct, 75);
});

test('validateArticleDraft enforces headline, word count, and https source URL', () => {
  const invalid = validateArticleDraft({
    headline: 'Short',
    category: 'Semiconductors',
    body: 'Too few words here.',
    primarySourceUrl: 'http://insecure.example.com',
  });
  assert.equal(invalid.valid, false);
  assert.equal(invalid.errors.length, 3);

  const validBody = Array.from({ length: 30 }, (_, i) => `word${i}`).join(' ');
  const valid = validateArticleDraft({
    headline: 'Global Wafer Supply Stabilizes After Q3 Foundry Expansion',
    category: 'Semiconductors',
    body: validBody,
    primarySourceUrl: 'https://reuters.example.com/filing-2026',
  });
  assert.equal(valid.valid, true);
  assert.equal(valid.errors.length, 0);
  assert.equal(valid.wordCount, 30);
});

test('filterArticles and summarizeAnalyticsSeries return expected subsets and sums', () => {
  const articles: ArticleRecord[] = [
    {
      id: '1',
      headline: 'EU Grid Storage Directive Passed',
      category: 'Energy',
      stage: 'Published',
      authorAgent: 'News Writer',
      factCheckScore: 98,
      seoScore: 92,
      wordCount: 840,
      updatedAt: '10m ago',
      summary: 'Summary 1',
    },
    {
      id: '2',
      headline: 'Subsea Fiber Route Scheduled',
      category: 'Telecom',
      stage: 'Drafts',
      authorAgent: 'News Writer',
      factCheckScore: 91,
      seoScore: 84,
      wordCount: 620,
      updatedAt: '25m ago',
      summary: 'Summary 2',
    },
  ];
  assert.equal(filterArticles(articles, 'grid', 'ALL').length, 1);
  assert.equal(filterArticles(articles, '', 'Drafts').length, 1);

  const summary = summarizeAnalyticsSeries([
    { label: 'Mon', websiteViews: 1000, articlesPublished: 4, socialReach: 5000, revenueUsd: 25.5 },
    { label: 'Tue', websiteViews: 1500, articlesPublished: 6, socialReach: 7000, revenueUsd: 34.5 },
  ]);
  assert.equal(summary.totalViews, 2500);
  assert.equal(summary.totalArticles, 10);
  assert.equal(summary.totalReach, 12000);
  assert.equal(summary.totalRevenue, 60);
});
