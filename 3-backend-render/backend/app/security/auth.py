"""Security and authentication utilities (Argon2id password hashing + JWT + RBAC)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

from app.config import AppSettings, get_settings

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    _argon2_hasher: Optional[PasswordHasher] = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )
except ImportError:  # pragma: no cover
    _argon2_hasher = None
    VerifyMismatchError = Exception  # type: ignore

try:
    import jwt as pyjwt
except ImportError:  # pragma: no cover
    pyjwt = None  # type: ignore


VALID_ROLES = {"super_admin", "managing_editor", "fact_checker", "operator", "viewer"}
ADMIN_ROLES = {"super_admin", "managing_editor"}
OPERATOR_ROLES = {"super_admin", "managing_editor", "operator"}
EDITORIAL_ROLES = {"super_admin", "managing_editor", "fact_checker"}


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Verified identity extracted from a validated Bearer JWT."""

    user_id: str
    email: str
    roles: List[str]
    session_id: str

    @property
    def sub(self) -> str:
        return self.user_id

    def has_any_role(self, allowed: Iterable[str]) -> bool:
        allowed_set = set(allowed)
        return any(role in allowed_set for role in self.roles)


def hash_password(plain_password: str) -> str:
    """Hashes a password using Argon2id (with PBKDF2 fallback only if CFFI is absent)."""
    if not plain_password or len(plain_password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if _argon2_hasher is not None:
        return _argon2_hasher.hash(plain_password)

    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 310000)
    return f"$pbkdf2-sha256$310000${salt}${derived.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash in constant time."""
    if not plain_password or not password_hash:
        return False

    if _argon2_hasher is not None and password_hash.startswith("$argon2"):
        try:
            return bool(_argon2_hasher.verify(password_hash, plain_password))
        except Exception:
            return False

    if password_hash.startswith("$pbkdf2-sha256$"):
        parts = password_hash.split("$")
        if len(parts) != 5:
            return False
        iterations = int(parts[2])
        salt = parts[3]
        expected_hex = parts[4]
        derived = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        ).hex()
        return hmac.compare_digest(derived, expected_hex)

    return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def create_access_token(
    *,
    user_id: str,
    email: str,
    roles: List[str],
    session_id: Optional[str] = None,
    settings: Optional[AppSettings] = None,
    expires_delta_seconds: Optional[int] = None,
) -> str:
    """Issues a signed HS256 JWT token. Requires JWT_SECRET to be configured."""
    cfg = settings or get_settings()
    secret = (cfg.JWT_SECRET or "").strip()
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters.")

    now = int(time.time())
    ttl = expires_delta_seconds if expires_delta_seconds is not None else cfg.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {
        "sub": user_id,
        "email": email,
        "roles": [r for r in roles if r in VALID_ROLES],
        "sid": session_id or secrets.token_hex(8),
        "iat": now,
        "exp": now + ttl,
        "iss": "nexus-media-ai-backend",
    }

    if pyjwt is not None:
        return str(pyjwt.encode(payload, secret, algorithm=cfg.JWT_ALGORITHM))

    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = (
        f"{_b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_and_verify_access_token(
    token: str, settings: Optional[AppSettings] = None
) -> AuthenticatedPrincipal:
    """Validates a Bearer JWT signature, expiration, and claims."""
    cfg = settings or get_settings()
    secret = (cfg.JWT_SECRET or "").strip()
    if len(secret) < 32:
        raise ValueError("Server JWT_SECRET is not configured.")

    if not token or token.count(".") != 2:
        raise ValueError("Malformed authentication token.")

    if pyjwt is not None:
        try:
            decoded = pyjwt.decode(
                token,
                secret,
                algorithms=[cfg.JWT_ALGORITHM],
                issuer="nexus-media-ai-backend",
            )
        except pyjwt.PyJWTError as exc:
            raise ValueError(f"Invalid authentication token: {exc}") from exc
    else:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature.")
        decoded = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(decoded.get("exp", 0)) < int(time.time()):
            raise ValueError("Token has expired.")
        if decoded.get("iss") != "nexus-media-ai-backend":
            raise ValueError("Invalid token issuer.")

    user_id = str(decoded.get("sub") or "").strip()
    email = str(decoded.get("email") or "").strip()
    raw_roles = decoded.get("roles") or []
    roles = [str(r) for r in raw_roles if str(r) in VALID_ROLES]
    if not user_id or not email or not roles:
        raise ValueError("Token is missing required subject or role claims.")

    return AuthenticatedPrincipal(
        user_id=user_id,
        email=email,
        roles=roles,
        session_id=str(decoded.get("sid") or ""),
    )
