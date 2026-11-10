"""
NEXUS MEDIA AI — Section 3 Feature Verification Tests:
1. Article generation pipeline end to end using existing agents/orchestrator
2. Human-quality writing rules, source citations, AI disclosure, and 6-pillar quality scoring (>= 85 threshold)
3. Publishing modes: manual vs auto (trend >= 60, sources >= 3, quality >= 85, no conflicts, kill switch disengaged)
4. Global kill switch: DB/memory state, API exposure, blocking publishing and agent workflows
5. Social adapters: honest "not_connected" state when credentials missing
6. Scheduler: 300s replay window, HMAC verification, overlap prevention
"""

import asyncio
import json
import time
from typing import Any, Dict
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.orchestrator import orchestrator_engine
from app.agents.provider import AIProviderAdapter
from app.agents.specialists import NewsWriterAgent, score_editorial_quality
from app.config import get_settings
from app.main import create_app
from app.publishing.blog_client import sign_request
from app.publishing.social import FacebookPageAdapter, XTwitterAdapter
from app.services.operations import get_kill_switch_service, set_kill_switch_service
from app.services.pipeline import run_autonomous_editorial_pipeline


class Section3FeaturesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        # Ensure kill switch is disengaged before each test
        asyncio.run(set_kill_switch_service(None, False, "test_setup"))

    def test_01_ai_provider_gemini_and_mock_fallback(self) -> None:
        # Without API key, provider honestly reports not connected
        adapter_no_key = AIProviderAdapter(provider_name="gemini", env_override={})
        status_no_key = adapter_no_key.get_status()
        self.assertFalse(status_no_key.is_connected)
        self.assertEqual(status_no_key.status_label, "PROVIDER_NOT_CONNECTED")

        # Fallback text generation works deterministically and without throwing exceptions
        text = asyncio.run(adapter_no_key.generate_text("Headline: Quantum Computing Benchmark"))
        self.assertIn("Quantum Computing Benchmark", text)
        self.assertTrue(len(text) > 50)

        # When API key is provided, provider reports connected
        adapter_with_key = AIProviderAdapter(
            provider_name="gemini",
            env_override={"AI_PROVIDER_API_KEY": "AIzaSyRealSimulatedKey123"},
        )
        status_with_key = adapter_with_key.get_status()
        self.assertTrue(status_with_key.is_connected)
        self.assertEqual(status_with_key.status_label, "PROVIDER_CONNECTED")

    def test_02_human_quality_writing_rules_and_quality_score(self) -> None:
        sources = [
            {"url": "https://reuters.com/wire/1", "title": "Wire Source 1", "publisher": "Reuters"},
            {"url": "https://bloomberg.com/wire/2", "title": "Wire Source 2", "publisher": "Bloomberg"},
            {"url": "https://wsj.com/wire/3", "title": "Wire Source 3", "publisher": "Wall Street Journal"},
        ]
        verified_claims = [
            {
                "claim_text": "Foundry wafers demonstrated an 82% defect-free yield.",
                "supporting_sources": ["https://reuters.com/wire/1"],
                "publisher": "Reuters",
                "classification": "verified",
            },
            {
                "claim_text": "Capital expenditure expanded by 14% year-over-year.",
                "supporting_sources": ["https://bloomberg.com/wire/2"],
                "publisher": "Bloomberg",
                "classification": "verified",
            },
        ]

        writer_agent = orchestrator_engine.select_specialist_for_stage("article_drafting")
        from app.agents.schemas import AgentTaskInput
        task_in = AgentTaskInput(
            task_id="test-writing-task-01",
            agent_id="agent-news-writer",
            stage_name="article_drafting",
            workflow_run_id="wf-test-01",
            idempotency_key="key-test-01",
            payload={
                "headline": "Commercial Foundry Yield Reaches Milestone",
                "verified_claims": verified_claims,
                "collected_sources": sources,
            },
        )
        output = asyncio.run(writer_agent.execute(task_in))
        self.assertEqual(output.status, "completed")
        res = output.result

        body = res["body_markdown"]
        # Rule 1: Source citations with markdown links
        self.assertIn("[Reuters](https://reuters.com/wire/1)", body)
        self.assertIn("[Bloomberg](https://bloomberg.com/wire/2)", body)

        # Rule 2: Mandatory AI-assistance disclosure paragraph
        self.assertIn("Editorial Disclosure:", body)
        self.assertIn("NEXUS MEDIA AI", body)

        # Rule 3: 6-pillar editorial quality score computed
        quality = res["editorial_quality_score"]
        self.assertIn("accuracy", quality)
        self.assertIn("originality", quality)
        self.assertIn("readability", quality)
        self.assertIn("research_depth", quality)
        self.assertIn("natural_flow", quality)
        self.assertIn("audience_value", quality)
        self.assertIn("total_score", quality)

        # Should achieve >= 85
        self.assertGreaterEqual(quality["total_score"], 85)
        self.assertTrue(res["passes_quality_threshold"])

    def test_03_publishing_modes_manual_vs_auto(self) -> None:
        pub_agent = orchestrator_engine.select_specialist_for_stage("publishing_preparation")
        from app.agents.schemas import AgentTaskInput

        # 1. Manual mode: staged as "Awaiting Approval"
        task_manual = AgentTaskInput(
            task_id="test-pub-manual",
            agent_id="agent-publishing",
            stage_name="publishing_preparation",
            workflow_run_id="wf-test-pub",
            idempotency_key="pub-idem-manual",
            payload={
                "headline": "Test Story",
                "slug": "test-story",
                "body_markdown": "# Test Story\n\n## Overview\nValid body content here.",
                "publishing_mode": "manual",
                "trend_score": 90.0,
                "editorial_quality_score": {"total_score": 92},
                "collected_sources": [{"publisher": f"Pub {i}", "url": f"https://example.com/{i}"} for i in range(4)],
                "conflicts_count": 0,
                "kill_switch_engaged": False,
            },
        )
        out_manual = asyncio.run(pub_agent.execute(task_manual))
        self.assertEqual(out_manual.status, "completed")
        self.assertEqual(out_manual.result["queue_stage"], "Awaiting Approval")
        self.assertFalse(out_manual.result["auto_published"])

        # 2. Auto mode: all 5 conditions satisfied -> stage is "Scheduled" / auto-published
        task_auto_pass = AgentTaskInput(
            task_id="test-pub-auto-pass",
            agent_id="agent-publishing",
            stage_name="publishing_preparation",
            workflow_run_id="wf-test-pub",
            idempotency_key="pub-idem-auto-pass",
            payload={
                "headline": "Test Story",
                "slug": "test-story",
                "body_markdown": "# Test Story\n\n## Overview\nValid body content here.",
                "publishing_mode": "auto",
                "trend_score": 85.0,  # >= 60
                "editorial_quality_score": {"total_score": 90},  # >= 85
                "collected_sources": [{"publisher": f"Pub {i}", "url": f"https://example.com/{i}"} for i in range(3)],  # >= 3
                "conflicts_count": 0,  # no conflicts
                "kill_switch_engaged": False,  # kill switch off
            },
        )
        out_auto = asyncio.run(pub_agent.execute(task_auto_pass))
        self.assertEqual(out_auto.status, "completed")
        self.assertEqual(out_auto.result["queue_stage"], "Scheduled")
        self.assertTrue(out_auto.result["auto_published"])

        # 3. Auto mode but quality < 85 -> blocked, staged as "Awaiting Approval"
        task_auto_low_quality = AgentTaskInput(
            task_id="test-pub-auto-low-q",
            agent_id="agent-publishing",
            stage_name="publishing_preparation",
            workflow_run_id="wf-test-pub",
            idempotency_key="pub-idem-auto-low-q",
            payload={
                "headline": "Test Story",
                "slug": "test-story",
                "body_markdown": "# Test Story\n\n## Overview\nValid body content here.",
                "publishing_mode": "auto",
                "trend_score": 85.0,
                "editorial_quality_score": {"total_score": 78},  # < 85!
                "collected_sources": [{"publisher": f"Pub {i}", "url": f"https://example.com/{i}"} for i in range(3)],
                "conflicts_count": 0,
                "kill_switch_engaged": False,
            },
        )
        out_low_q = asyncio.run(pub_agent.execute(task_auto_low_quality))
        self.assertEqual(out_low_q.status, "completed")
        self.assertEqual(out_low_q.result["queue_stage"], "Awaiting Approval")
        self.assertFalse(out_low_q.result["auto_published"])
        self.assertIn("Editorial quality (78) < 85", out_low_q.result["status_summary"])

    def test_04_kill_switch_api_and_publishing_block(self) -> None:
        # Check initial state: disengaged
        res_get = self.client.get("/api/system/kill-switch")
        self.assertEqual(res_get.status_code, 200)
        self.assertFalse(res_get.json()["kill_switch_engaged"])
        self.assertEqual(res_get.json()["status"], "disengaged")

        # Acquire admin token for POST /api/system/kill-switch
        login_res = self.client.post("/api/auth/login", json={"email": "admin@nexusmedia.ai", "password": "AdminPass123!"})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Engage kill switch
        res_engage = self.client.post("/api/system/kill-switch", json={"engaged": True, "reason": "Emergency testing"}, headers=headers)
        self.assertEqual(res_engage.status_code, 200)
        self.assertTrue(res_engage.json()["kill_switch_engaged"])
        self.assertEqual(res_engage.json()["status"], "engaged")

        # Check that publishing is now blocked with 409 Conflict
        res_pub = self.client.post("/api/blog/publish/some-article-id", headers=headers)
        self.assertEqual(res_pub.status_code, 409)
        self.assertEqual(res_pub.json()["detail"]["code"], "KILL_SWITCH_ENGAGED")

        # Disengage kill switch
        res_disengage = self.client.post("/api/system/kill-switch", json={"engaged": False, "reason": "Test ended"}, headers=headers)
        self.assertEqual(res_disengage.status_code, 200)
        self.assertFalse(res_disengage.json()["kill_switch_engaged"])

    def test_05_social_adapters_honest_not_connected_state(self) -> None:
        twitter = XTwitterAdapter(env={})
        self.assertFalse(twitter.is_connected())
        pub_res = asyncio.run(twitter.publish({"title": "Test Tweet", "url": "https://blog.example.com"}))
        self.assertEqual(pub_res["status"], "not_connected")
        self.assertIn("TWITTER_API_KEY", pub_res["message"])

        fb = FacebookPageAdapter(env={})
        self.assertFalse(fb.is_connected())
        fb_res = asyncio.run(fb.publish({"title": "Test FB Post", "url": "https://blog.example.com"}))
        self.assertEqual(fb_res["status"], "not_connected")
        self.assertIn("FACEBOOK_PAGE_ID", fb_res["message"])

    def test_06_scheduler_hmac_replay_window_and_overlap_protection(self) -> None:
        settings = get_settings()
        secret = settings.CLOUDFLARE_WEBHOOK_SECRET or "test-webhook-secret-xyz"
        body = json.dumps({"trigger": "cloudflare_cron", "cron": "*/30 * * * *"})

        # Valid timestamp: accepted (or returns scan result / 409 if overlap, but NOT 401)
        now_ts = str(int(time.time()))
        valid_sig = sign_request(secret, now_ts, "", body)
        with patch.object(settings, "CLOUDFLARE_WEBHOOK_SECRET", secret):
            res_valid = self.client.post(
                "/api/webhooks/cron/news-scan",
                data=body,
                headers={"X-Nexus-Timestamp": now_ts, "X-Nexus-Signature": valid_sig, "Content-Type": "application/json"},
            )
            # Should be accepted (200 or 409 for scan overlap deduplication, NOT 401 unauthorized)
            self.assertIn(res_valid.status_code, (200, 409))

            # Timestamp older than 300 seconds -> rejected with 401 BAD_SIGNATURE
            old_ts = str(int(time.time()) - 350)
            old_sig = sign_request(secret, old_ts, "", body)
            res_expired = self.client.post(
                "/api/webhooks/cron/news-scan",
                data=body,
                headers={"X-Nexus-Timestamp": old_ts, "X-Nexus-Signature": old_sig, "Content-Type": "application/json"},
            )
            self.assertEqual(res_expired.status_code, 401)
            self.assertEqual(res_expired.json()["detail"]["code"], "BAD_SIGNATURE")

    def test_07_end_to_end_autonomous_pipeline(self) -> None:
        # Run autonomous pipeline end to end (mock AI provider)
        result = asyncio.run(run_autonomous_editorial_pipeline())
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertEqual(result["stage"], "Awaiting Approval")
        self.assertGreaterEqual(result["word_count"], 150)
        self.assertGreaterEqual(result["quality_score"], 85)
        self.assertIn("image", result)
        self.assertEqual(result["image"]["provider"], "Wikimedia Commons")


if __name__ == "__main__":
    unittest.main()
