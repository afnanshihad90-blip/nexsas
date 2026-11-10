"""Signed server-to-server client that pushes articles to the PHP blog (publish.php).

Signature scheme (mirrored in blog/api/publish.php):
    signature = HMAC_SHA256(secret, f"{timestamp}.{idempotency_key}.{raw_body}")
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Optional

REQUIRED_FIELDS = ("title", "slug", "content")


def sign_request(secret: str, timestamp: str, idempotency_key: str, raw_body: str) -> str:
    msg = f"{timestamp}.{idempotency_key}.{raw_body}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: str, idempotency_key: str, raw_body: str,
                     signature: str, max_skew_seconds: int = 300, now: Optional[float] = None) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs((now if now is not None else time.time()) - ts) > max_skew_seconds:
        return False
    expected = sign_request(secret, timestamp, idempotency_key, raw_body)
    return hmac.compare_digest(expected, signature or "")


def build_payload(article: Dict[str, Any]) -> Dict[str, Any]:
    missing = [f for f in REQUIRED_FIELDS if not str(article.get(f) or "").strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return {
        "title": article["title"].strip(),
        "slug": article["slug"].strip(),
        "content": article["content"],
        "excerpt": article.get("excerpt", ""),
        "category": article.get("category", "technology"),
        "status": article.get("status", "draft"),
        "meta_description": article.get("meta_description", ""),
        "image": article.get("image"),            # {url, alt, credit, credit_url, license}
        "sources": article.get("sources", []),    # [{title, url}]
    }


class BlogPublishError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, hint: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.hint = hint


HINTS = {
    401: "Signature mismatch: check BLOG_SIGNING_SECRET matches blog/config.php.",
    403: "Likely hosting security block (InfinityFree challenge). Do NOT bypass; use the pull-sync route or move hosting.",
    404: "publish.php path wrong: check BLOG_ENDPOINT.",
}


async def push_article(endpoint: str, secret: str, article: Dict[str, Any],
                       idempotency_key: Optional[str] = None, retries: int = 3,
                       timeout: float = 20.0) -> Dict[str, Any]:
    import httpx  # lazy import

    payload = build_payload(article)
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    key = idempotency_key or f"art-{payload['slug']}-{uuid.uuid4().hex[:8]}"
    last_err: Optional[BlogPublishError] = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries):
            ts = str(int(time.time()))
            headers = {
                "Content-Type": "application/json",
                "X-Nexus-Timestamp": ts,
                "Idempotency-Key": key,
                "X-Nexus-Signature": sign_request(secret, ts, key, raw),
                "User-Agent": "NexusMediaAI/1.0",
            }
            try:
                r = await client.post(endpoint, content=raw.encode(), headers=headers)
            except httpx.HTTPError as exc:
                last_err = BlogPublishError(f"Network error: {type(exc).__name__}", hint="Timeout/connection problem.")
            else:
                ctype = r.headers.get("content-type", "")
                if r.status_code in (200, 201) and "json" in ctype:
                    return r.json()
                last_err = BlogPublishError(
                    f"Blog responded {r.status_code}", r.status_code, HINTS.get(r.status_code, ""))
                if r.status_code < 500 and r.status_code != 429:
                    break  # client errors will not fix themselves
            await asyncio.sleep(2 ** attempt)
    assert last_err is not None
    raise last_err
