"""
NEXUS MEDIA AI — Step 4 Multi-Agent Intelligence System Automated Test Suite
Covers all 10 required test categories using mock model responses (zero real API credits spent):
1. Agent registration (1 Central Orchestrator + 9 Specialist Agents)
2. Agent configuration & AI provider abstraction
3. Orchestrator task assignment & 10-stage workflow routing
4. Structured AgentTaskInput / AgentTaskOutput schemas & code-injection rejection
5. Failed agent execution & specialist domain guardrails
6. Retry limits & Dead-Letter Queue (DLQ) transition
7. Task cancellation
8. Duplicate task & workflow idempotency prevention
9. Workflow failure handling & verification gate halting
10. Database models & incremental migration verification
"""

import asyncio
from pathlib import Path
import sys
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.orchestrator import (  # noqa: E402
    PIPELINE_STAGES_ORDER,
    OrchestratorAgent,
)
from app.agents.provider import AIProviderAdapter  # noqa: E402
from app.agents.queue import ReliableTaskQueue  # noqa: E402
from app.agents.schemas import (  # noqa: E402
    AgentTaskInput,
    AgentTaskOutput,
    assert_safe_json_payload,
)


class MultiAgentIntelligenceSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        # Use deterministic mock provider so zero real API credits are ever spent
        self.mock_provider = AIProviderAdapter(
            provider_name="mock",
            model_name="mock-deterministic-v1",
            mock_responder=lambda slug, payload: {"mock_agent": slug, "echo": bool(payload)},
        )
        self.orchestrator = OrchestratorAgent(
            provider_adapter=self.mock_provider,
            task_queue=ReliableTaskQueue(),
        )

    def test_01_agent_registration_orchestrator_and_nine_specialists(self) -> None:
        agents = self.orchestrator.list_all_agents()
        self.assertEqual(len(agents), 10, "Must register 1 Orchestrator + 9 Specialist Agents")

        expected_specialist_ids = {
            "agent-trend-scout",
            "agent-source-collector",
            "agent-research",
            "agent-fact-checker",
            "agent-news-writer",
            "agent-seo",
            "agent-media",
            "agent-publishing",
            "agent-analytics",
        }
        registered_specialists = set(self.orchestrator.specialists.keys())
        self.assertEqual(registered_specialists, expected_specialist_ids)

        # Specialist agents must never independently publish content
        for spec_agent in self.orchestrator.specialists.values():
            self.assertFalse(spec_agent.can_publish_directly)

    def test_02_agent_configuration_and_provider_abstraction(self) -> None:
        updated = self.orchestrator.update_agent_config(
            "agent-fact-checker",
            {
                "enabled": True,
                "provider": "gemini",
                "model": "gemini-2.5-pro",
                "timeout_seconds": 75,
                "max_retries": 4,
                "temperature": 0.0,
                "system_instructions": "Strict primary source verification only.",
            },
            actor="admin-test",
        )
        self.assertEqual(updated["timeout_seconds"], 75)
        self.assertEqual(updated["max_retries"], 4)
        self.assertEqual(updated["temperature"], 0.0)
        self.assertEqual(updated["system_instructions"], "Strict primary source verification only.")

        # Verify disconnected provider when no API key is present in environment
        unconnected_provider = AIProviderAdapter(
            provider_name="gemini",
            env_override={"AI_PROVIDER_API_KEY": "", "GEMINI_API_KEY": ""},
        )
        status = unconnected_provider.get_status()
        self.assertFalse(status.is_connected)
        self.assertEqual(status.status_label, "PROVIDER_NOT_CONNECTED")

    def test_03_structured_agent_communication_schemas_and_code_safety(self) -> None:
        # Reject arbitrary callable or executable code strings
        with self.assertRaises(ValueError):
            assert_safe_json_payload({"malicious": "eval('os.system(\"rm -rf /\")')"})

        with self.assertRaises(ValueError):
            assert_safe_json_payload({"fn": lambda x: x})

        # Valid task execution must return all 8 required AgentTaskOutput fields
        task_in = AgentTaskInput(
            task_id="tsk-schema-01",
            agent_id="agent-trend-scout",
            stage_name="trend_discovery",
            idempotency_key="idem-schema-01",
            payload={
                "feed_items": [
                    {
                        "title": "European Grid Operators Approve 4GW Offshore HVDC Interconnect",
                        "source_name": "ENTSO-E Regulatory Wire",
                        "feed_url": "https://www.entsoe.eu/news/",
                        "relevance_hint": 93,
                    }
                ]
            },
        )
        output, _, _ = asyncio.run(self.orchestrator.dispatch_task(task_in))
        self.assertIsInstance(output, AgentTaskOutput)
        dumped = output.to_dict()
        for required_key in (
            "task_id",
            "agent_id",
            "status",
            "result",
            "errors",
            "started_at",
            "completed_at",
            "execution_metadata",
        ):
            self.assertIn(required_key, dumped)
        self.assertEqual(output.status, "completed")

    def test_04_specialist_domain_guardrails_and_failed_execution(self) -> None:
        # 1. Fact Checker must NEVER mark a claim verified without supporting evidence
        fc_input = AgentTaskInput(
            task_id="tsk-fc-unverified",
            agent_id="agent-fact-checker",
            stage_name="fact_checking",
            idempotency_key="idem-fc-unverified",
            payload={
                "claims": [
                    {
                        "claim_text": "Unverified rumor with zero sources",
                        "supporting_sources": [],
                        "evidence_excerpt": "",
                    }
                ]
            },
        )
        fc_out, _, _ = asyncio.run(self.orchestrator.dispatch_task(fc_input))
        self.assertEqual(fc_out.result["verified_count"], 0)
        self.assertEqual(fc_out.result["unsupported_count"], 1)
        self.assertEqual(
            fc_out.result["verification_report"][0]["classification"],
            "unsupported",
        )

        # 2. Source Collector must fail rather than invent sources when none are provided
        sc_input = AgentTaskInput(
            task_id="tsk-sc-empty",
            agent_id="agent-source-collector",
            stage_name="source_collection",
            idempotency_key="idem-sc-empty",
            payload={"sources": []},
            max_retries=0,
        )
        sc_out, _, _ = asyncio.run(self.orchestrator.dispatch_task(sc_input))
        self.assertIn(sc_out.status, ("failed", "dead_letter"))

        # 3. Media Agent must reject AI image generation when allow_image_generation is False
        media_input = AgentTaskInput(
            task_id="tsk-media-gen",
            agent_id="agent-media",
            stage_name="media_licensing",
            idempotency_key="idem-media-gen",
            payload={"request_image_generation": True},
            max_retries=0,
        )
        media_out, _, _ = asyncio.run(self.orchestrator.dispatch_task(media_input))
        self.assertIn(media_out.status, ("failed", "dead_letter"))

        # 4. Analytics Agent must return NOT_CONNECTED when analytics providers are disconnected
        analytics_input = AgentTaskInput(
            task_id="tsk-analytics-disconnected",
            agent_id="agent-analytics",
            stage_name="analytics_monitoring",
            idempotency_key="idem-analytics-disconnected",
            payload={"analytics_connected": False},
        )
        an_out, _, _ = asyncio.run(self.orchestrator.dispatch_task(analytics_input))
        self.assertEqual(an_out.status, "not_connected")
        self.assertEqual(an_out.result["provider_status"], "NOT_CONNECTED")
        self.assertIsNone(an_out.result["website_views"])

    def test_05_retry_limits_and_dead_letter_queue(self) -> None:
        fail_input = AgentTaskInput(
            task_id="tsk-retry-dlq",
            agent_id="agent-research",
            stage_name="evidence_research",
            idempotency_key="idem-retry-dlq",
            payload={
                "simulate_failure": True,
                "simulated_error_message": "Upstream timeout during evidence clustering",
            },
            max_retries=2,
            timeout_seconds=10,
        )
        out, record, dup = asyncio.run(self.orchestrator.dispatch_task(fail_input))
        self.assertFalse(dup)
        self.assertEqual(out.status, "dead_letter")
        self.assertEqual(record.status, "dead_letter")
        self.assertEqual(record.retry_count, 2)
        self.assertEqual(out.execution_metadata["attempts_executed"], 3)

    def test_06_task_cancellation(self) -> None:
        task_in = AgentTaskInput(
            task_id="tsk-cancel-01",
            agent_id="agent-seo",
            stage_name="seo_optimization",
            idempotency_key="idem-cancel-01",
            payload={"headline": "Test Headline", "body_markdown": "# Test\n\n## Section\nBody"},
        )
        record, _ = self.orchestrator.task_queue.submit_task(task_in)
        cancelled_rec = self.orchestrator.task_queue.cancel_task(
            record.task_id, reason="Cancelled by unit test"
        )
        self.assertEqual(cancelled_rec.status, "cancelled")

        # Attempting to execute a cancelled task returns status='cancelled' immediately
        out, _, _ = asyncio.run(self.orchestrator.dispatch_task(task_in))
        self.assertEqual(out.status, "cancelled")

    def test_07_duplicate_task_prevention_idempotency(self) -> None:
        task_in = AgentTaskInput(
            task_id="tsk-idem-orig",
            agent_id="agent-trend-scout",
            stage_name="trend_discovery",
            idempotency_key="unique-story-key-2026",
            payload={"topic_headline": "Global Wafer Fab Capacity Expansion Report"},
        )
        out1, _, dup1 = asyncio.run(self.orchestrator.dispatch_task(task_in))
        self.assertFalse(dup1)
        self.assertEqual(out1.status, "completed")

        # Second dispatch with same idempotency_key must prevent duplicate execution
        out2, _, dup2 = asyncio.run(self.orchestrator.dispatch_task(task_in))
        self.assertTrue(dup2)
        self.assertEqual(out1.task_id, out2.task_id)

    def test_08_full_10_stage_orchestrator_workflow_and_failure_halt(self) -> None:
        # 1. Successful 10-stage workflow execution
        wf_result = asyncio.run(
            self.orchestrator.run_workflow_pipeline(
                idempotency_key="wf-idem-success-01",
                topic_headline="Sub-2nm Gate-All-Around Foundry Yield Reaches Commercial Threshold",
                sources=[
                    {
                        "url": "https://www.sec.gov/Archives/edgar/data/foundry-q3-filing.htm",
                        "title": "Q3 Foundry Operations Disclosure",
                        "publisher": "SEC EDGAR Filing",
                        "published_at": "2026-11-09T10:00:00Z",
                        "reliability_tier": "Tier 1 Primary",
                        "factual_statements": [
                            "Gate-all-around test wafers achieved 82% defect-free yield across 300mm lots."
                        ],
                    },
                    {
                        "url": "https://semi.org/en/news-resources/fab-report-2026",
                        "title": "SEMI Global Fab Equipment Report",
                        "publisher": "SEMI Industry Association",
                        "published_at": "2026-11-09T12:00:00Z",
                        "reliability_tier": "Tier 1 Primary",
                        "factual_statements": [
                            "High-NA EUV lithography tool installations rose 24% year-over-year."
                        ],
                    },
                ],
                analytics_connected=False,
            )
        )
        self.assertEqual(wf_result["status"], "completed")
        for stage in PIPELINE_STAGES_ORDER:
            self.assertIn(stage, wf_result["stage_results"])

        # Verify Publishing Agent used draft_manual_approval mode and did not auto-publish
        pub_stage = wf_result["stage_results"]["publishing_preparation"]["result"]
        self.assertEqual(pub_stage["publishing_mode"], "draft_manual_approval")
        self.assertFalse(pub_stage["auto_published"])

        # Verify Analytics Agent returned NOT_CONNECTED honestly
        analytics_stage = wf_result["stage_results"]["analytics_monitoring"]
        self.assertEqual(analytics_stage["status"], "not_connected")
        self.assertEqual(analytics_stage["result"]["provider_status"], "NOT_CONNECTED")

        # 2. Workflow failure handling: contradicted claim halts at verification_gate and stops downstream stages
        wf_halted = asyncio.run(
            self.orchestrator.run_workflow_pipeline(
                idempotency_key="wf-idem-halted-02",
                topic_headline="Disputed Merger Valuation Rumor",
                sources=[
                    {
                        "url": "https://example.org/filing-1",
                        "title": "Filing 1",
                        "publisher": "Regulatory Wire",
                        "factual_statements": ["Claim A"],
                    }
                ],
                stage_overrides={
                    "fact_checking": {
                        "claims": [
                            {
                                "claim_text": "Contradicted claim without corroboration",
                                "supporting_sources": ["https://example.org/filing-1"],
                                "evidence_excerpt": "Claim A",
                                "contradicted": True,
                            }
                        ]
                    }
                },
            )
        )
        self.assertEqual(wf_halted["status"], "halted_verification")
        self.assertEqual(wf_halted["failure_stage"], "verification_gate")
        # Downstream stages (article_drafting, seo_optimization, publishing_preparation) must NOT run
        self.assertNotIn("article_drafting", wf_halted["stage_results"])
        self.assertNotIn("publishing_preparation", wf_halted["stage_results"])

    def test_09_database_migration_and_models_exist(self) -> None:
        repo_root = BACKEND_ROOT.parent
        step4_migration = (
            repo_root
            / "supabase"
            / "migrations"
            / "20261109000002_nexus_media_ai_multi_agent_system.sql"
        )
        if not step4_migration.exists():
            step4_migration = (
                repo_root.parent
                / "4-database-supabase"
                / "migrations"
                / "20261109000002_nexus_media_ai_multi_agent_system.sql"
            )
        self.assertTrue(step4_migration.exists())
        sql_text = step4_migration.read_text(encoding="utf-8")
        for table_name in (
            "public.agents",
            "public.agent_configs",
            "public.agent_tasks",
            "public.workflow_runs",
            "public.agent_execution_logs",
        ):
            self.assertIn(table_name, sql_text)


if __name__ == "__main__":
    unittest.main()
