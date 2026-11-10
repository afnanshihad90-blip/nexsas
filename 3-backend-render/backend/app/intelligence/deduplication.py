"""
NEXUS MEDIA AI — Step 5: Multi-Stage Duplicate Detection & Story Clustering
Implements:
- Stage 1: URL Normalization & Canonical URL Matching (strips tracking params utm_*, fbclid, gclid, etc.)
- Stage 2: Headline Normalization & Token/Bigram Similarity Detection
- Stage 3: Event Clustering into StoryClusterRecord objects, distinguishing independent
  publishers from syndicated wire copies so syndicated copies are never treated as independent sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "yclid",
    "mc_cid",
    "mc_eid",
    "igsh",
    "igshid",
    "ref",
    "ref_src",
    "ref_url",
    "source",
    "_ga",
    "_gl",
    "ncid",
    "cmpid",
    "ito",
    "ocid",
    " s",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "over",
    "says",
    "the",
    "to",
    "up",
    "with",
    "after",
    "amid",
    "new",
    "report",
    "reports",
    "update",
    "live",
    "breaking",
}

WIRE_SYNDICATION_MARKERS = (
    "reuters",
    "associated press",
    "ap news",
    "afp",
    "agence france-presse",
    "bloomberg wire",
    "pr newswire",
    "business wire",
    "globe newswire",
)


def normalize_canonical_url(url: str) -> str:
    """
    Stage 1: Normalize article URL by lowercasing scheme/host, stripping www. and fragments,
    removing tracking query parameters (utm_*, fbclid, gclid, etc.), sorting remaining query params,
    and normalizing trailing slashes.
    """
    if not url or not isinstance(url, str):
        return ""

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = re.sub(r"/+", "/", parsed.path or "/")
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    filtered_params: List[Tuple[str, str]] = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=False):
        k_lower = k.lower().strip()
        if k_lower.startswith("utm_") or k_lower.startswith("WT.") or k_lower in TRACKING_QUERY_PARAMS:
            continue
        filtered_params.append((k_lower, v.strip()))

    filtered_params.sort(key=lambda item: (item[0], item[1]))
    clean_query = urlencode(filtered_params)

    return urlunparse((scheme, netloc, path, "", clean_query, ""))


def normalize_headline(headline: str) -> str:
    """
    Stage 2: Normalize headline text by stripping agency prefixes (e.g., 'BREAKING:', 'UPDATE 1-'),
    lowercasing, removing punctuation, and collapsing whitespace.
    """
    if not headline:
        return ""
    text = headline.strip().lower()
    # Strip common wire prefixes like "UPDATE 2-", "BREAKING:", "EXCLUSIVE -"
    text = re.sub(
        r"^(?:breaking(?:\s+news)?|exclusive|update\s*\d*|live\s+updates?|watch)\s*[:\-–—]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Strip trailing publisher suffix like " - Reuters" or " | Financial Times"
    text = re.sub(r"\s+[\-–—|]\s+[a-z0-9\s.&]{2,35}$", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [tok for tok in text.split() if tok]
    return " ".join(tokens)


def _extract_content_tokens(headline: str) -> List[str]:
    norm = normalize_headline(headline)
    tokens = [tok for tok in norm.split() if tok not in STOPWORDS and len(tok) > 1]
    return tokens if tokens else norm.split()


def compute_headline_similarity(headline_a: str, headline_b: str) -> float:
    """
    Compute similarity score [0.0, 1.0] between two headlines using a combination of
    normalized exact match, token Jaccard similarity, and character/word bigram overlap.
    """
    norm_a = normalize_headline(headline_a)
    norm_b = normalize_headline(headline_b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    tokens_a = _extract_content_tokens(headline_a)
    tokens_b = _extract_content_tokens(headline_b)
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    jaccard = intersection / union if union else 0.0

    # Containment coefficient helps when one headline is a slightly shorter version of the same event
    min_len = min(len(set_a), len(set_b))
    containment = intersection / min_len if min_len else 0.0

    # Word bigram overlap
    bigrams_a = {f"{tokens_a[i]}_{tokens_a[i + 1]}" for i in range(len(tokens_a) - 1)}
    bigrams_b = {f"{tokens_b[i]}_{tokens_b[i + 1]}" for i in range(len(tokens_b) - 1)}
    if bigrams_a and bigrams_b:
        bigram_union = len(bigrams_a | bigrams_b)
        bigram_sim = len(bigrams_a & bigrams_b) / bigram_union if bigram_union else 0.0
    else:
        bigram_sim = jaccard

    combined = (0.50 * jaccard) + (0.35 * containment) + (0.15 * bigram_sim)
    return round(min(1.0, max(0.0, combined)), 4)


def detect_syndicated_copy(
    headline: str,
    summary: str,
    author: Optional[str],
    source_name: str,
    existing_cluster_headlines: List[str],
) -> bool:
    """
    Determine whether an incoming article is a syndicated wire copy rather than
    independent original reporting.
    """
    combined_meta = f"{author or ''} {summary or ''}".lower()
    source_lower = (source_name or "").lower()

    # If the article explicitly credits a wire service that is not the publisher itself
    for marker in WIRE_SYNDICATION_MARKERS:
        if marker in combined_meta and marker not in source_lower:
            return True

    # Near-verbatim headline match (>= 0.92 similarity) to an already-ingested story
    for existing_hl in existing_cluster_headlines:
        if compute_headline_similarity(headline, existing_hl) >= 0.92:
            return True

    return False


@dataclass
class StoryClusterRecord:
    story_id: str
    cluster_key: str
    main_headline: str
    normalized_headline: str
    category_slug: str
    related_source_ids: List[str] = field(default_factory=list)
    related_news_ids: List[str] = field(default_factory=list)
    independent_publishers: Set[str] = field(default_factory=set)
    syndicated_copies_count: int = 0
    first_discovered_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latest_update_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_to_research: bool = False
    research_task_id: Optional[str] = None
    cluster_headlines: List[str] = field(default_factory=list)

    @property
    def independent_publishers_count(self) -> int:
        return max(1, len(self.independent_publishers))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "cluster_key": self.cluster_key,
            "main_headline": self.main_headline,
            "normalized_headline": self.normalized_headline,
            "category_slug": self.category_slug,
            "related_source_ids": list(self.related_source_ids),
            "related_news_ids": list(self.related_news_ids),
            "independent_publishers_count": self.independent_publishers_count,
            "syndicated_copies_count": self.syndicated_copies_count,
            "supporting_sources_count": len(self.related_source_ids),
            "first_discovered_time": self.first_discovered_time,
            "latest_update_time": self.latest_update_time,
            "sent_to_research": self.sent_to_research,
            "research_task_id": self.research_task_id,
        }


class StoryClusteringEngine:
    """
    Multi-stage deduplication & event clustering engine:
    - Stage 1: Exact canonical URL deduplication.
    - Stage 2: Near-identical headline deduplication (>= duplicate_threshold).
    - Stage 3: Event clustering (>= cluster_threshold) into StoryClusterRecord objects,
      tracking independent publishers separately from syndicated wire copies.
    """

    def __init__(
        self,
        duplicate_headline_threshold: float = 0.88,
        event_cluster_threshold: float = 0.45,
    ) -> None:
        self.duplicate_headline_threshold = duplicate_headline_threshold
        self.event_cluster_threshold = event_cluster_threshold
        self._canonical_url_index: Dict[str, str] = {}  # canonical_url -> news_id
        self._clusters: Dict[str, StoryClusterRecord] = {}

    @property
    def clusters(self) -> Dict[str, StoryClusterRecord]:
        return self._clusters

    def ingest_item(
        self,
        news_id: str,
        source_id: str,
        source_name: str,
        url: str,
        headline: str,
        summary: str = "",
        author: Optional[str] = None,
        category_slug: str = "world-trending-news",
        discovered_at: Optional[str] = None,
        is_syndicated_override: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Process a news item through all 3 deduplication/clustering stages.
        Returns a dictionary with:
        - is_exact_duplicate: bool
        - duplicate_stage: Optional['canonical_url' | 'near_identical_headline']
        - is_syndicated_copy: bool
        - canonical_url: str
        - normalized_headline: str
        - cluster: StoryClusterRecord
        """
        now_iso = discovered_at or datetime.now(timezone.utc).isoformat()
        canonical_url = normalize_canonical_url(url)
        norm_headline = normalize_headline(headline)

        # Stage 1: Canonical URL match
        if canonical_url and canonical_url in self._canonical_url_index:
            existing_news_id = self._canonical_url_index[canonical_url]
            matched_cluster = self._find_cluster_by_news_id(existing_news_id)
            return {
                "is_exact_duplicate": True,
                "duplicate_stage": "canonical_url",
                "duplicate_of_news_id": existing_news_id,
                "is_syndicated_copy": True,
                "canonical_url": canonical_url,
                "normalized_headline": norm_headline,
                "cluster": matched_cluster,
            }

        # Stage 2 & Stage 3: Find best matching event cluster by headline similarity
        best_cluster: Optional[StoryClusterRecord] = None
        best_similarity = 0.0

        for cluster in self._clusters.values():
            sim = compute_headline_similarity(headline, cluster.main_headline)
            for alt_hl in cluster.cluster_headlines:
                sim = max(sim, compute_headline_similarity(headline, alt_hl))
            if sim > best_similarity:
                best_similarity = sim
                best_cluster = cluster

        # Stage 2: Same publisher + near-identical headline is a duplicate item
        if (
            best_cluster is not None
            and best_similarity >= self.duplicate_headline_threshold
            and source_id in best_cluster.related_source_ids
        ):
            return {
                "is_exact_duplicate": True,
                "duplicate_stage": "near_identical_headline",
                "duplicate_of_news_id": best_cluster.related_news_ids[0] if best_cluster.related_news_ids else None,
                "is_syndicated_copy": True,
                "canonical_url": canonical_url,
                "normalized_headline": norm_headline,
                "cluster": best_cluster,
            }

        if canonical_url:
            self._canonical_url_index[canonical_url] = news_id

        # Stage 3: Group into existing StoryCluster if similarity >= event_cluster_threshold
        if best_cluster is not None and best_similarity >= self.event_cluster_threshold:
            is_syndicated = (
                is_syndicated_override
                if is_syndicated_override is not None
                else detect_syndicated_copy(
                    headline=headline,
                    summary=summary,
                    author=author,
                    source_name=source_name,
                    existing_cluster_headlines=best_cluster.cluster_headlines,
                )
            )
            if source_id not in best_cluster.related_source_ids:
                best_cluster.related_source_ids.append(source_id)
            if news_id not in best_cluster.related_news_ids:
                best_cluster.related_news_ids.append(news_id)
            best_cluster.cluster_headlines.append(headline)
            best_cluster.latest_update_time = now_iso

            publisher_key = (source_name or source_id).strip().lower()
            if is_syndicated:
                best_cluster.syndicated_copies_count += 1
            else:
                best_cluster.independent_publishers.add(publisher_key)

            return {
                "is_exact_duplicate": False,
                "duplicate_stage": None,
                "duplicate_of_news_id": None,
                "is_syndicated_copy": is_syndicated,
                "canonical_url": canonical_url,
                "normalized_headline": norm_headline,
                "cluster": best_cluster,
            }

        # Otherwise create a new StoryClusterRecord
        digest = hashlib.sha256(norm_headline.encode("utf-8")).hexdigest()[:10]
        story_id = f"cluster-{digest}"
        cluster_key = f"{category_slug}:{digest}"
        publisher_key = (source_name or source_id).strip().lower()
        is_syndicated = bool(is_syndicated_override) if is_syndicated_override is not None else False

        new_cluster = StoryClusterRecord(
            story_id=story_id,
            cluster_key=cluster_key,
            main_headline=headline,
            normalized_headline=norm_headline,
            category_slug=category_slug,
            related_source_ids=[source_id],
            related_news_ids=[news_id],
            independent_publishers={publisher_key},
            syndicated_copies_count=1 if is_syndicated else 0,
            first_discovered_time=now_iso,
            latest_update_time=now_iso,
            cluster_headlines=[headline],
        )
        self._clusters[story_id] = new_cluster

        return {
            "is_exact_duplicate": False,
            "duplicate_stage": None,
            "duplicate_of_news_id": None,
            "is_syndicated_copy": is_syndicated,
            "canonical_url": canonical_url,
            "normalized_headline": norm_headline,
            "cluster": new_cluster,
        }

    def _find_cluster_by_news_id(self, news_id: str) -> Optional[StoryClusterRecord]:
        for cluster in self._clusters.values():
            if news_id in cluster.related_news_ids:
                return cluster
        return None
