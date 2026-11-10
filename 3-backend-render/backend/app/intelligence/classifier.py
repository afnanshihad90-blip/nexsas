"""
NEXUS MEDIA AI — Step 5: News Topic Classifier
Classifies discovered news into the four primary supported niches:
1. Business & Finance (slug: business-finance)
2. World Trending News (slug: world-trending-news)
3. AI & Technology (slug: ai-technology)
4. Science & Space (slug: science-space)

Features:
- Rule-based keyword & topic filtering first.
- Optional AI fallback adapter when rule-based confidence is below threshold.
- Supports multiple secondary tags.
- Stores classification confidence (0-100) and human-readable reasoning.
- Flags low-confidence classifications (`needs_review = True`) for editorial review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


PRIMARY_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "business-finance": {
        "slug": "business-finance",
        "name": "Business & Finance",
        "sector_group": "Markets & Economy",
        "priority_weight": 10,
        "keywords": [
            "central bank",
            "interest rates",
            "inflation",
            "earnings",
            "treasury",
            "equities",
            "capital expenditure",
            "bond yields",
            "mergers",
            "ipo",
            "gdp",
            "federal reserve",
            "ecb",
            "liquidity",
            "tariff",
            "supply chain",
            "fiscal",
            "valuation",
        ],
        "topics": ["Monetary Policy", "Corporate Earnings", "Global Markets", "Supply Chain Finance"],
    },
    "world-trending-news": {
        "slug": "world-trending-news",
        "name": "World Trending News",
        "sector_group": "Global Affairs",
        "priority_weight": 10,
        "keywords": [
            "summit",
            "geopolitics",
            "treaty",
            "sanctions",
            "election",
            "parliament",
            "united nations",
            "diplomacy",
            "trade corridor",
            "energy grid",
            "minister",
            "coalition",
            "border",
            "maritime",
            "security council",
        ],
        "topics": ["Geopolitics", "International Policy", "Energy & Infrastructure", "Global Security"],
    },
    "ai-technology": {
        "slug": "ai-technology",
        "name": "AI & Technology",
        "sector_group": "Technology & Compute",
        "priority_weight": 10,
        "keywords": [
            "artificial intelligence",
            "llm",
            "semiconductor",
            "gpu",
            "foundry",
            "wafer",
            "datacenter",
            "cybersecurity",
            "quantum",
            "open source model",
            "inference",
            "neural",
            "packaging",
            "cloud compute",
            "chip",
            "lithography",
            "ai",
        ],
        "topics": ["Foundation Models", "Semiconductors", "Cloud Infrastructure", "Cybersecurity"],
    },
    "science-space": {
        "slug": "science-space",
        "name": "Science & Space",
        "sector_group": "Scientific Discovery",
        "priority_weight": 9,
        "keywords": [
            "orbital",
            "satellite",
            "exoplanet",
            "fusion",
            "telescope",
            "launch vehicle",
            "lunar",
            "astrophysics",
            "biotech",
            "cern",
            "nasa",
            "esa",
            "spacecraft",
            "payload",
            "gene",
            "superconductor",
            "climate observation",
        ],
        "topics": ["Orbital Launch Systems", "Deep Space Exploration", "Clean Energy Physics", "Biotechnology"],
    },
}


@dataclass
class TopicClassificationResult:
    primary_category_slug: str
    primary_category_name: str
    secondary_tags: List[str] = field(default_factory=list)
    classification_method: str = "rule_based"
    confidence: float = 75.0
    reasoning: str = ""
    needs_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_category_slug": self.primary_category_slug,
            "primary_category_name": self.primary_category_name,
            "secondary_tags": list(self.secondary_tags),
            "classification_method": self.classification_method,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "needs_review": self.needs_review,
        }


class NewsTopicClassifier:
    """
    Hybrid Rule-Based + Optional AI Fallback Classifier for Step 5 News Intelligence.
    """

    def __init__(
        self,
        categories: Optional[Dict[str, Dict[str, Any]]] = None,
        review_confidence_threshold: float = 65.0,
        ai_fallback_fn: Optional[Callable[[str, str], Optional[Dict[str, Any]]]] = None,
    ) -> None:
        self.categories = categories or dict(PRIMARY_CATEGORIES)
        self.review_confidence_threshold = review_confidence_threshold
        self.ai_fallback_fn = ai_fallback_fn

    def classify(
        self,
        headline: str,
        description: str = "",
        enabled_category_slugs: Optional[List[str]] = None,
    ) -> TopicClassificationResult:
        """
        Classify a news item using rule-based keyword/phrase scoring first,
        then optional AI fallback when rule-based confidence is low.
        """
        corpus = f"{headline or ''} {description or ''}".lower()
        headline_lower = (headline or "").lower()

        active_slugs = (
            [s for s in enabled_category_slugs if s in self.categories]
            if enabled_category_slugs
            else list(self.categories.keys())
        )
        if not active_slugs:
            active_slugs = list(self.categories.keys())

        scores: Dict[str, float] = {}
        matched_keywords_by_cat: Dict[str, List[str]] = {}

        for slug in active_slugs:
            cat = self.categories[slug]
            keywords = cat.get("keywords", [])
            matched: List[str] = []
            cat_score = 0.0
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in headline_lower:
                    cat_score += 26.0
                    matched.append(kw)
                elif kw_lower in corpus:
                    cat_score += 14.0
                    matched.append(kw)
            scores[slug] = cat_score
            matched_keywords_by_cat[slug] = matched

        ranked = sorted(active_slugs, key=lambda s: scores.get(s, 0.0), reverse=True)
        best_slug = ranked[0]
        best_raw_score = scores.get(best_slug, 0.0)

        # Collect secondary tags across all matching categories and matched keywords
        secondary_tags: List[str] = []
        for slug in ranked:
            if scores.get(slug, 0.0) > 0:
                cat_name = self.categories[slug]["name"]
                if cat_name not in secondary_tags:
                    secondary_tags.append(cat_name)
                for kw in matched_keywords_by_cat[slug][:3]:
                    if kw not in secondary_tags:
                        secondary_tags.append(kw)

        if best_raw_score >= 26.0:
            confidence = round(min(98.0, 62.0 + best_raw_score * 0.75), 2)
            matched_list = ", ".join(matched_keywords_by_cat[best_slug][:4])
            reasoning = (
                f"Rule-based classification matched category '{self.categories[best_slug]['name']}' "
                f"via high-signal indicators ({matched_list})."
            )
            return TopicClassificationResult(
                primary_category_slug=best_slug,
                primary_category_name=self.categories[best_slug]["name"],
                secondary_tags=secondary_tags[:6],
                classification_method="rule_based",
                confidence=confidence,
                reasoning=reasoning,
                needs_review=confidence < self.review_confidence_threshold,
            )

        # Optional AI fallback when rule-based score is weak
        if self.ai_fallback_fn is not None:
            try:
                ai_result = self.ai_fallback_fn(headline, description)
                if ai_result and ai_result.get("category_slug") in self.categories:
                    ai_slug = ai_result["category_slug"]
                    ai_conf = float(ai_result.get("confidence", 72.0))
                    ai_tags = list(ai_result.get("tags", secondary_tags))
                    return TopicClassificationResult(
                        primary_category_slug=ai_slug,
                        primary_category_name=self.categories[ai_slug]["name"],
                        secondary_tags=ai_tags[:6],
                        classification_method="ai_fallback",
                        confidence=round(ai_conf, 2),
                        reasoning=str(
                            ai_result.get(
                                "reasoning",
                                f"AI fallback classified story under {self.categories[ai_slug]['name']}.",
                            )
                        ),
                        needs_review=ai_conf < self.review_confidence_threshold,
                    )
            except Exception:
                pass

        # Low-confidence rule-based fallback
        if best_raw_score > 0:
            confidence = round(48.0 + best_raw_score * 0.6, 2)
            matched_list = ", ".join(matched_keywords_by_cat[best_slug][:3])
            reasoning = (
                f"Weak keyword match ({matched_list}) for '{self.categories[best_slug]['name']}'; "
                "flagged for editorial review."
            )
        else:
            best_slug = "world-trending-news" if "world-trending-news" in self.categories else ranked[0]
            confidence = 42.0
            secondary_tags = ["Unclassified Signal", "Needs Editorial Review"]
            reasoning = (
                "No strong domain keyword match found across configured niches; defaulted to "
                f"'{self.categories[best_slug]['name']}' and flagged for human review."
            )

        return TopicClassificationResult(
            primary_category_slug=best_slug,
            primary_category_name=self.categories[best_slug]["name"],
            secondary_tags=secondary_tags[:6],
            classification_method="rule_based",
            confidence=confidence,
            reasoning=reasoning,
            needs_review=confidence < self.review_confidence_threshold,
        )
