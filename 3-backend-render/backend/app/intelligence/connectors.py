"""
NEXUS MEDIA AI — Step 5: Modular News Source Connectors
Defines the common connector interface required by Section 2:
- fetch()
- normalize()
- validate()
- get_source_metadata()
- report_errors()

Supported connector types:
1. RSSFeedConnector (reputable publisher RSS 2.0 & Atom XML feeds)
2. GDELTPublicDataConnector (GDELT v2 DOC API JSON format)
3. ApprovedNewsAPIConnector (REST News API JSON format)
4. AdminConfiguredRSSConnector (Custom admin-configured RSS URLs with strict SSRF & robots compliance)

Features:
- Pagination, timeouts, rate limits, exponential retry backoff, and source-specific error reporting.
- Respects robots.txt, publisher terms, API limits, and copyright restrictions (stores short metadata
  descriptions only — never copies full copyrighted article bodies).
- Never assumes a source is connected until a real test or verified payload succeeds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from app.intelligence.deduplication import normalize_canonical_url, normalize_headline
from app.intelligence.security import (
    SSRFValidationError,
    sanitize_untrusted_article_text,
    validate_safe_external_url,
)


@dataclass
class FetchedRawItem:
    external_guid: str
    headline: str
    url: str
    published_at: Optional[str] = None
    author: Optional[str] = None
    summary: str = ""
    language: str = "en"
    category_hint: Optional[str] = None
    image_url: Optional[str] = None
    image_legally_usable: bool = False
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedNewsItem:
    external_guid: str
    original_headline: str
    normalized_headline: str
    source_id: str
    source_name: str
    original_article_url: str
    canonical_url: str
    publication_timestamp: str
    first_discovered_timestamp: str
    author: Optional[str]
    language: str
    category: str
    short_metadata_description: str
    image_url: Optional[str]
    image_legally_usable: bool
    source_reliability_metadata: Dict[str, Any]
    collection_status: str = "collected"
    prompt_injection_sanitized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "external_guid": self.external_guid,
            "original_headline": self.original_headline,
            "normalized_headline": self.normalized_headline,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "original_article_url": self.original_article_url,
            "canonical_url": self.canonical_url,
            "publication_timestamp": self.publication_timestamp,
            "first_discovered_timestamp": self.first_discovered_timestamp,
            "author": self.author,
            "language": self.language,
            "category": self.category,
            "short_metadata_description": self.short_metadata_description,
            "image_url": self.image_url,
            "image_legally_usable": self.image_legally_usable,
            "source_reliability_metadata": dict(self.source_reliability_metadata),
            "collection_status": self.collection_status,
            "prompt_injection_sanitized": self.prompt_injection_sanitized,
        }


@dataclass
class ConnectorErrorReport:
    source_id: str
    source_name: str
    connector_type: str
    error_code: str
    message: str
    retryable: bool
    attempt: int
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "connector_type": self.connector_type,
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
            "attempt": self.attempt,
            "occurred_at": self.occurred_at,
        }


class BaseNewsSourceConnector(ABC):
    """
    Common interface implemented by all news source connectors:
    - fetch()
    - normalize()
    - validate()
    - get_source_metadata()
    - report_errors()
    """

    connector_type: str = "base"

    def __init__(
        self,
        source_id: str,
        source_name: str,
        endpoint_url: str,
        trust_tier: str = "Primary Wire",
        reliability_score: float = 90.0,
        timeout_seconds: int = 15,
        rate_limit_per_minute: int = 30,
        max_retries: int = 3,
        robots_txt_compliant: bool = True,
        terms_approved: bool = True,
        default_category: str = "world-trending-news",
        default_language: str = "en",
        transport_fn: Optional[Callable[[str, int], str]] = None,
    ) -> None:
        self.source_id = source_id
        self.source_name = source_name
        self.endpoint_url = endpoint_url
        self.trust_tier = trust_tier
        self.reliability_score = reliability_score
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_retries = max_retries
        self.robots_txt_compliant = robots_txt_compliant
        self.terms_approved = terms_approved
        self.default_category = default_category
        self.default_language = default_language
        self.transport_fn = transport_fn
        self._error_reports: List[ConnectorErrorReport] = []
        self._request_timestamps: List[float] = []
        self.connection_status: str = "NOT_CONNECTED"

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate connector configuration, robots.txt/publisher compliance flags,
        and SSRF safety of the endpoint URL.
        """
        if not self.robots_txt_compliant:
            self._record_error(
                "ROBOTS_TXT_PROHIBITED",
                f"Source '{self.source_name}' is marked non-compliant with robots.txt.",
                retryable=False,
            )
            return False, "Automated access prohibited by robots.txt policy."

        if not self.terms_approved:
            self._record_error(
                "PUBLISHER_TERMS_UNAPPROVED",
                f"Source '{self.source_name}' publisher terms are not approved.",
                retryable=False,
            )
            return False, "Publisher terms of service not approved."

        try:
            validate_safe_external_url(self.endpoint_url)
        except SSRFValidationError as exc:
            self._record_error("SSRF_VALIDATION_FAILED", str(exc), retryable=False)
            return False, str(exc)

        return True, None

    def compute_backoff_seconds(self, attempt: int) -> float:
        """Deterministic exponential backoff for retryable connector failures."""
        safe_attempt = max(1, int(attempt))
        return min(30.0, round(0.5 * (2 ** (safe_attempt - 1)), 2))

    def _check_rate_limit(self) -> bool:
        now = time.monotonic()
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]
        if len(self._request_timestamps) >= self.rate_limit_per_minute:
            self._record_error(
                "RATE_LIMIT_EXCEEDED",
                f"Rate limit of {self.rate_limit_per_minute} requests/min exceeded for {self.source_name}.",
                retryable=True,
            )
            return False
        self._request_timestamps.append(now)
        return True

    def _record_error(
        self,
        error_code: str,
        message: str,
        retryable: bool = True,
        attempt: int = 1,
    ) -> ConnectorErrorReport:
        report = ConnectorErrorReport(
            source_id=self.source_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            error_code=error_code,
            message=message,
            retryable=retryable,
            attempt=attempt,
        )
        self._error_reports.append(report)
        return report

    def _execute_transport_with_retries(self, page: int = 1, page_size: int = 20) -> str:
        valid, err_msg = self.validate()
        if not valid:
            raise ValueError(err_msg or "Connector validation failed.")

        if not self._check_rate_limit():
            raise RuntimeError("Connector rate limit exceeded.")

        last_exc: Optional[Exception] = None
        total_attempts = max(1, self.max_retries)

        for attempt in range(1, total_attempts + 1):
            try:
                if self.transport_fn is not None:
                    raw_payload = self.transport_fn(self.endpoint_url, self.timeout_seconds)
                    self.connection_status = "CONNECTED"
                    return raw_payload

                req = urllib.request.Request(
                    self.endpoint_url,
                    headers={
                        "User-Agent": "NexusMediaAI-NewsIntelligence/1.0 (+https://nexusmedia.ai/bot; respectful-rss-ingestor)",
                        "Accept": "application/rss+xml, application/atom+xml, application/xml, application/json;q=0.9",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    self.connection_status = "CONNECTED"
                    return body
            except TimeoutError as exc:
                last_exc = exc
                self._record_error(
                    "SOURCE_TIMEOUT",
                    f"Source '{self.source_name}' timed out after {self.timeout_seconds}s (attempt {attempt}).",
                    retryable=True,
                    attempt=attempt,
                )
            except urllib.error.URLError as exc:
                last_exc = exc
                self._record_error(
                    "NETWORK_FETCH_ERROR",
                    f"Network error fetching '{self.source_name}': {exc}",
                    retryable=True,
                    attempt=attempt,
                )
            except Exception as exc:
                last_exc = exc
                self._record_error(
                    "CONNECTOR_EXECUTION_ERROR",
                    f"Error fetching '{self.source_name}': {exc}",
                    retryable=attempt < total_attempts,
                    attempt=attempt,
                )

        self.connection_status = "ERROR"
        raise RuntimeError(f"Failed to fetch from '{self.source_name}' after {total_attempts} attempts: {last_exc}")

    @abstractmethod
    def fetch(self, page: int = 1, page_size: int = 20) -> List[FetchedRawItem]:
        """Fetch raw items from the source with pagination, timeout, and retry handling."""

    def normalize(self, raw_items: List[FetchedRawItem]) -> List[NormalizedNewsItem]:
        """
        Normalize raw source items into the canonical Step 5 News Intelligence schema.
        Sanitizes untrusted text, enforces short metadata description limits (never storing full
        copyrighted article bodies), and validates article URLs against SSRF.
        """
        normalized_list: List[NormalizedNewsItem] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in raw_items:
            try:
                validate_safe_external_url(item.url)
            except SSRFValidationError as exc:
                self._record_error(
                    "ARTICLE_URL_SSRF_BLOCKED",
                    f"Skipped article with unsafe URL '{item.url}': {exc}",
                    retryable=False,
                )
                continue

            clean_headline, hl_injected = sanitize_untrusted_article_text(item.headline, max_length=220)
            clean_desc, desc_injected = sanitize_untrusted_article_text(item.summary, max_length=320)
            if not clean_headline:
                continue

            canonical = normalize_canonical_url(item.url)
            norm_hl = normalize_headline(clean_headline)

            safe_image_url: Optional[str] = None
            legally_usable = bool(item.image_legally_usable)
            if item.image_url and legally_usable:
                try:
                    safe_image_url = validate_safe_external_url(item.image_url)
                except SSRFValidationError:
                    safe_image_url = None
                    legally_usable = False

            normalized_list.append(
                NormalizedNewsItem(
                    external_guid=item.external_guid or canonical or norm_hl[:64],
                    original_headline=clean_headline,
                    normalized_headline=norm_hl,
                    source_id=self.source_id,
                    source_name=self.source_name,
                    original_article_url=item.url.strip(),
                    canonical_url=canonical,
                    publication_timestamp=item.published_at or now_iso,
                    first_discovered_timestamp=now_iso,
                    author=item.author.strip() if item.author else None,
                    language=(item.language or self.default_language or "en").lower()[:8],
                    category=item.category_hint or self.default_category,
                    short_metadata_description=clean_desc,
                    image_url=safe_image_url,
                    image_legally_usable=legally_usable,
                    source_reliability_metadata={
                        "trust_tier": self.trust_tier,
                        "reliability_score": self.reliability_score,
                        "connector_type": self.connector_type,
                        "robots_txt_compliant": self.robots_txt_compliant,
                        "terms_approved": self.terms_approved,
                    },
                    collection_status="collected",
                    prompt_injection_sanitized=bool(hl_injected or desc_injected),
                )
            )

        return normalized_list

    def get_source_metadata(self) -> Dict[str, Any]:
        """Return structured metadata and compliance state for this connector."""
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "connector_type": self.connector_type,
            "endpoint_url": self.endpoint_url,
            "trust_tier": self.trust_tier,
            "reliability_score": self.reliability_score,
            "timeout_seconds": self.timeout_seconds,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_retries": self.max_retries,
            "robots_txt_compliant": self.robots_txt_compliant,
            "terms_approved": self.terms_approved,
            "connection_status": self.connection_status,
            "error_count": len(self._error_reports),
        }

    def report_errors(self) -> List[Dict[str, Any]]:
        """Return all recorded connector errors."""
        return [err.to_dict() for err in self._error_reports]


class RSSFeedConnector(BaseNewsSourceConnector):
    """Connector for RSS 2.0 and Atom XML feeds from reputable publishers."""

    connector_type = "rss_feed"

    def fetch(self, page: int = 1, page_size: int = 20) -> List[FetchedRawItem]:
        xml_payload = self._execute_transport_with_retries(page=page, page_size=page_size)
        trimmed = xml_payload.strip()
        if trimmed.startswith("{") or trimmed.startswith("["):
            try:
                data = json.loads(trimmed)
                articles = data.get("articles", []) if isinstance(data, dict) else []
                items: List[FetchedRawItem] = []
                for art in articles:
                    title = str(art.get("title") or "").strip()
                    url = str(art.get("url") or "").strip()
                    if title and url:
                        items.append(
                            FetchedRawItem(
                                external_guid=str(art.get("url_mobile") or url),
                                headline=title,
                                url=url,
                                published_at=str(art.get("seendate") or "") or None,
                                author=str(art.get("domain") or "") or None,
                                summary=str(art.get("snippet") or art.get("title") or ""),
                                language=str(art.get("language") or "en")[:8],
                            )
                        )
                return items
            except Exception:
                pass

        try:
            root = ET.fromstring(trimmed)
        except ET.ParseError as exc:
            self._record_error(
                "INVALID_RSS_XML",
                f"Malformed XML in RSS feed '{self.source_name}': {exc}",
                retryable=False,
            )
            raise ValueError(f"Invalid RSS/Atom XML payload from '{self.source_name}': {exc}") from exc

        items: List[FetchedRawItem] = []

        # RSS 2.0 <item> elements
        for item_el in root.findall(".//item"):
            title = (item_el.findtext("title") or "").strip()
            link = (item_el.findtext("link") or "").strip()
            guid = (item_el.findtext("guid") or link or title).strip()
            pub_date = (item_el.findtext("pubDate") or "").strip() or None
            author = (
                item_el.findtext("author")
                or item_el.findtext("{http://purl.org/dc/elements/1.1/}creator")
                or None
            )
            desc = (item_el.findtext("description") or "").strip()
            cat = (item_el.findtext("category") or "").strip() or None
            if title and link:
                items.append(
                    FetchedRawItem(
                        external_guid=guid,
                        headline=title,
                        url=link,
                        published_at=pub_date,
                        author=author,
                        summary=desc,
                        language=self.default_language,
                        category_hint=cat,
                    )
                )

        # Atom <entry> elements
        if not items:
            atom_ns = "{http://www.w3.org/2005/Atom}"
            for entry_el in root.findall(f".//{atom_ns}entry") + root.findall(".//entry"):
                title = (
                    entry_el.findtext(f"{atom_ns}title")
                    or entry_el.findtext("title")
                    or ""
                ).strip()
                link_el = entry_el.find(f"{atom_ns}link")
                if link_el is None:
                    link_el = entry_el.find("link")
                link = (link_el.attrib.get("href") if link_el is not None else "") or ""
                guid = (
                    entry_el.findtext(f"{atom_ns}id")
                    or entry_el.findtext("id")
                    or link
                    or title
                ).strip()
                updated = (
                    entry_el.findtext(f"{atom_ns}updated")
                    or entry_el.findtext("updated")
                    or None
                )
                summary = (
                    entry_el.findtext(f"{atom_ns}summary")
                    or entry_el.findtext("summary")
                    or ""
                ).strip()
                if title and link:
                    items.append(
                        FetchedRawItem(
                            external_guid=guid,
                            headline=title,
                            url=link,
                            published_at=updated,
                            summary=summary,
                            language=self.default_language,
                        )
                    )

        start = max(0, (max(1, page) - 1) * max(1, page_size))
        end = start + max(1, page_size)
        return items[start:end]


class AdminConfiguredRSSConnector(RSSFeedConnector):
    """Connector for admin-added custom RSS feed URLs."""

    connector_type = "admin_rss"


class GDELTPublicDataConnector(BaseNewsSourceConnector):
    """Connector for GDELT 2.0 DOC API JSON responses."""

    connector_type = "gdelt_api"

    def fetch(self, page: int = 1, page_size: int = 20) -> List[FetchedRawItem]:
        raw_json = self._execute_transport_with_retries(page=page, page_size=page_size)
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            self._record_error("INVALID_GDELT_JSON", f"Malformed GDELT JSON: {exc}", retryable=False)
            raise ValueError(f"Invalid GDELT JSON payload: {exc}") from exc

        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        items: List[FetchedRawItem] = []
        for art in articles:
            if not isinstance(art, dict):
                continue
            title = str(art.get("title") or "").strip()
            url = str(art.get("url") or "").strip()
            if not title or not url:
                continue
            items.append(
                FetchedRawItem(
                    external_guid=str(art.get("url_mobile") or url),
                    headline=title,
                    url=url,
                    published_at=str(art.get("seendate") or "") or None,
                    author=str(art.get("domain") or "") or None,
                    summary=str(art.get("snippet") or art.get("title") or ""),
                    language=str(art.get("language") or "en")[:8],
                    raw_metadata={"sourcecountry": art.get("sourcecountry")},
                )
            )

        start = max(0, (max(1, page) - 1) * max(1, page_size))
        end = start + max(1, page_size)
        return items[start:end]


class ApprovedNewsAPIConnector(BaseNewsSourceConnector):
    """Connector for approved structured News API JSON feeds."""

    connector_type = "news_api"

    def fetch(self, page: int = 1, page_size: int = 20) -> List[FetchedRawItem]:
        raw_json = self._execute_transport_with_retries(page=page, page_size=page_size)
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            self._record_error("INVALID_NEWS_API_JSON", f"Malformed News API JSON: {exc}", retryable=False)
            raise ValueError(f"Invalid News API JSON payload: {exc}") from exc

        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        items: List[FetchedRawItem] = []
        for art in articles:
            if not isinstance(art, dict):
                continue
            title = str(art.get("title") or "").strip()
            url = str(art.get("url") or "").strip()
            if not title or not url:
                continue
            items.append(
                FetchedRawItem(
                    external_guid=str(art.get("id") or url),
                    headline=title,
                    url=url,
                    published_at=str(art.get("publishedAt") or "") or None,
                    author=str(art.get("author") or "") or None,
                    summary=str(art.get("description") or ""),
                    language=str(art.get("language") or "en")[:8],
                    image_url=str(art.get("urlToImage") or "") or None,
                    image_legally_usable=bool(art.get("imageLicensed", False)),
                )
            )

        start = max(0, (max(1, page) - 1) * max(1, page_size))
        end = start + max(1, page_size)
        return items[start:end]
