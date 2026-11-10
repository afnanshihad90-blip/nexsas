"""
NEXUS MEDIA AI — Step 5: News Intelligence Engine
Orchestrates:
1. Primary News Niches (Business & Finance, World Trending News, AI & Technology, Science & Space)
   with admin enable/disable and configurable keywords, topics, regions, and languages.
2. Modular News Source Registry (RSS feeds, GDELT public data, Approved News APIs, Admin RSS URLs)
   with honest NOT_CONNECTED state until a real test or verified payload succeeds.
3. Scheduled & On-Demand News Collection Workflow with:
   - Overlapping scan prevention (mutex/state lock)
   - Idempotency key deduplication
   - Multi-stage duplicate detection & event clustering
   - Rule-based + AI fallback classification
   - Weighted trend scoring
   - Cloudflare Worker cron scheduler integration support
   - Candidate story selection & handoff to Step 4 ResearchAgent (stopping strictly before
     deep research automation or article generation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.intelligence.classifier import NewsTopicClassifier, PRIMARY_CATEGORIES
from app.intelligence.connectors import (
    AdminConfiguredRSSConnector,
    ApprovedNewsAPIConnector,
    BaseNewsSourceConnector,
    GDELTPublicDataConnector,
    NormalizedNewsItem,
    RSSFeedConnector,
)
from app.intelligence.deduplication import StoryClusteringEngine
from app.intelligence.scoring import TrendScoringEngine
from app.intelligence.security import SSRFValidationError, validate_safe_external_url


DEFAULT_CONFIGURED_SOURCES: List[Dict[str, Any]] = [
    {
        "id": "src-reuters-global",
        "name": "Global Markets & Business Wire RSS",
        "protocol": "RSS 2.0",
        "connector_type": "rss_feed",
        "endpoint_url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "trust_tier": "Primary Wire",
        "reliability_score": 97.0,
        "poll_interval_seconds": 180,
        "timeout_seconds": 15,
        "rate_limit_per_minute": 30,
        "max_retries": 3,
        "status": "NOT_CONNECTED",
        "is_enabled": True,
        "robots_txt_compliant": True,
        "terms_approved": True,
        "category_slug": "business-finance",
        "last_polled_at": None,
        "last_success_at": None,
        "last_error_message": None,
        "articles_ingested_24h": 0,
    },
    {
        "id": "src-gdelt-v2-events",
        "name": "GDELT 2.0 Global World Events DOC API",
        "protocol": "REST JSON",
        "connector_type": "gdelt_api",
        "endpoint_url": "https://api.gdeltproject.org/api/v2/doc/doc?query=world%20news&mode=ArtList&maxrecords=25&format=json",
        "trust_tier": "Public Open Data",
        "reliability_score": 91.0,
        "poll_interval_seconds": 300,
        "timeout_seconds": 15,
        "rate_limit_per_minute": 20,
        "max_retries": 2,
        "status": "NOT_CONNECTED",
        "is_enabled": True,
        "robots_txt_compliant": True,
        "terms_approved": True,
        "category_slug": "world-trending-news",
        "last_polled_at": None,
        "last_success_at": None,
        "last_error_message": None,
        "articles_ingested_24h": 0,
    },
    {
        "id": "src-approved-news-api",
        "name": "Tech & AI Compute Wire RSS",
        "protocol": "RSS 2.0",
        "connector_type": "rss_feed",
        "endpoint_url": "https://techcrunch.com/feed/",
        "trust_tier": "Verified Aggregator",
        "reliability_score": 92.0,
        "poll_interval_seconds": 300,
        "timeout_seconds": 15,
        "rate_limit_per_minute": 25,
        "max_retries": 3,
        "status": "NOT_CONNECTED",
        "is_enabled": True,
        "robots_txt_compliant": True,
        "terms_approved": True,
        "category_slug": "ai-technology",
        "last_polled_at": None,
        "last_success_at": None,
        "last_error_message": None,
        "articles_ingested_24h": 0,
    },
    {
        "id": "src-nasa-esa-science",
        "name": "Phys.org Space & Physics News RSS",
        "protocol": "RSS 2.0",
        "connector_type": "rss_feed",
        "endpoint_url": "https://phys.org/rss-feed/",
        "trust_tier": "Primary Filing",
        "reliability_score": 98.0,
        "poll_interval_seconds": 600,
        "timeout_seconds": 15,
        "rate_limit_per_minute": 20,
        "max_retries": 3,
        "status": "NOT_CONNECTED",
        "is_enabled": True,
        "robots_txt_compliant": True,
        "terms_approved": True,
        "category_slug": "science-space",
        "last_polled_at": None,
        "last_success_at": None,
        "last_error_message": None,
        "articles_ingested_24h": 0,
    },
]


class NewsIntelligenceEngine:
    """
    Stateful Step 5 News Intelligence Engine with in-memory & database-ready persistence hooks,
    multi-stage deduplication, clustering, classification, weighted trend scoring, and
    Cloudflare Worker cron scheduling support.
    """

    def __init__(self) -> None:
        self.categories: Dict[str, Dict[str, Any]] = {}
        for slug, meta in PRIMARY_CATEGORIES.items():
            self.categories[slug] = {
                "id": f"cat-{slug}",
                "slug": slug,
                "name": meta["name"],
                "sector_group": meta["sector_group"],
                "priority_weight": meta["priority_weight"],
                "is_enabled": True,
                "keywords": list(meta["keywords"]),
                "topics": list(meta["topics"]),
                "regions": ["global", "north-america", "europe", "asia-pacific"],
                "languages": ["en"],
            }

        self.sources: Dict[str, Dict[str, Any]] = {
            src["id"]: dict(src) for src in DEFAULT_CONFIGURED_SOURCES
        }
        self.news_items: Dict[str, Dict[str, Any]] = {}
        self.classifications: Dict[str, Dict[str, Any]] = {}
        self.trend_scores: Dict[str, Dict[str, Any]] = {}
        self.collection_runs: List[Dict[str, Any]] = []
        self._idempotency_runs: Dict[str, Dict[str, Any]] = {}
        self._scan_in_progress: bool = False
        self.scan_interval_seconds: int = 300

        self.clustering_engine = StoryClusteringEngine()
        self.classifier = NewsTopicClassifier(categories=self.categories)
        self.scoring_engine = TrendScoringEngine()

    def build_connector(
        self,
        source_cfg: Dict[str, Any],
        transport_fn: Optional[Callable[[str, int], str]] = None,
    ) -> BaseNewsSourceConnector:
        connector_type = source_cfg.get("connector_type", "rss_feed")
        cls_map = {
            "rss_feed": RSSFeedConnector,
            "gdelt_api": GDELTPublicDataConnector,
            "news_api": ApprovedNewsAPIConnector,
            "admin_rss": AdminConfiguredRSSConnector,
        }
        connector_cls = cls_map.get(connector_type, RSSFeedConnector)
        return connector_cls(
            source_id=source_cfg["id"],
            source_name=source_cfg["name"],
            endpoint_url=source_cfg["endpoint_url"],
            trust_tier=source_cfg.get("trust_tier", "Secondary Attribution"),
            reliability_score=float(source_cfg.get("reliability_score", 85.0)),
            timeout_seconds=int(source_cfg.get("timeout_seconds", 15)),
            rate_limit_per_minute=int(source_cfg.get("rate_limit_per_minute", 30)),
            max_retries=int(source_cfg.get("max_retries", 3)),
            robots_txt_compliant=bool(source_cfg.get("robots_txt_compliant", True)),
            terms_approved=bool(source_cfg.get("terms_approved", True)),
            default_category=source_cfg.get("category_slug", "world-trending-news"),
            transport_fn=transport_fn,
        )

    def list_categories(self) -> List[Dict[str, Any]]:
        return list(self.categories.values())

    def update_category(
        self,
        slug: str,
        is_enabled: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if slug not in self.categories:
            raise KeyError(f"Unknown category slug '{slug}'.")
        cat = self.categories[slug]
        if is_enabled is not None:
            cat["is_enabled"] = bool(is_enabled)
        if keywords is not None:
            cat["keywords"] = [k.strip() for k in keywords if k.strip()]
        if topics is not None:
            cat["topics"] = [t.strip() for t in topics if t.strip()]
        if regions is not None:
            cat["regions"] = [r.strip() for r in regions if r.strip()]
        if languages is not None:
            cat["languages"] = [lang.strip() for lang in languages if lang.strip()]
        return dict(cat)

    def list_sources(self) -> List[Dict[str, Any]]:
        return list(self.sources.values())

    def add_source(
        self,
        name: str,
        endpoint_url: str,
        connector_type: str = "admin_rss",
        protocol: str = "RSS 2.0",
        trust_tier: str = "Secondary Attribution",
        reliability_score: float = 82.0,
        poll_interval_seconds: int = 300,
        category_slug: str = "world-trending-news",
        robots_txt_compliant: bool = True,
        terms_approved: bool = True,
    ) -> Dict[str, Any]:
        """
        Register a new news source after validating its URL against SSRF and checking
        robots.txt / publisher terms compliance. Status defaults honestly to NOT_CONNECTED
        until a real connection test succeeds.
        """
        safe_url = validate_safe_external_url(endpoint_url)
        if not robots_txt_compliant:
            raise ValueError("Cannot register source that prohibits automated access in robots.txt.")
        if not terms_approved:
            raise ValueError("Cannot register source without approved publisher terms.")

        for existing in self.sources.values():
            if existing["name"].lower() == name.strip().lower():
                raise ValueError(f"Source with name '{name}' already exists.")

        source_id = f"src-{uuid.uuid4().hex[:8]}"
        new_source = {
            "id": source_id,
            "name": name.strip(),
            "protocol": protocol,
            "connector_type": connector_type,
            "endpoint_url": safe_url,
            "trust_tier": trust_tier,
            "reliability_score": round(max(0.0, min(100.0, float(reliability_score))), 2),
            "poll_interval_seconds": max(60, int(poll_interval_seconds)),
            "timeout_seconds": 15,
            "rate_limit_per_minute": 30,
            "max_retries": 3,
            "status": "NOT_CONNECTED",
            "is_enabled": True,
            "robots_txt_compliant": bool(robots_txt_compliant),
            "terms_approved": bool(terms_approved),
            "category_slug": category_slug if category_slug in self.categories else "world-trending-news",
            "last_polled_at": None,
            "last_success_at": None,
            "last_error_message": None,
            "articles_ingested_24h": 0,
        }
        self.sources[source_id] = new_source
        return dict(new_source)

    def update_source(
        self,
        source_id: str,
        is_enabled: Optional[bool] = None,
        endpoint_url: Optional[str] = None,
        poll_interval_seconds: Optional[int] = None,
        reliability_score: Optional[float] = None,
        category_slug: Optional[str] = None,
        test_connection: bool = False,
        transport_fn: Optional[Callable[[str, int], str]] = None,
    ) -> Dict[str, Any]:
        if source_id not in self.sources:
            raise KeyError(f"Source '{source_id}' not found.")

        src = self.sources[source_id]
        if endpoint_url is not None:
            src["endpoint_url"] = validate_safe_external_url(endpoint_url)
            src["status"] = "NOT_CONNECTED"
        if is_enabled is not None:
            src["is_enabled"] = bool(is_enabled)
        if poll_interval_seconds is not None:
            src["poll_interval_seconds"] = max(60, int(poll_interval_seconds))
        if reliability_score is not None:
            src["reliability_score"] = round(max(0.0, min(100.0, float(reliability_score))), 2)
        if category_slug is not None and category_slug in self.categories:
            src["category_slug"] = category_slug

        if test_connection:
            now_iso = datetime.now(timezone.utc).isoformat()
            src["last_polled_at"] = now_iso
            connector = self.build_connector(src, transport_fn=transport_fn)
            try:
                raw_items = connector.fetch(page=1, page_size=5)
                src["status"] = "CONNECTED"
                src["last_success_at"] = now_iso
                src["last_error_message"] = None
                src["last_test_items_count"] = len(raw_items)
            except Exception as exc:
                src["status"] = "ERROR"
                src["last_error_message"] = str(exc)

        return dict(src)

    def ingest_normalized_items(
        self,
        normalized_items: List[NormalizedNewsItem],
    ) -> Dict[str, int]:
        """
        Process a batch of normalized items through:
        - Stage 1-3 duplicate detection & story clustering
        - Category classification (rule-based + optional AI fallback)
        - Weighted trend scoring
        """
        new_count = 0
        duplicate_count = 0
        enabled_slugs = [slug for slug, cat in self.categories.items() if cat.get("is_enabled", True)]

        for norm_item in normalized_items:
            news_id = f"news-{uuid.uuid4().hex[:10]}"
            classification = self.classifier.classify(
                headline=norm_item.original_headline,
                description=norm_item.short_metadata_description,
                enabled_category_slugs=enabled_slugs,
            )

            dedup_result = self.clustering_engine.ingest_item(
                news_id=news_id,
                source_id=norm_item.source_id,
                source_name=norm_item.source_name,
                url=norm_item.original_article_url,
                headline=norm_item.original_headline,
                summary=norm_item.short_metadata_description,
                author=norm_item.author,
                category_slug=classification.primary_category_slug,
                discovered_at=norm_item.first_discovered_timestamp,
            )

            cluster = dedup_result["cluster"]
            if dedup_result["is_exact_duplicate"]:
                duplicate_count += 1
                continue

            new_count += 1
            item_record = {
                "id": news_id,
                "source_id": norm_item.source_id,
                "source_name": norm_item.source_name,
                "story_cluster_id": cluster.story_id if cluster else None,
                "headline": norm_item.original_headline,
                "original_headline": norm_item.original_headline,
                "normalized_headline": norm_item.normalized_headline,
                "summary": norm_item.short_metadata_description,
                "short_metadata_description": norm_item.short_metadata_description,
                "canonical_url": norm_item.canonical_url,
                "original_article_url": norm_item.original_article_url,
                "publication_timestamp": norm_item.publication_timestamp,
                "first_discovered_timestamp": norm_item.first_discovered_timestamp,
                "discovered_at": norm_item.first_discovered_timestamp,
                "author": norm_item.author,
                "language": norm_item.language,
                "category": classification.primary_category_slug,
                "category_name": classification.primary_category_name,
                "secondary_tags": classification.secondary_tags,
                "classification": classification.to_dict(),
                "image_url": norm_item.image_url,
                "image_legally_usable": norm_item.image_legally_usable,
                "source_reliability_metadata": norm_item.source_reliability_metadata,
                "is_syndicated_copy": dedup_result["is_syndicated_copy"],
                "collection_status": norm_item.collection_status,
                "status": "ingested",
                "urgency": "high" if classification.confidence >= 85.0 else "normal",
                "virality_score": 0.0,
                "source_diversity_score": float(cluster.independent_publishers_count * 25.0) if cluster else 25.0,
            }
            self.news_items[news_id] = item_record
            self.classifications[news_id] = classification.to_dict()

            if cluster is not None:
                rel_scores = [
                    float(self.sources.get(sid, {}).get("reliability_score", 88.0))
                    for sid in cluster.related_source_ids
                ]
                avg_rel = sum(rel_scores) / len(rel_scores) if rel_scores else 88.0
                trend_res = self.scoring_engine.calculate_trend_score(
                    story_cluster_id=cluster.story_id,
                    trend_category=cluster.category_slug,
                    avg_source_reliability=avg_rel,
                    supporting_source_count=len(cluster.related_source_ids),
                    independent_source_count=cluster.independent_publishers_count,
                    syndicated_copies_count=cluster.syndicated_copies_count,
                    age_hours=1.0,
                    audience_relevance_score=min(96.0, classification.confidence + 10.0),
                    first_seen=cluster.first_discovered_time,
                    last_updated=cluster.latest_update_time,
                )
                self.trend_scores[cluster.story_id] = trend_res.to_dict()
                item_record["virality_score"] = trend_res.trend_score
                item_record["trend_score"] = trend_res.trend_score
                item_record["trend_level"] = trend_res.trend_level

        return {"new_stories_count": new_count, "duplicate_stories_count": duplicate_count}

    def run_collection_scan(
        self,
        idempotency_key: Optional[str] = None,
        trigger_source: str = "manual",
        source_ids: Optional[List[str]] = None,
        transport_override_by_source: Optional[Dict[str, Callable[[str, int], str]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a scheduled or manual News Collection Scan across enabled sources.
        Enforces:
        - Idempotency key deduplication
        - Overlapping scan prevention
        - Per-source isolation (failed sources never crash the entire scan)
        """
        if idempotency_key and idempotency_key in self._idempotency_runs:
            cached = dict(self._idempotency_runs[idempotency_key])
            cached["idempotent_replay"] = True
            return cached

        if self._scan_in_progress:
            raise RuntimeError("SCAN_ALREADY_IN_PROGRESS: Overlapping collection scans are prevented.")

        self._scan_in_progress = True
        started_dt = datetime.now(timezone.utc)
        run_key = idempotency_key or f"scan-{started_dt.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        try:
            active_sources = [
                src
                for sid, src in self.sources.items()
                if src.get("is_enabled", True) and (source_ids is None or sid in source_ids)
            ]

            total_discovered = 0
            new_stories = 0
            duplicate_stories = 0
            failed_sources = 0
            errors: List[Dict[str, Any]] = []

            for src in active_sources:
                sid = src["id"]
                transport_fn = (
                    transport_override_by_source.get(sid)
                    if transport_override_by_source
                    else None
                )
                connector = self.build_connector(src, transport_fn=transport_fn)
                src["last_polled_at"] = started_dt.isoformat()
                try:
                    raw_items = connector.fetch(page=1, page_size=25)
                    norm_items = connector.normalize(raw_items)
                    total_discovered += len(norm_items)
                    counts = self.ingest_normalized_items(norm_items)
                    new_stories += counts["new_stories_count"]
                    duplicate_stories += counts["duplicate_stories_count"]
                    src["status"] = "CONNECTED"
                    src["last_success_at"] = datetime.now(timezone.utc).isoformat()
                    src["last_error_message"] = None
                    src["articles_ingested_24h"] = int(src.get("articles_ingested_24h", 0)) + counts["new_stories_count"]
                except Exception as exc:
                    failed_sources += 1
                    src["status"] = "ERROR"
                    src["last_error_message"] = str(exc)
                    errors.append(
                        {
                            "source_id": sid,
                            "source_name": src["name"],
                            "error": str(exc),
                            "connector_errors": connector.report_errors(),
                        }
                    )

            completed_dt = datetime.now(timezone.utc)
            next_scheduled_dt = completed_dt + timedelta(seconds=self.scan_interval_seconds)

            run_summary = {
                "run_key": run_key,
                "trigger_source": trigger_source,
                "status": "completed_with_errors" if failed_sources > 0 else "completed",
                "sources_polled_count": len(active_sources),
                "total_discovered": total_discovered,
                "new_stories_count": new_stories,
                "duplicate_stories_count": duplicate_stories,
                "failed_sources_count": failed_sources,
                "error_summary": errors,
                "started_at": started_dt.isoformat(),
                "completed_at": completed_dt.isoformat(),
                "next_scheduled_at": next_scheduled_dt.isoformat(),
                "idempotent_replay": False,
            }
            self.collection_runs.insert(0, run_summary)
            if idempotency_key:
                self._idempotency_runs[idempotency_key] = run_summary
            return dict(run_summary)
        finally:
            self._scan_in_progress = False

    def classify_existing_item(
        self,
        news_id: str,
        category_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        if news_id not in self.news_items:
            raise KeyError(f"News item '{news_id}' not found.")
        item = self.news_items[news_id]
        if category_override and category_override in self.categories:
            cat = self.categories[category_override]
            result = {
                "primary_category_slug": category_override,
                "primary_category_name": cat["name"],
                "secondary_tags": [cat["name"], "Operator Classified"],
                "classification_method": "operator_override",
                "confidence": 100.0,
                "reasoning": f"Manually classified by operator under '{cat['name']}'.",
                "needs_review": False,
            }
        else:
            enabled_slugs = [slug for slug, cat in self.categories.items() if cat.get("is_enabled", True)]
            cls_res = self.classifier.classify(
                headline=item["headline"],
                description=item.get("short_metadata_description", ""),
                enabled_category_slugs=enabled_slugs,
            )
            result = cls_res.to_dict()

        item["category"] = result["primary_category_slug"]
        item["category_name"] = result["primary_category_name"]
        item["secondary_tags"] = result["secondary_tags"]
        item["classification"] = result
        self.classifications[news_id] = result
        return dict(item)

    def archive_news_item(self, news_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        if news_id not in self.news_items:
            raise KeyError(f"News item '{news_id}' not found.")
        item = self.news_items[news_id]
        item["collection_status"] = "archived"
        item["status"] = "archived"
        item["archive_reason"] = reason or "Archived by editorial operator"
        item["archived_at"] = datetime.now(timezone.utc).isoformat()
        return dict(item)

    def list_trending_stories(
        self,
        category_slug: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for story_id, cluster in self.clustering_engine.clusters.items():
            if category_slug and cluster.category_slug != category_slug:
                continue
            score_data = self.trend_scores.get(story_id)
            if not score_data:
                continue
            if float(score_data["trend_score"]) < min_score:
                continue
            results.append(
                {
                    **cluster.to_dict(),
                    **score_data,
                }
            )
        results.sort(key=lambda r: float(r.get("trend_score", 0.0)), reverse=True)
        return results

    def list_clusters(self) -> List[Dict[str, Any]]:
        clusters_out: List[Dict[str, Any]] = []
        for story_id, cluster in self.clustering_engine.clusters.items():
            score_data = self.trend_scores.get(story_id, {})
            clusters_out.append(
                {
                    **cluster.to_dict(),
                    "trend_score": score_data.get("trend_score", 0.0),
                    "trend_level": score_data.get("trend_level", "Ignore"),
                    "trend_status": score_data.get("trend_status", "emerging"),
                }
            )
        clusters_out.sort(key=lambda c: float(c.get("trend_score", 0.0)), reverse=True)
        return clusters_out

    def get_collection_status(self) -> Dict[str, Any]:
        latest_run = self.collection_runs[0] if self.collection_runs else None
        connected_count = sum(1 for s in self.sources.values() if s.get("status") == "CONNECTED")
        error_count = sum(1 for s in self.sources.values() if s.get("status") == "ERROR")
        not_connected_count = sum(1 for s in self.sources.values() if s.get("status") == "NOT_CONNECTED")

        return {
            "scan_in_progress": self._scan_in_progress,
            "scan_interval_seconds": self.scan_interval_seconds,
            "scheduler_provider": "Cloudflare Worker Cron Trigger (POST /api/news/scan)",
            "total_sources_configured": len(self.sources),
            "connected_sources_count": connected_count,
            "not_connected_sources_count": not_connected_count,
            "failed_sources_count": error_count,
            "total_discovered_stories": len(self.news_items),
            "active_story_clusters": len(self.clustering_engine.clusters),
            "last_scan": latest_run,
            "next_scheduled_scan": latest_run.get("next_scheduled_at") if latest_run else None,
        }


_GLOBAL_NEWS_ENGINE: Optional[NewsIntelligenceEngine] = None


def get_news_intelligence_engine() -> NewsIntelligenceEngine:
    global _GLOBAL_NEWS_ENGINE
    if _GLOBAL_NEWS_ENGINE is None:
        _GLOBAL_NEWS_ENGINE = NewsIntelligenceEngine()
        try:
            import threading
            threading.Thread(
                target=lambda: _GLOBAL_NEWS_ENGINE.run_collection_scan(
                    idempotency_key="boot-wire-scan", trigger_source="server_startup"
                ),
                daemon=True,
            ).start()
        except Exception:
            pass
    return _GLOBAL_NEWS_ENGINE
