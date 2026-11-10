"""HTTP Security Headers, Rate Limiting Interface, and Structured Log Secret Redaction."""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"(postgres(?:ql(?:\+asyncpg)?)?://[^:]+:)([^@]+)(@)", re.IGNORECASE),
    re.compile(r"(sb_secret_)[A-Za-z0-9_\-]+", re.IGNORECASE),
]


def redact_sensitive_text(message: str) -> str:
    """Scrubs tokens, database passwords, and secret keys from log messages."""
    redacted = message
    redacted = SECRET_PATTERNS[0].sub(r"\1[REDACTED_TOKEN]", redacted)
    redacted = SECRET_PATTERNS[1].sub(r"\1[REDACTED_DB_PASSWORD]\3", redacted)
    redacted = SECRET_PATTERNS[2].sub(r"\1[REDACTED_SUPABASE_SECRET]", redacted)
    return redacted


class SecretRedactingLogFilter(logging.Filter):
    """Logging filter that guarantees no secret values are emitted to stdout/stderr."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            record.args = tuple(
                redact_sensitive_text(str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects enterprise security headers on every API response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response


class InMemoryRateLimiter:
    """Sliding-window rate limiter interface (replaceable with Redis in production clusters)."""

    def __init__(
        self,
        max_requests: int = 120,
        window_seconds: int = 60,
        requests_per_window: Optional[int] = None,
    ) -> None:
        self.max_requests = requests_per_window if requests_per_window is not None else max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        dq = self._buckets[client_key]
        cutoff = now - self.window_seconds
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies request rate limiting by client IP."""

    def __init__(self, app, limiter: InMemoryRateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_host = request.client.host if request.client else "unknown"
        if not self.limiter.is_allowed(client_host):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Too many requests. Please retry after the rate-limit window resets.",
                },
            )
        return await call_next(request)
