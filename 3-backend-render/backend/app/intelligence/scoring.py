"""
NEXUS MEDIA AI — Step 5: Weighted Trending Topic Detection Engine
Calculates deterministic, configurable trend scores with transparent breakdown:
- Source reliability: 25%
- Popularity and coverage: 25%
- Freshness: 20%
- Independent source coverage: 15%
- Audience relevance: 10%
- Story uniqueness: 5%

Trend Levels:
- 80–100: High priority trend
- 60–79: Normal priority trend
- 40–59: Low priority trend
- Below 40: Ignore

Honest Popularity Policy:
- Never fabricates search/social popularity metrics.
- When real external popularity telemetry is not connected, clearly labels popularity mode as
  'estimated_from_coverage' (derived from corroborated publisher count & velocity) or 'unavailable'.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


DEFAULT_TREND_WEIGHTS: Dict[str, float] = {
    "source_reliability": 0.25,
    "popularity_and_coverage": 0.25,
    "freshness": 0.20,
    "independent_source_coverage": 0.15,
    "audience_relevance": 0.10,
    "story_uniqueness": 0.05,
}


def classify_trend_level(score: float) -> str:
    """Map numeric 0-100 trend score to required Step 5 trend priority levels."""
    if score >= 80.0:
        return "High"
    if score >= 60.0:
        return "Normal"
    if score >= 40.0:
        return "Low"
    return "Ignore"


@dataclass
class TrendScoreResult:
    story_cluster_id: str
    trend_score: float
    trend_level: str
    score_breakdown: Dict[str, Any]
    confidence: float
    trend_category: str
    first_seen: str
    last_updated: str
    supporting_source_count: int
    independent_source_count: int
    trend_status: str
    popularity_estimate_mode: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_cluster_id": self.story_cluster_id,
            "trend_score": self.trend_score,
            "trend_level": self.trend_level,
            "score_breakdown": self.score_breakdown,
            "confidence": self.confidence,
            "trend_category": self.trend_category,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "supporting_source_count": self.supporting_source_count,
            "independent_source_count": self.independent_source_count,
            "trend_status": self.trend_status,
            "popularity_estimate_mode": self.popularity_estimate_mode,
        }


class TrendScoringEngine:
    """Configurable weighted trend scoring engine."""

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        merged = dict(DEFAULT_TREND_WEIGHTS)
        if weights:
            merged.update(weights)
        total = sum(merged.values()) or 1.0
        self.weights = {k: v / total for k, v in merged.items()}

    def calculate_trend_score(
        self,
        story_cluster_id: str,
        trend_category: str,
        avg_source_reliability: float,
        supporting_source_count: int,
        independent_source_count: int,
        syndicated_copies_count: int = 0,
        age_hours: float = 1.0,
        audience_relevance_score: float = 82.0,
        story_uniqueness_score: float = 85.0,
        live_popularity_score: Optional[float] = None,
        first_seen: Optional[str] = None,
        last_updated: Optional[str] = None,
    ) -> TrendScoreResult:
        """
        Compute weighted 0-100 trend score and detailed component breakdown.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        first_seen_iso = first_seen or now_iso
        last_updated_iso = last_updated or now_iso

        # 1. Source reliability (0-100)
        rel_component = max(0.0, min(100.0, float(avg_source_reliability)))

        # 2. Popularity & coverage (0-100) — never fabricate external popularity data
        if live_popularity_score is not None:
            pop_component = max(0.0, min(100.0, float(live_popularity_score)))
            popularity_mode = "verified_live_signal"
        elif supporting_source_count > 0:
            # Estimate strictly from multi-source coverage breadth & corroboration velocity
            coverage_base = min(100.0, 42.0 + (independent_source_count * 16.0) + (supporting_source_count * 4.5))
            pop_component = round(coverage_base, 2)
            popularity_mode = "estimated_from_coverage"
        else:
            pop_component = 0.0
            popularity_mode = "unavailable"

        # 3. Freshness (0-100) based on hours since publication/discovery
        safe_age = max(0.0, float(age_hours))
        if safe_age <= 1.0:
            freshness_component = 98.0
        elif safe_age <= 3.0:
            freshness_component = 90.0
        elif safe_age <= 6.0:
            freshness_component = 82.0
        elif safe_age <= 12.0:
            freshness_component = 70.0
        elif safe_age <= 24.0:
            freshness_component = 55.0
        else:
            freshness_component = max(15.0, 55.0 - ((safe_age - 24.0) * 1.5))

        # 4. Independent source coverage (0-100) — discounts syndicated wire copies
        ind_count = max(1, int(independent_source_count))
        if ind_count >= 5:
            ind_component = 98.0
        elif ind_count == 4:
            ind_component = 90.0
        elif ind_count == 3:
            ind_component = 82.0
        elif ind_count == 2:
            ind_component = 68.0
        else:
            ind_component = 45.0

        # 5. Audience relevance (0-100)
        aud_component = max(0.0, min(100.0, float(audience_relevance_score)))

        # 6. Story uniqueness (0-100) — penalizes heavily syndicated duplicates
        uniqueness_penalty = min(35.0, float(syndicated_copies_count) * 8.0)
        uniq_component = max(20.0, min(100.0, float(story_uniqueness_score) - uniqueness_penalty))

        weighted_total = (
            rel_component * self.weights["source_reliability"]
            + pop_component * self.weights["popularity_and_coverage"]
            + freshness_component * self.weights["freshness"]
            + ind_component * self.weights["independent_source_coverage"]
            + aud_component * self.weights["audience_relevance"]
            + uniq_component * self.weights["story_uniqueness"]
        )
        final_score = round(max(0.0, min(100.0, weighted_total)), 2)
        level = classify_trend_level(final_score)

        if level == "High":
            trend_status = "accelerating"
        elif level == "Normal":
            trend_status = "emerging"
        elif level == "Low":
            trend_status = "monitoring"
        else:
            trend_status = "ignored"

        confidence = round(
            min(
                99.0,
                max(
                    35.0,
                    (rel_component * 0.45)
                    + (ind_component * 0.35)
                    + (20.0 if popularity_mode == "verified_live_signal" else 12.0),
                ),
            ),
            2,
        )

        breakdown = {
            "weights": dict(self.weights),
            "components": {
                "source_reliability": round(rel_component, 2),
                "popularity_and_coverage": round(pop_component, 2),
                "freshness": round(freshness_component, 2),
                "independent_source_coverage": round(ind_component, 2),
                "audience_relevance": round(aud_component, 2),
                "story_uniqueness": round(uniq_component, 2),
            },
            "weighted_contributions": {
                "source_reliability": round(rel_component * self.weights["source_reliability"], 2),
                "popularity_and_coverage": round(pop_component * self.weights["popularity_and_coverage"], 2),
                "freshness": round(freshness_component * self.weights["freshness"], 2),
                "independent_source_coverage": round(ind_component * self.weights["independent_source_coverage"], 2),
                "audience_relevance": round(aud_component * self.weights["audience_relevance"], 2),
                "story_uniqueness": round(uniq_component * self.weights["story_uniqueness"], 2),
            },
            "popularity_measurement_status": popularity_mode,
            "syndicated_copies_discounted": syndicated_copies_count,
        }

        return TrendScoreResult(
            story_cluster_id=story_cluster_id,
            trend_score=final_score,
            trend_level=level,
            score_breakdown=breakdown,
            confidence=confidence,
            trend_category=trend_category,
            first_seen=first_seen_iso,
            last_updated=last_updated_iso,
            supporting_source_count=max(1, supporting_source_count),
            independent_source_count=ind_count,
            trend_status=trend_status,
            popularity_estimate_mode=popularity_mode,
        )
