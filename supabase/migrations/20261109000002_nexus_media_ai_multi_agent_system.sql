-- ============================================================================
-- NEXUS MEDIA AI — STEP 4: MULTI-AGENT INTELLIGENCE SYSTEM MIGRATION
-- Migration ID: 20261109000002_nexus_media_ai_multi_agent_system.sql
-- Purpose: Extends existing Step 2 agent tables (agents, agent_configs,
--          agent_tasks, agent_activity) without duplicating them, and adds
--          workflow_runs and agent_execution_logs with Row Level Security.
-- ============================================================================

BEGIN;

-- 1. Extend public.agents with Step 4 operational counters & enablement flag
ALTER TABLE public.agents
  ADD COLUMN IF NOT EXISTS is_orchestrator BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS success_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failure_count INTEGER NOT NULL DEFAULT 0;

-- 2. Extend public.agent_configs with provider abstraction & retry settings
ALTER TABLE public.agent_configs
  ADD COLUMN IF NOT EXISTS provider_name TEXT NOT NULL DEFAULT 'unconfigured',
  ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3 CHECK (max_retries >= 0 AND max_retries <= 10),
  ADD COLUMN IF NOT EXISTS allow_image_generation BOOLEAN NOT NULL DEFAULT FALSE;

-- 3. Create public.workflow_runs for the 10-Stage Orchestrator Pipeline
CREATE TABLE IF NOT EXISTS public.workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key TEXT NOT NULL UNIQUE,
  orchestrator_agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
  topic_headline TEXT NOT NULL,
  current_stage TEXT NOT NULL DEFAULT 'trend_discovery' CHECK (current_stage IN (
    'trend_discovery',
    'source_collection',
    'evidence_research',
    'fact_checking',
    'verification_gate',
    'article_drafting',
    'seo_optimization',
    'media_licensing',
    'publishing_preparation',
    'analytics_monitoring'
  )),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
    'queued',
    'running',
    'completed',
    'halted_verification',
    'failed',
    'cancelled'
  )),
  stage_results JSONB NOT NULL DEFAULT '{}'::jsonb,
  failure_stage TEXT,
  failure_reason TEXT,
  initiated_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Extend public.agent_tasks for idempotency, dead-letter queue, and workflow linking
ALTER TABLE public.agent_tasks
  ADD COLUMN IF NOT EXISTS workflow_run_id UUID REFERENCES public.workflow_runs(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER NOT NULL DEFAULT 120,
  ADD COLUMN IF NOT EXISTS dead_letter_reason TEXT,
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

-- Allow dead_letter status in public.agent_tasks
ALTER TABLE public.agent_tasks DROP CONSTRAINT IF EXISTS agent_tasks_status_check;
ALTER TABLE public.agent_tasks
  ADD CONSTRAINT agent_tasks_status_check
  CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'dead_letter'));

-- 5. Create public.agent_execution_logs for structured JSON agent I/O audit trails
CREATE TABLE IF NOT EXISTS public.agent_execution_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES public.agent_tasks(id) ON DELETE CASCADE,
  workflow_run_id UUID REFERENCES public.workflow_runs(id) ON DELETE CASCADE,
  agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  agent_slug TEXT NOT NULL,
  stage_name TEXT NOT NULL,
  attempt_number INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'cancelled', 'dead_letter', 'not_connected')),
  input_envelope JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_envelope JSONB NOT NULL DEFAULT '{}'::jsonb,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Triggers for updated_at on workflow_runs
DROP TRIGGER IF EXISTS trg_workflow_runs_updated_at ON public.workflow_runs;
CREATE TRIGGER trg_workflow_runs_updated_at
  BEFORE UPDATE ON public.workflow_runs
  FOR EACH ROW
  EXECUTE FUNCTION public.trigger_set_updated_at();

-- 7. Indexes for Step 4 Orchestration & Task Queue Lookup
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status_created
  ON public.workflow_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_idempotency
  ON public.workflow_runs(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_idempotency
  ON public.agent_tasks(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_workflow_run
  ON public.agent_tasks(workflow_run_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_execution_logs_agent_created
  ON public.agent_execution_logs(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_execution_logs_workflow
  ON public.agent_execution_logs(workflow_run_id, created_at ASC);

-- 7. Ensure role authorization helper exists
CREATE OR REPLACE FUNCTION public.has_any_role(allowed_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF auth.uid() IS NULL THEN
    RETURN FALSE;
  END IF;
  RETURN EXISTS (
    SELECT 1
    FROM public.users u
    JOIN public.user_roles ur ON ur.user_id = u.id
    WHERE u.auth_user_id = auth.uid()
      AND u.status = 'active'
      AND ur.role_name = ANY(allowed_roles)
  );
END;
$$;

-- 8. Row Level Security (RLS) for new Step 4 tables
ALTER TABLE public.workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_execution_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins and operators manage workflow_runs" ON public.workflow_runs;
CREATE POLICY "Admins and operators manage workflow_runs"
  ON public.workflow_runs
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

DROP POLICY IF EXISTS "Admins and operators view agent_execution_logs" ON public.agent_execution_logs;
CREATE POLICY "Admins and operators view agent_execution_logs"
  ON public.agent_execution_logs
  FOR ALL
  TO authenticated
  USING (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator', 'fact_checker']))
  WITH CHECK (public.has_any_role(ARRAY['super_admin', 'managing_editor', 'operator']));

COMMIT;
