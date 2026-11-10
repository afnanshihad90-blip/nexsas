"""
NEXUS MEDIA AI — Central Orchestrator Agent & 10-Stage Pipeline (Step 4)
Responsibilities:
- Receiving tasks and selecting the appropriate specialist agents.
- Managing the 10-stage workflow pipeline:
  1. Trend Scout discovers a story.
  2. Source Collector gathers supporting sources.
  3. Research Agent analyzes the evidence.
  4. Fact Checker evaluates factual claims.
  5. Orchestrator checks verification results (verification gate).
  6. News Writer creates an original draft.
  7. SEO Agent optimizes the draft.
  8. Media Agent recommends licensed imagery.
  9. Publishing Agent prepares a draft publishing job.
  10. Analytics Agent monitors published content when real analytics become available.
- Tracking task status, handling failures, preventing duplicate jobs, managing retries,
  recording agent activity & execution logs, and enforcing workflow rules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from app.agents.provider import AIProviderAdapter
from app.agents.queue import QueuedTaskRecord, ReliableTaskQueue
from app.agents.schemas import (
    AgentConfigurationSpec,
    AgentTaskInput,
    AgentTaskOutput,
    utc_now_iso,
)
from app.agents.specialists import (
    AnalyticsAgent,
    BaseSpecialistAgent,
    FactCheckerAgent,
    MediaAgent,
    NewsWriterAgent,
    PublishingAgent,
    ResearchAgent,
    SEOAgent,
    SourceCollectorAgent,
    TrendScoutAgent,
)


PIPELINE_STAGES_ORDER = (
    "trend_discovery",
    "source_collection",
    "evidence_research",
    "fact_checking",
    "verification_gate",
    "article_drafting",
    "seo_optimization",
    "media_licensing",
    "publishing_preparation",
    "analytics_monitoring",
)

STAGE_TO_AGENT_ID = {
    "trend_discovery": "agent-trend-scout",
    "source_collection": "agent-source-collector",
    "evidence_research": "agent-research",
    "fact_checking": "agent-fact-checker",
    "verification_gate": "agent-orchestrator",
    "article_drafting": "agent-news-writer",
    "seo_optimization": "agent-seo",
    "media_licensing": "agent-media",
    "publishing_preparation": "agent-publishing",
    "analytics_monitoring": "agent-analytics",
}


def build_default_agent_Specs() -> Dict[str, AgentConfigurationSpec]:
    """Creates the canonical configuration registry for the Orchestrator + 9 Specialist Agents."""
    specs = [
        AgentConfigurationSpec(
            agent_id="agent-orchestrator",
            slug="orchestrator",
            name="Orchestrator",
            role="Master Pipeline Coordinator",
            description="Central control coordinator managing workflow stages, task routing, verification gates, retries, and idempotency.",
            is_orchestrator=True,
            enabled=True,
            provider="gemini",
            model="gemini-2.5-pro",
            timeout_seconds=120,
            max_retries=3,
            temperature=0.1,
            system_instructions="Coordinate all 9 specialist agents across the 10-stage editorial pipeline. Halt immediately if verification fails.",
            current_status="Idle",
            current_task="Ready to coordinate multi-agent workflows",
        ),
        AgentConfigurationSpec(
            agent_id="agent-trend-scout",
            slug="trend-scout",
            name="Trend Scout",
            role="Global Wire & Signal Discovery",
            description="Discovers trending news topics from configured RSS feeds, detects duplicate topics, and scores emerging relevance.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=3,
            temperature=0.2,
            system_instructions="Analyze configured RSS and news feeds, filter duplicate topics, and score story relevance.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-source-collector",
            slug="source-collector",
            name="Source Collector",
            role="Source Attribution & Metadata Harvester",
            description="Collects source URLs, publisher metadata, publication timestamps, and reliability tiers without inventing sources.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=3,
            temperature=0.0,
            system_instructions="Preserve exact source URLs, publisher attribution, and timestamps. Never invent sources or article metadata.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-research",
            slug="research-agent",
            name="Research Agent",
            role="Evidence Organization & Claim Extraction",
            description="Organizes evidence from collected sources, extracts factual claims, and identifies disagreements or missing context.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-pro",
            timeout_seconds=90,
            max_retries=3,
            temperature=0.1,
            system_instructions="Organize multi-source evidence, extract factual claims, and surface inter-source disagreements.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-fact-checker",
            slug="fact-checker",
            name="Fact Checker",
            role="Claim Verification & Citation Audit",
            description="Evaluates individual claims against independent sources and classifies them as verified, disputed, unsupported, or outdated.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-pro",
            timeout_seconds=90,
            max_retries=3,
            temperature=0.0,
            system_instructions="Never mark a claim verified without supporting evidence. Classify every claim rigorously.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-news-writer",
            slug="news-writer",
            name="News Writer",
            role="Original Editorial Drafting",
            description="Writes original, well-structured news articles with headlines, section headings, analysis, and source links from verified research.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-pro",
            timeout_seconds=120,
            max_retries=2,
            temperature=0.3,
            system_instructions="Write original, accurate news journalism strictly grounded in verified claims and primary source links.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-seo",
            slug="seo-agent",
            name="SEO Agent",
            role="Search Intent & Structured Metadata",
            description="Generates SEO titles, meta descriptions, slugs, internal links, and FAQ schemas while checking heading hierarchy and keyword stuffing.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=2,
            temperature=0.2,
            system_instructions="Optimize metadata and heading hierarchy for search intent without sacrificing factual accuracy.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-media",
            slug="media-agent",
            name="Media Agent",
            role="Licensed Editorial Imagery & Attribution",
            description="Searches approved providers (Unsplash, Pexels, Wikimedia Commons), verifies licenses, and enforces photographer attribution.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=2,
            temperature=0.1,
            allow_image_generation=False,
            system_instructions="Verify explicit image licenses from Unsplash, Pexels, or Wikimedia Commons. Never assume an image is free without license verification.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-publishing",
            slug="publishing-agent",
            name="Publishing Agent",
            role="Draft Packaging & Queue Staging",
            description="Validates required editorial metadata and stages approved publishing jobs in draft/manual approval mode only.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=3,
            temperature=0.0,
            system_instructions="Stage articles in draft/manual approval mode only. Never publish automatically in Step 4.",
        ),
        AgentConfigurationSpec(
            agent_id="agent-analytics",
            slug="analytics-agent",
            name="Analytics Agent",
            role="Real Telemetry & Performance Attribution",
            description="Processes connected website and social analytics without fabricating traffic, reach, clicks, or revenue.",
            enabled=True,
            provider="gemini",
            model="gemini-2.5-flash",
            timeout_seconds=60,
            max_retries=2,
            temperature=0.0,
            system_instructions="Return NOT_CONNECTED when analytics providers are disconnected. Never fabricate metrics.",
        ),
    ]
    return {spec.agent_id: spec for spec in specs}


class OrchestratorAgent:
    """
    Central Orchestrator controlling the 9 specialist agents, task routing,
    workflow stages, verification gates, retries, and execution logs.
    """

    def __init__(
        self,
        provider_adapter: Optional[AIProviderAdapter] = None,
        task_queue: Optional[ReliableTaskQueue] = None,
    ) -> None:
        self.configs: Dict[str, AgentConfigurationSpec] = build_default_agent_Specs()
        self.provider_adapter = provider_adapter or AIProviderAdapter()
        self.task_queue = task_queue or ReliableTaskQueue()

        self.specialists: Dict[str, BaseSpecialistAgent] = {
            "agent-trend-scout": TrendScoutAgent(self.configs["agent-trend-scout"], self.provider_adapter),
            "agent-source-collector": SourceCollectorAgent(
                self.configs["agent-source-collector"], self.provider_adapter
            ),
            "agent-research": ResearchAgent(self.configs["agent-research"], self.provider_adapter),
            "agent-fact-checker": FactCheckerAgent(self.configs["agent-fact-checker"], self.provider_adapter),
            "agent-news-writer": NewsWriterAgent(self.configs["agent-news-writer"], self.provider_adapter),
            "agent-seo": SEOAgent(self.configs["agent-seo"], self.provider_adapter),
            "agent-media": MediaAgent(self.configs["agent-media"], self.provider_adapter),
            "agent-publishing": PublishingAgent(self.configs["agent-publishing"], self.provider_adapter),
            "agent-analytics": AnalyticsAgent(self.configs["agent-analytics"], self.provider_adapter),
        }

        self.execution_logs: List[Dict[str, Any]] = []
        self.activity_events: List[Dict[str, Any]] = []
        self.workflow_runs: Dict[str, Dict[str, Any]] = {}
        self._workflow_id_by_idempotency: Dict[str, str] = {}

    def resolve_agent_id(self, identifier: str) -> str:
        """Resolves either an agent_id ('agent-trend-scout') or slug ('trend-scout') to canonical agent_id."""
        if identifier in self.configs:
            return identifier
        for aid, cfg in self.configs.items():
            if cfg.slug == identifier:
                return aid
        raise KeyError(f"Agent '{identifier}' is not registered in the Orchestrator.")

    def select_specialist_for_stage(self, stage_name: str) -> BaseSpecialistAgent:
        """Selects the appropriate specialist agent for a given workflow stage."""
        agent_id = STAGE_TO_AGENT_ID.get(stage_name)
        if not agent_id or agent_id not in self.specialists:
            raise KeyError(f"No specialist agent registered for stage '{stage_name}'.")
        return self.specialists[agent_id]

    def list_all_agents(self) -> List[Dict[str, Any]]:
        provider_status = self.provider_adapter.get_status()
        result: List[Dict[str, Any]] = []
        for aid, cfg in self.configs.items():
            item = cfg.to_dict()
            item["provider_status"] = provider_status.status_label
            item["provider_connected"] = provider_status.is_connected
            result.append(item)
        return result

    def get_agent_details(self, identifier: str) -> Dict[str, Any]:
        aid = self.resolve_agent_id(identifier)
        cfg = self.configs[aid]
        provider_status = self.provider_adapter.get_status()
        recent_logs = [log for log in self.execution_logs if log["agent_id"] == aid][:20]
        recent_tasks = self.task_queue.list_tasks(agent_id=aid, limit=20)
        return {
            **cfg.to_dict(),
            "provider_status": provider_status.status_label,
            "provider_connected": provider_status.is_connected,
            "execution_history": recent_logs,
            "recent_tasks": recent_tasks,
        }

    def update_agent_config(
        self,
        identifier: str,
        updates: Dict[str, Any],
        actor: str = "operator",
    ) -> Dict[str, Any]:
        aid = self.resolve_agent_id(identifier)
        cfg = self.configs[aid]

        if "enabled" in updates and updates["enabled"] is not None:
            cfg.enabled = bool(updates["enabled"])
            if not cfg.enabled:
                cfg.current_status = "Disabled"
            elif cfg.current_status == "Disabled":
                cfg.current_status = "Idle"

        if "provider" in updates and updates["provider"]:
            cfg.provider = str(updates["provider"]).strip().lower()
        if "model" in updates and updates["model"]:
            cfg.model = str(updates["model"]).strip()
        if "timeout_seconds" in updates and updates["timeout_seconds"] is not None:
            timeout_val = int(updates["timeout_seconds"])
            if timeout_val < 1 or timeout_val > 600:
                raise ValueError("timeout_seconds must be between 1 and 600.")
            cfg.timeout_seconds = timeout_val
        if "max_retries" in updates and updates["max_retries"] is not None:
            retries_val = int(updates["max_retries"])
            if retries_val < 0 or retries_val > 10:
                raise ValueError("max_retries must be between 0 and 10.")
            cfg.max_retries = retries_val
        if "temperature" in updates and updates["temperature"] is not None:
            temp_val = float(updates["temperature"])
            if temp_val < 0.0 or temp_val > 2.0:
                raise ValueError("temperature must be between 0.0 and 2.0.")
            cfg.temperature = temp_val
        if "system_instructions" in updates and updates["system_instructions"] is not None:
            cfg.system_instructions = str(updates["system_instructions"]).strip()
        if "allow_image_generation" in updates and updates["allow_image_generation"] is not None:
            cfg.allow_image_generation = bool(updates["allow_image_generation"])

        self._record_activity(
            agent_id=aid,
            event_type="System configuration",
            title=f"{cfg.name} configuration updated by {actor}",
            summary=f"Enabled={cfg.enabled}, Model={cfg.model}, Timeout={cfg.timeout_seconds}s, MaxRetries={cfg.max_retries}",
            severity="normal",
        )
        return self.get_agent_details(aid)

    def set_agent_state(
        self,
        identifier: str,
        action: str,
        actor: str = "operator",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        aid = self.resolve_agent_id(identifier)
        cfg = self.configs[aid]
        previous_status = cfg.current_status

        if action == "enable":
            cfg.enabled = True
            if cfg.current_status == "Disabled":
                cfg.current_status = "Idle"
        elif action == "disable":
            cfg.enabled = False
            cfg.current_status = "Disabled"
        elif action == "pause":
            cfg.current_status = "Paused"
        elif action == "resume":
            cfg.enabled = True
            cfg.current_status = "Idle"
        else:
            raise ValueError(f"Unsupported agent control action: '{action}'")

        self._record_activity(
            agent_id=aid,
            event_type="Agent lifecycle",
            title=f"{cfg.name} {action}d by {actor}",
            summary=reason or f"Transitioned from {previous_status} to {cfg.current_status} (enabled={cfg.enabled}).",
            severity="warning" if action in ("pause", "disable") else "success",
        )
        return {
            "agent_id": aid,
            "name": cfg.name,
            "previous_status": previous_status,
            "current_status": cfg.current_status,
            "enabled": cfg.enabled,
            "updated_by": actor,
            "reason": reason,
            "timestamp": utc_now_iso(),
        }

    async def dispatch_task(
        self,
        task_input: AgentTaskInput,
    ) -> tuple[AgentTaskOutput, QueuedTaskRecord, bool]:
        """
        Routes a single task through the reliable task queue to the target specialist agent,
        recording structured execution logs and activity telemetry.
        """
        aid = self.resolve_agent_id(task_input.agent_id)
        if aid == "agent-orchestrator":
            raise ValueError("Direct specialist task dispatch must target one of the 9 specialist agents.")

        specialist = self.specialists[aid]
        cfg = self.configs[aid]

        # Inherit agent-level timeout & retry configuration when defaults are used
        effective_input = AgentTaskInput(
            task_id=task_input.task_id,
            agent_id=aid,
            stage_name=task_input.stage_name,
            workflow_run_id=task_input.workflow_run_id,
            idempotency_key=task_input.idempotency_key,
            payload=task_input.payload,
            timeout_seconds=task_input.timeout_seconds or cfg.timeout_seconds,
            max_retries=task_input.max_retries if task_input.max_retries is not None else cfg.max_retries,
        )

        output, record, duplicate_prevented = await self.task_queue.execute_with_reliability(
            effective_input,
            specialist.execute,
        )

        if not duplicate_prevented:
            self._record_execution_log(effective_input, output, record.retry_count + 1)
            self._record_activity(
                agent_id=aid,
                event_type=effective_input.stage_name,
                title=f"{cfg.name} finished task {output.task_id} ({output.status})",
                summary=(
                    "; ".join(output.errors)
                    if output.errors
                    else f"Completed stage '{effective_input.stage_name}' in {output.execution_metadata.get('duration_ms', 1)}ms."
                ),
                severity="error" if output.status in ("failed", "dead_letter") else "success",
            )

        return output, record, duplicate_prevented

    async def run_workflow_pipeline(
        self,
        *,
        idempotency_key: str,
        topic_headline: str,
        sources: List[Dict[str, Any]],
        feed_items: Optional[List[Dict[str, Any]]] = None,
        candidate_images: Optional[List[Dict[str, Any]]] = None,
        analytics_connected: bool = False,
        analytics_records: Optional[List[Dict[str, Any]]] = None,
        stage_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the complete 10-stage Orchestrator workflow pipeline:
        1. Trend Scout discovers a story.
        2. Source Collector gathers supporting sources.
        3. Research Agent analyzes the evidence.
        4. Fact Checker evaluates factual claims.
        5. Orchestrator checks verification results (verification_gate).
        6. News Writer creates an original draft.
        7. SEO Agent optimizes the draft.
        8. Media Agent recommends licensed imagery.
        9. Publishing Agent prepares a draft publishing job.
        10. Analytics Agent monitors published content when real analytics become available.

        Each stage saves its result and execution status.
        If a critical stage fails, downstream processing stops immediately and the reason is recorded.
        """
        orch_cfg = self.configs["agent-orchestrator"]
        if not orch_cfg.enabled or orch_cfg.current_status == "Paused":
            raise RuntimeError(
                f"Orchestrator cannot start workflow while status='{orch_cfg.current_status}' (enabled={orch_cfg.enabled})."
            )

        from app.services.operations import get_kill_switch_service
        if await get_kill_switch_service(None):
            raise RuntimeError(
                "EMERGENCY_STOP_ENGAGED: Cannot start workflow while global emergency kill switch is engaged."
            )

        # Duplicate workflow run prevention via idempotency_key
        if idempotency_key in self._workflow_id_by_idempotency:
            existing_wf_id = self._workflow_id_by_idempotency[idempotency_key]
            existing_run = dict(self.workflow_runs[existing_wf_id])
            existing_run["duplicate_prevented"] = True
            return existing_run

        workflow_run_id = f"wf-{uuid.uuid4().hex[:12]}"
        started_at = utc_now_iso()
        orch_cfg.current_status = "Running"
        orch_cfg.current_task = f"Coordinating workflow {workflow_run_id}: {topic_headline}"

        run_state: Dict[str, Any] = {
            "workflow_run_id": workflow_run_id,
            "idempotency_key": idempotency_key,
            "topic_headline": topic_headline,
            "status": "running",
            "current_stage": "trend_discovery",
            "stage_results": {},
            "failure_stage": None,
            "failure_reason": None,
            "duplicate_prevented": False,
            "started_at": started_at,
            "completed_at": None,
        }
        self.workflow_runs[workflow_run_id] = run_state
        self._workflow_id_by_idempotency[idempotency_key] = workflow_run_id
        overrides = stage_overrides or {}

        async def _run_specialist_stage(
            stage_name: str, payload: Dict[str, Any]
        ) -> Optional[AgentTaskOutput]:
            run_state["current_stage"] = stage_name
            merged_payload = {**payload, **(overrides.get(stage_name) or {})}
            specialist = self.select_specialist_for_stage(stage_name)
            task_in = AgentTaskInput(
                task_id=f"{workflow_run_id}-{stage_name}",
                agent_id=specialist.config.agent_id,
                stage_name=stage_name,
                workflow_run_id=workflow_run_id,
                idempotency_key=f"{idempotency_key}:{stage_name}",
                payload=merged_payload,
                timeout_seconds=specialist.config.timeout_seconds,
                max_retries=specialist.config.max_retries,
            )
            out, _, _ = await self.dispatch_task(task_in)
            run_state["stage_results"][stage_name] = out.to_dict()
            if out.status in ("failed", "dead_letter", "cancelled"):
                run_state["status"] = "failed"
                run_state["failure_stage"] = stage_name
                run_state["failure_reason"] = "; ".join(out.errors) or f"Stage '{stage_name}' failed."
                run_state["completed_at"] = utc_now_iso()
                orch_cfg.failure_count += 1
                orch_cfg.current_status = "Idle"
                orch_cfg.last_execution = run_state["completed_at"]
                self._record_activity(
                    agent_id="agent-orchestrator",
                    event_type="Workflow halted",
                    title=f"Workflow {workflow_run_id} halted at {stage_name}",
                    summary=str(run_state["failure_reason"]),
                    severity="error",
                )
                return None
            return out

        # Stage 1: Trend Scout discovers a story
        s1 = await _run_specialist_stage(
            "trend_discovery",
            {"topic_headline": topic_headline, "feed_items": feed_items or []},
        )
        if s1 is None:
            return run_state

        discovered_headline = (
            (s1.result.get("primary_candidate") or {}).get("headline") or topic_headline
        )

        # Stage 2: Source Collector gathers supporting sources
        s2 = await _run_specialist_stage(
            "source_collection",
            {"sources": sources},
        )
        if s2 is None:
            return run_state

        collected_sources = s2.result.get("collected_sources") or []

        # Stage 3: Research Agent analyzes the evidence
        s3 = await _run_specialist_stage(
            "evidence_research",
            {"collected_sources": collected_sources},
        )
        if s3 is None:
            return run_state

        extracted_claims = s3.result.get("extracted_claims") or []

        # Stage 4: Fact Checker evaluates factual claims
        s4 = await _run_specialist_stage(
            "fact_checking",
            {"claims": extracted_claims},
        )
        if s4 is None:
            return run_state

        # Stage 5: Orchestrator checks verification results (Verification Gate)
        run_state["current_stage"] = "verification_gate"
        verification_report = s4.result.get("verification_report") or []
        verified_count = int(s4.result.get("verified_count") or 0)
        disputed_count = int(s4.result.get("disputed_count") or 0)
        unsupported_count = int(s4.result.get("unsupported_count") or 0)

        gate_passed = verified_count > 0 and disputed_count == 0 and unsupported_count == 0
        gate_started = utc_now_iso()
        gate_output = AgentTaskOutput(
            task_id=f"{workflow_run_id}-verification_gate",
            agent_id="agent-orchestrator",
            status="completed" if gate_passed else "failed",
            result={
                "verification_gate_passed": gate_passed,
                "verified_claims_count": verified_count,
                "disputed_claims_count": disputed_count,
                "unsupported_claims_count": unsupported_count,
            },
            errors=(
                []
                if gate_passed
                else [
                    f"Orchestrator verification gate halted pipeline: verified={verified_count}, "
                    f"disputed={disputed_count}, unsupported={unsupported_count}."
                ]
            ),
            started_at=gate_started,
            completed_at=utc_now_iso(),
            execution_metadata={
                "stage_name": "verification_gate",
                "workflow_run_id": workflow_run_id,
                "idempotency_key": f"{idempotency_key}:verification_gate",
            },
        )
        run_state["stage_results"]["verification_gate"] = gate_output.to_dict()

        if not gate_passed:
            run_state["status"] = "halted_verification"
            run_state["failure_stage"] = "verification_gate"
            run_state["failure_reason"] = gate_output.errors[0]
            run_state["completed_at"] = utc_now_iso()
            orch_cfg.failure_count += 1
            orch_cfg.current_status = "Idle"
            orch_cfg.last_execution = run_state["completed_at"]
            self._record_activity(
                agent_id="agent-orchestrator",
                event_type="Verification gate halted",
                title=f"Orchestrator halted {workflow_run_id} at verification_gate",
                summary=run_state["failure_reason"],
                severity="error",
            )
            return run_state

        # Stage 6: News Writer creates an original draft
        s6 = await _run_specialist_stage(
            "article_drafting",
            {
                "headline": discovered_headline,
                "verified_claims": verification_report,
                "collected_sources": collected_sources,
            },
        )
        if s6 is None:
            return run_state

        # Stage 7: SEO Agent optimizes the draft
        s7 = await _run_specialist_stage(
            "seo_optimization",
            {
                "headline": s6.result.get("headline", discovered_headline),
                "body_markdown": s6.result.get("body_markdown", ""),
            },
        )
        if s7 is None:
            return run_state

        # Stage 8: Media Agent recommends licensed imagery
        media_payload = {"headline": discovered_headline}
        if candidate_images is not None:
            media_payload["candidate_images"] = candidate_images
        s8 = await _run_specialist_stage("media_licensing", media_payload)
        if s8 is None:
            return run_state

        # Stage 9: Publishing Agent prepares a draft publishing job
        s9 = await _run_specialist_stage(
            "publishing_preparation",
            {
                "headline": s6.result.get("headline", discovered_headline),
                "slug": s7.result.get("suggested_slug") or s6.result.get("slug"),
                "body_markdown": s6.result.get("body_markdown", ""),
                "seo_metadata": s7.result,
                "recommended_images": s8.result.get("recommended_images", []),
                "trend_score": float(run_state.get("trend_score", 75.0)),
                "collected_sources": collected_sources,
                "editorial_quality_score": s6.result.get("editorial_quality_score", {}),
                "conflicts_count": disputed_count + unsupported_count,
                "editorial_approved": False,
                "auto_publish": False,
            },
        )
        if s9 is None:
            return run_state

        # Stage 10: Analytics Agent monitors published content when real analytics become available
        s10 = await _run_specialist_stage(
            "analytics_monitoring",
            {
                "analytics_connected": analytics_connected,
                "analytics_records": analytics_records or [],
            },
        )
        if s10 is None:
            return run_state

        run_state["status"] = "completed"
        run_state["completed_at"] = utc_now_iso()
        orch_cfg.success_count += 1
        orch_cfg.current_status = "Idle"
        orch_cfg.last_execution = run_state["completed_at"]
        orch_cfg.current_task = f"Completed 10-stage workflow {workflow_run_id}"

        self._record_activity(
            agent_id="agent-orchestrator",
            event_type="Workflow completed",
            title=f"10-stage workflow completed for '{discovered_headline}'",
            summary="Draft staged in manual approval queue; analytics status recorded.",
            severity="success",
        )
        return run_state

    def _record_execution_log(
        self,
        task_input: AgentTaskInput,
        output: AgentTaskOutput,
        attempts: int,
    ) -> None:
        entry = {
            "id": f"log-{uuid.uuid4().hex[:10]}",
            "task_id": output.task_id,
            "workflow_run_id": task_input.workflow_run_id,
            "agent_id": output.agent_id,
            "stage_name": task_input.stage_name,
            "attempts": attempts,
            "status": output.status,
            "input_payload": task_input.payload,
            "output": output.to_dict(),
            "created_at": output.completed_at,
        }
        self.execution_logs.insert(0, entry)

    def _record_activity(
        self,
        *,
        agent_id: str,
        event_type: str,
        title: str,
        summary: str,
        severity: str = "normal",
    ) -> None:
        cfg = self.configs.get(agent_id)
        event = {
            "id": f"act-{uuid.uuid4().hex[:10]}",
            "agent_id": agent_id,
            "agent_name": cfg.name if cfg else agent_id,
            "event_type": event_type,
            "title": title,
            "summary": summary,
            "severity": severity,
            "timestamp": utc_now_iso(),
        }
        self.activity_events.insert(0, event)

    def get_system_overview(self) -> Dict[str, Any]:
        provider_status = self.provider_adapter.get_status()
        agents_list = self.list_all_agents()
        enabled_count = sum(1 for a in agents_list if a["enabled"])
        specialist_count = sum(1 for a in agents_list if not a["is_orchestrator"])
        return {
            "orchestrator": self.get_agent_details("agent-orchestrator"),
            "specialist_count": specialist_count,
            "total_registered_agents": len(agents_list),
            "enabled_agents_count": enabled_count,
            "provider_status": {
                "provider": provider_status.provider_name,
                "model": provider_status.model_name,
                "connected": provider_status.is_connected,
                "status_label": provider_status.status_label,
                "env_var_checked": provider_status.env_var_checked,
            },
            "queue": self.task_queue.get_queue_stats(),
            "workflow_runs_count": len(self.workflow_runs),
            "recent_activity": self.activity_events[:25],
        }


# Global singleton Orchestrator instance for the FastAPI control plane
orchestrator_engine = OrchestratorAgent()
