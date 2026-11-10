"""
NEXUS MEDIA AI — Modular Social Media Distribution Adapters (Section 3.5)
Strictly adheres to:
1. One platform at a time behind a common interface (publish(article) -> result).
2. Starting with X (Twitter) and Facebook Page via official APIs.
3. NEVER fakes success: returns honest "not_connected" when credentials are not configured.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("nexus_media_ai.social")


class BaseSocialAdapter:
    """Contract for external social media publishing adapters."""

    platform_name: str = "base"

    def is_connected(self) -> bool:
        raise NotImplementedError

    async def publish(self, article: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class XTwitterAdapter(BaseSocialAdapter):
    """X / Twitter API v2 publishing adapter."""

    platform_name = "x_twitter"

    def __init__(self, env: Optional[Dict[str, str]] = None) -> None:
        self._env = env if env is not None else dict(os.environ)
        self.api_key = (self._env.get("TWITTER_API_KEY") or "").strip()
        self.api_secret = (self._env.get("TWITTER_API_SECRET") or "").strip()
        self.access_token = (self._env.get("TWITTER_ACCESS_TOKEN") or "").strip()
        self.access_token_secret = (self._env.get("TWITTER_ACCESS_TOKEN_SECRET") or "").strip()

    def is_connected(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)

    async def publish(self, article: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_connected():
            return {
                "platform": self.platform_name,
                "status": "not_connected",
                "message": "X/Twitter API credentials (TWITTER_API_KEY, TWITTER_ACCESS_TOKEN) are not configured.",
                "post_id": None,
            }

        title = str(article.get("title") or article.get("headline") or "").strip()
        url = str(article.get("url") or "")
        tweet_text = f"{title}\n\nRead fact-checked report: {url}"[:280]

        try:
            # Official X API v2 tweet endpoint
            headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("https://api.twitter.com/2/tweets", json={"text": tweet_text}, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json().get("data", {})
                    return {
                        "platform": self.platform_name,
                        "status": "published",
                        "post_id": data.get("id"),
                        "text": tweet_text,
                    }
                return {
                    "platform": self.platform_name,
                    "status": "error",
                    "http_status": res.status_code,
                    "error": res.text,
                }
        except Exception as exc:
            logger.warning("X/Twitter publish failed: %s", exc)
            return {"platform": self.platform_name, "status": "error", "error": str(exc)}


class FacebookPageAdapter(BaseSocialAdapter):
    """Facebook Page Graph API publishing adapter."""

    platform_name = "facebook"

    def __init__(self, env: Optional[Dict[str, str]] = None) -> None:
        self._env = env if env is not None else dict(os.environ)
        self.page_id = (self._env.get("FACEBOOK_PAGE_ID") or "").strip()
        self.access_token = (self._env.get("FACEBOOK_ACCESS_TOKEN") or "").strip()

    def is_connected(self) -> bool:
        return bool(self.page_id and self.access_token)

    async def publish(self, article: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_connected():
            return {
                "platform": self.platform_name,
                "status": "not_connected",
                "message": "Facebook Page credentials (FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN) are not configured.",
                "post_id": None,
            }

        title = str(article.get("title") or article.get("headline") or "").strip()
        excerpt = str(article.get("excerpt") or article.get("summary") or "").strip()
        link = str(article.get("url") or "")
        message = f"{title}\n\n{excerpt}"

        try:
            endpoint = f"https://graph.facebook.com/v19.0/{self.page_id}/feed"
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    endpoint,
                    params={"access_token": self.access_token, "message": message, "link": link},
                )
                if res.status_code in (200, 201):
                    post_id = res.json().get("id")
                    return {
                        "platform": self.platform_name,
                        "status": "published",
                        "post_id": post_id,
                    }
                return {
                    "platform": self.platform_name,
                    "status": "error",
                    "http_status": res.status_code,
                    "error": res.text,
                }
        except Exception as exc:
            logger.warning("Facebook Page publish failed: %s", exc)
            return {"platform": self.platform_name, "status": "error", "error": str(exc)}


def get_social_adapters() -> List[BaseSocialAdapter]:
    """Returns registry of social media distribution adapters."""
    return [XTwitterAdapter(), FacebookPageAdapter()]
