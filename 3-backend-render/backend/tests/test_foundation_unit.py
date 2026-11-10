"""
NEXUS MEDIA AI — Standard Library Unittest Verification Suite
Executes in any Python 3.10+ environment without requiring external pip packages,
verifying:
1. Password hashing (Argon2/PBKDF2 fallback) & constant-time verification
2. JWT signing, decoding, expiration rejection, and signature tampering rejection
3. Role-based authorization matrix (super_admin, managing_editor, operator, fact_checker, viewer)
4. Configuration normalization & secret redaction summary
5. Complete verification of all 16 required API routes and structural AST contracts
"""

import ast
import os
from pathlib import Path
import sys
import unittest

os.environ["JWT_SECRET"] = "unit-test-secret-signing-key-at-least-32-chars!"

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import AppSettings  # noqa: E402
from app.security.auth import (  # noqa: E402
    ADMIN_ROLES,
    EDITORIAL_ROLES,
    OPERATOR_ROLES,
    create_access_token,
    decode_and_verify_access_token,
    hash_password,
    verify_password,
)


class BackendFoundationUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings(
            APP_ENV="development",
            JWT_SECRET="unit-test-secret-signing-key-at-least-32-chars!",
            DATABASE_URL="",
            ADMIN_ORIGIN="http://localhost:3000",
        )

    def test_password_hashing_and_verification(self) -> None:
        raw_secret = "NexusOperator#2026!Secure"
        digest = hash_password(raw_secret)
        self.assertNotEqual(raw_secret, digest)
        self.assertTrue(verify_password(raw_secret, digest))
        self.assertFalse(verify_password("WrongPassword#2026", digest))

    def test_jwt_lifecycle_and_tamper_protection(self) -> None:
        token = create_access_token(
            user_id="admin-operator-01",
            email="ops@nexusmedia.ai",
            roles=["super_admin", "operator"],
            settings=self.settings,
            expires_delta_seconds=900,
        )
        principal = decode_and_verify_access_token(token, settings=self.settings)
        self.assertEqual(principal.sub, "admin-operator-01")
        self.assertEqual(principal.user_id, "admin-operator-01")
        self.assertEqual(principal.email, "ops@nexusmedia.ai")
        self.assertTrue(principal.has_any_role(ADMIN_ROLES))

        # Tampered signature must fail
        tampered = token[:-4] + "AAAA"
        with self.assertRaises(ValueError):
            decode_and_verify_access_token(tampered, settings=self.settings)

        # Wrong secret key must fail
        wrong_settings = AppSettings(
            JWT_SECRET="different-secret-signing-key-at-least-32-chars!"
        )
        with self.assertRaises(ValueError):
            decode_and_verify_access_token(token, settings=wrong_settings)

        # Expired token must fail
        expired_token = create_access_token(
            user_id="admin-operator-01",
            email="ops@nexusmedia.ai",
            roles=["super_admin"],
            settings=self.settings,
            expires_delta_seconds=-60,
        )
        with self.assertRaises(ValueError):
            decode_and_verify_access_token(expired_token, settings=self.settings)

    def test_role_authorization_sets_and_config_redaction(self) -> None:
        self.assertIn("super_admin", ADMIN_ROLES)
        self.assertIn("managing_editor", ADMIN_ROLES)
        self.assertNotIn("operator", ADMIN_ROLES)
        self.assertIn("operator", OPERATOR_ROLES)
        self.assertIn("fact_checker", EDITORIAL_ROLES)
        self.assertNotIn("viewer", OPERATOR_ROLES)

        redacted = self.settings.redacted_summary()
        self.assertFalse(redacted["database_configured"])
        self.assertTrue(redacted["jwt_secret_configured"])
        self.assertIn("http://localhost:3000", redacted["cors_allowed_origins"])

    def test_all_required_files_and_16_routes_exist(self) -> None:
        required_files = [
            "app/main.py",
            "app/config.py",
            "app/database.py",
            "app/dependencies.py",
            "app/api/health.py",
            "app/api/agents.py",
            "app/api/articles.py",
            "app/api/news.py",
            "app/api/publishing.py",
            "app/api/analytics.py",
            "app/api/logs.py",
            "app/models/entities.py",
            "app/schemas/payloads.py",
            "app/services/operations.py",
            "app/middleware/security_headers.py",
            "app/security/auth.py",
            "requirements.txt",
            "Dockerfile",
            ".env.example",
            "README.md",
        ]
        for rel_path in required_files:
            full_path = BACKEND_ROOT / rel_path
            self.assertTrue(full_path.exists(), f"Missing required backend file: {rel_path}")
            if rel_path.endswith(".py"):
                source = full_path.read_text(encoding="utf-8")
                ast.parse(source, filename=rel_path)

        # Verify all 16 route decorators across app/api/*.py
        expected_routes = [
            ("app/api/health.py", 'prefix="/api/system/health"'),
            ("app/api/health.py", '"/database"'),
            ("app/api/agents.py", 'prefix="/api/agents"'),
            ("app/api/agents.py", '"/{agent_id}"'),
            ("app/api/agents.py", '"/{agent_id}/pause"'),
            ("app/api/agents.py", '"/{agent_id}/resume"'),
            ("app/api/news.py", 'prefix="/api/news"'),
            ("app/api/news.py", '"/{news_id}"'),
            ("app/api/articles.py", 'prefix="/api/articles"'),
            ("app/api/articles.py", '"/{article_id}"'),
            ("app/api/articles.py", '"/{article_id}/approve"'),
            ("app/api/articles.py", '"/{article_id}/publish"'),
            ("app/api/publishing.py", 'prefix="/api/publishing"'),
            ("app/api/publishing.py", '"/jobs"'),
            ("app/api/analytics.py", 'prefix="/api/analytics"'),
            ("app/api/analytics.py", '"/traffic"'),
            ("app/api/analytics.py", '"/revenue"'),
            ("app/api/logs.py", 'prefix="/api/logs"'),
        ]
        for file_rel, pattern in expected_routes:
            content = (BACKEND_ROOT / file_rel).read_text(encoding="utf-8")
            self.assertIn(pattern, content, f"Expected route pattern {pattern} in {file_rel}")


if __name__ == "__main__":
    unittest.main()
