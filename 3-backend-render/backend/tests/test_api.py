"""
NEXUS MEDIA AI — FastAPI Integration Test Suite (Pytest + Unittest compatible)
Covers:
1. Health endpoint (/api/system/health)
2. Database unavailable state (/api/system/health/database & graceful GET/POST handling)
3. Invalid request handling (422 validation errors)
4. Authentication protection (401 on missing/invalid bearer token)
5. Agent endpoint authorization (403 on insufficient role, 503 when DB unconfigured for valid operator)
6. Article endpoint validation (slug format, length constraints, role checks)
7. CORS configuration (restricted to configured dashboard origin)
"""

import os
from pathlib import Path
import sys
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Ensure deterministic test environment before importing app
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = ""
os.environ["JWT_SECRET"] = "test-only-jwt-secret-key-for-nexus-media-ai-pytest-32b"
os.environ["ADMIN_ORIGIN"] = "http://localhost:3000"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"

try:
    import pytest
    from fastapi.testclient import TestClient
    from app.main import create_app

    FASTAPI_RUNTIME_AVAILABLE = True
except ImportError:  # pragma: no cover
    pytest = None  # type: ignore
    TestClient = object  # type: ignore
    create_app = None  # type: ignore
    FASTAPI_RUNTIME_AVAILABLE = False

from app.security.auth import create_access_token  # noqa: E402


if FASTAPI_RUNTIME_AVAILABLE and pytest is not None:

    @pytest.fixture()
    def client() -> TestClient:
        app = create_app()
        return TestClient(app)


@unittest.skipUnless(FASTAPI_RUNTIME_AVAILABLE, "FastAPI TestClient requires requirements.txt installed")
class FastApiEndpointIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_system_health_endpoint(self) -> None:
        response = self.client.get("/api/system/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload,
            {
                "application": "NEXUS MEDIA AI",
                "status": "online",
                "database": "not_configured",
                "environment": "development",
                "version": "0.1.0",
            },
        )
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")

    def test_database_unavailable_state(self) -> None:
        db_resp = self.client.get("/api/system/health/database")
        self.assertEqual(db_resp.status_code, 200)
        body = db_resp.json()
        self.assertEqual(body["status"], "not_configured")
        self.assertFalse(body["configured"])

        agents_resp = self.client.get("/api/agents")
        self.assertEqual(agents_resp.status_code, 200)
        self.assertEqual(agents_resp.json()["database_status"], "not_configured")
        self.assertEqual(agents_resp.json()["items"], [])

        single_agent = self.client.get("/api/agents/agent-trend-scout")
        self.assertEqual(single_agent.status_code, 503)

    def test_invalid_request_handling(self) -> None:
        resp = self.client.get("/api/agents?page=0&page_size=500")
        self.assertEqual(resp.status_code, 422)
        body = resp.json()
        self.assertEqual(body["error"], "VALIDATION_ERROR")

    def test_authentication_protection(self) -> None:
        for method, path in [
            ("POST", "/api/agents/agent-trend-scout/pause"),
            ("POST", "/api/agents/agent-trend-scout/resume"),
            ("POST", "/api/agents/agent-trend-scout/enable"),
            ("POST", "/api/agents/agent-trend-scout/disable"),
            ("POST", "/api/articles"),
            ("POST", "/api/articles/art-1/approve"),
            ("POST", "/api/articles/art-1/publish"),
            ("GET", "/api/publishing/jobs"),
            ("GET", "/api/analytics/traffic"),
            ("GET", "/api/analytics/revenue"),
            ("GET", "/api/logs"),
        ]:
            response = self.client.request(method, path)
            self.assertEqual(response.status_code, 401, f"Expected 401 for {method} {path}")

    def test_agent_endpoint_authorization(self) -> None:
        viewer_token = create_access_token(
            user_id="user-viewer-1",
            email="viewer@nexusmedia.ai",
            roles=["viewer"],
        )
        operator_token = create_access_token(
            user_id="user-operator-1",
            email="operator@nexusmedia.ai",
            roles=["operator"],
        )

        forbidden = self.client.post(
            "/api/agents/agent-trend-scout/pause",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={"reason": "Routine maintenance"},
        )
        self.assertEqual(forbidden.status_code, 403)

        allowed = self.client.post(
            "/api/agents/agent-trend-scout/pause",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={"reason": "Routine maintenance"},
        )
        self.assertEqual(allowed.status_code, 503)
        self.assertEqual(allowed.json()["detail"]["code"], "DATABASE_UNAVAILABLE")

    def test_article_endpoint_validation(self) -> None:
        fact_checker_token = create_access_token(
            user_id="user-editor-1",
            email="factchecker@nexusmedia.ai",
            roles=["fact_checker"],
        )

        invalid_resp = self.client.post(
            "/api/articles",
            headers={"Authorization": f"Bearer {fact_checker_token}"},
            json={
                "title": "Short",
                "slug": "Invalid Slug With Spaces!",
                "body_markdown": "Too short.",
            },
        )
        self.assertEqual(invalid_resp.status_code, 422)

        valid_resp = self.client.post(
            "/api/articles",
            headers={"Authorization": f"Bearer {fact_checker_token}"},
            json={
                "title": "Global Sovereign AI Compute Capacity Reaches New Milestone",
                "slug": "global-sovereign-ai-compute-milestone",
                "body_markdown": (
                    "Independent verification across seven regional data center clusters confirms "
                    "new sovereign AI compute deployments have exceeded 4.2 gigawatts of capacity."
                ),
            },
        )
        self.assertEqual(valid_resp.status_code, 503)

        publish_forbidden = self.client.post(
            "/api/articles/art-1/publish",
            headers={"Authorization": f"Bearer {fact_checker_token}"},
        )
        self.assertEqual(publish_forbidden.status_code, 403)

    def test_cors_configuration(self) -> None:
        allowed_origin = self.client.options(
            "/api/system/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(
            allowed_origin.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

        untrusted_origin = self.client.options(
            "/api/system/health",
            headers={
                "Origin": "https://malicious.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIsNone(untrusted_origin.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    unittest.main()
