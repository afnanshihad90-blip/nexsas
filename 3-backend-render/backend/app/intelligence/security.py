"""
NEXUS MEDIA AI — Step 5: News Intelligence Security & Sanitization
Implements:
1. Strict SSRF Protection for all external source URLs (blocks private IPv4/IPv6 ranges,
   loopback, link-local / cloud metadata 169.254.169.254, non-HTTP(S) schemes, and embedded credentials).
2. Untrusted External Article Text Sanitization:
   - Strips HTML/script tags and control characters.
   - Enforces short metadata description limits so full copyrighted articles are never stored.
   - Detects and neutralizes prompt-injection directives so untrusted article text can never
     override agent instructions.
"""

from __future__ import annotations

import html
import ipaddress
import re
from typing import Tuple
from urllib.parse import urlparse


class SSRFValidationError(ValueError):
    """Raised when a URL violates SSRF or protocol security rules."""


BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "0.0.0.0",
}

BLOCKED_HOST_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".home.arpa",
    ".corp",
    ".lan",
)

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|directives)", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?developer\s+mode", re.IGNORECASE),
    re.compile(r"override\s+(system|agent|editorial|safety)\s+(instructions|rules|policy)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|instruction|prompt|tool_call)\s*>", re.IGNORECASE),
]

HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")


def _is_forbidden_ip(ip_str: str) -> bool:
    """Return True if the IP string is loopback, private, link-local, multicast, or reserved."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if getattr(ip_obj, "ipv4_mapped", None) is not None:
        ip_obj = ip_obj.ipv4_mapped  # type: ignore[assignment]

    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
        or str(ip_obj).startswith("169.254.")
        or str(ip_obj).startswith("100.64.")
    )


def validate_safe_external_url(url: str, require_https: bool = False) -> str:
    """
    Validate that an external source or article URL is safe from SSRF.
    Blocks non-http(s) schemes, embedded credentials, localhost, internal hostnames,
    and private/loopback/link-local IP addresses.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    cleaned = url.strip()
    if len(cleaned) > 2048:
        raise SSRFValidationError("URL exceeds maximum allowed length of 2048 characters.")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()

    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if scheme not in allowed_schemes:
        raise SSRFValidationError(
            f"Unsupported URL scheme '{scheme or 'none'}'. Only {', '.join(sorted(allowed_schemes))} allowed."
        )

    if parsed.username or parsed.password:
        raise SSRFValidationError("Embedded credentials in source URLs are forbidden.")

    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        raise SSRFValidationError("URL must include a valid hostname.")

    if hostname in BLOCKED_HOSTNAMES or any(hostname.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        raise SSRFValidationError(f"SSRF protection blocked internal or reserved hostname '{hostname}'.")

    # Check direct IPv4 / IPv6 literals and bracketed IPv6
    if _is_forbidden_ip(hostname):
        raise SSRFValidationError(f"SSRF protection blocked private or reserved IP address '{hostname}'.")

    # Also block decimal/octal/hex encoded IP tricks like 0x7f000001 or 2130706433
    if hostname.isdigit() or hostname.startswith("0x"):
        raise SSRFValidationError(f"SSRF protection blocked numeric IP encoding '{hostname}'.")

    # Ensure domain has at least one dot when not an IP literal
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise SSRFValidationError(f"SSRF protection blocked unqualified single-label host '{hostname}'.")

    return cleaned


def sanitize_untrusted_article_text(
    raw_text: str,
    max_length: int = 360,
) -> Tuple[str, bool]:
    """
    Sanitize untrusted headline or metadata description text from external feeds:
    1. Strips <script>/<style> blocks and all HTML tags.
    2. Unescapes HTML entities and normalizes whitespace.
    3. Detects and neutralizes prompt injection patterns so external text cannot
       override agent instructions.
    4. Enforces copyright-safe metadata description truncation (`max_length` chars)
       so full copyrighted article bodies are never stored in the database.

    Returns (sanitized_text, prompt_injection_detected).
    """
    if not raw_text:
        return "", False

    text = SCRIPT_STYLE_RE.sub(" ", str(raw_text))
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)

    injection_detected = False
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            injection_detected = True
            text = pattern.sub("[REDACTED_UNTRUSTED_DIRECTIVE]", text)

    # Remove non-printable control characters
    text = "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\t", " "))
    text = WHITESPACE_RE.sub(" ", text).strip()

    if len(text) > max_length:
        truncated = text[: max_length - 1].rsplit(" ", 1)[0].strip()
        text = f"{truncated}…" if truncated else f"{text[: max_length - 1]}…"

    return text, injection_detected
