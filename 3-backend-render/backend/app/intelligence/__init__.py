"""
NEXUS MEDIA AI — Step 5: News Intelligence Engine Package
Provides:
- Supported News Niches & Category Management
- Modular News Source Connectors (RSS, GDELT, News API, Admin RSS)
- SSRF Protection & Untrusted Article Text Sanitization
- Multi-Stage Duplicate Detection & Event Story Clustering
- Weighted Trending Topic Detection Engine
- Hybrid Rule-Based + AI Fallback Topic Classification
- Scheduled News Collection Engine & Cloudflare Worker Cron Integration
"""

from app.intelligence.classifier import NewsTopicClassifier, TopicClassificationResult
from app.intelligence.connectors import (
    AdminConfiguredRSSConnector,
    ApprovedNewsAPIConnector,
    BaseNewsSourceConnector,
    ConnectorErrorReport,
    FetchedRawItem,
    GDELTPublicDataConnector,
    NormalizedNewsItem,
    RSSFeedConnector,
)
from app.intelligence.deduplication import (
    StoryClusterRecord,
    StoryClusteringEngine,
    compute_headline_similarity,
    normalize_canonical_url,
    normalize_headline,
)
from app.intelligence.engine import NewsIntelligenceEngine, get_news_intelligence_engine
from app.intelligence.scoring import TrendScoreResult, TrendScoringEngine
from app.intelligence.security import (
    SSRFValidationError,
    sanitize_untrusted_article_text,
    validate_safe_external_url,
)

__all__ = [
    "AdminConfiguredRSSConnector",
    "ApprovedNewsAPIConnector",
    "BaseNewsSourceConnector",
    "ConnectorErrorReport",
    "FetchedRawItem",
    "GDELTPublicDataConnector",
    "NewsIntelligenceEngine",
    "NewsTopicClassifier",
    "NormalizedNewsItem",
    "RSSFeedConnector",
    "SSRFValidationError",
    "StoryClusterRecord",
    "StoryClusteringEngine",
    "TopicClassificationResult",
    "TrendScoreResult",
    "TrendScoringEngine",
    "compute_headline_similarity",
    "get_news_intelligence_engine",
    "normalize_canonical_url",
    "normalize_headline",
    "sanitize_untrusted_article_text",
    "validate_safe_external_url",
]
