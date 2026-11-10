"""Licensed image sourcing (no AI generation). Pexels, Unsplash, Wikimedia Commons.

Every result carries license + attribution so the blog can show credit.
Unsplash: hotlink the API URLs and ping `download_location` when an image is chosen.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

STOPWORDS = set("the a an of to in on for and with from by at is are was were be as that this it its new says said".split())
ALLOWED_COMMONS_LICENSES = ("cc0", "public domain", "cc by", "cc-by", "cc by-sa", "cc-by-sa")


def extract_keywords(headline: str, limit: int = 4) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", headline) if w.lower() not in STOPWORDS and len(w) > 2]
    return " ".join(words[:limit])


def commons_license_ok(license_short: str) -> bool:
    low = (license_short or "").lower()
    if "nc" in low.split() or "-nc" in low or " nc" in low or "nd" in low.replace("and", ""):
        return False
    return any(low.startswith(a) for a in ALLOWED_COMMONS_LICENSES)


def score_relevance(text: str, query: str) -> float:
    q = {w.lower() for w in query.split()}
    t = {w.lower() for w in re.findall(r"[A-Za-z0-9]+", text or "")}
    return len(q & t) / max(len(q), 1)


async def search_pexels(client: Any, key: str, query: str) -> List[Dict[str, Any]]:
    r = await client.get("https://api.pexels.com/v1/search", params={"query": query, "per_page": 8, "orientation": "landscape"},
                         headers={"Authorization": key})
    r.raise_for_status()
    return [{
        "provider": "pexels", "url": p["src"]["large2x"], "alt": p.get("alt") or query,
        "credit": p["photographer"], "credit_url": p["url"], "license": "Pexels License",
        "width": p["width"], "height": p["height"],
    } for p in r.json().get("photos", [])]


async def search_unsplash(client: Any, key: str, query: str) -> List[Dict[str, Any]]:
    r = await client.get("https://api.unsplash.com/search/photos",
                         params={"query": query, "per_page": 8, "orientation": "landscape"},
                         headers={"Authorization": f"Client-ID {key}"})
    r.raise_for_status()
    return [{
        "provider": "unsplash", "url": p["urls"]["regular"], "alt": p.get("alt_description") or query,
        "credit": p["user"]["name"], "credit_url": p["user"]["links"]["html"] + "?utm_source=nexus_media_ai&utm_medium=referral",
        "license": "Unsplash License", "width": p["width"], "height": p["height"],
        "download_location": p["links"]["download_location"],
    } for p in r.json().get("results", [])]


async def search_commons(client: Any, query: str) -> List[Dict[str, Any]]:
    r = await client.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6,
        "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1280, "format": "json"})
    r.raise_for_status()
    out = []
    for page in (r.json().get("query", {}).get("pages", {})).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if not commons_license_ok(lic) or not info.get("thumburl"):
            continue
        out.append({
            "provider": "wikimedia", "url": info["thumburl"],
            "alt": re.sub("<.*?>", "", meta.get("ImageDescription", {}).get("value", query))[:200],
            "credit": re.sub("<.*?>", "", meta.get("Artist", {}).get("value", "Wikimedia Commons")),
            "credit_url": info.get("descriptionurl"), "license": lic,
            "width": info.get("thumbwidth", 0), "height": info.get("thumbheight", 0),
        })
    return out


async def pick_best_image(headline: str, pexels_key: str = "", unsplash_key: str = "", prefer_commons: bool = False) -> Optional[Dict[str, Any]]:
    import httpx
    query = extract_keywords(headline)
    candidates: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15) as client:
        jobs = []
        if prefer_commons:
            jobs.append(search_commons(client, query))
        if pexels_key:
            jobs.append(search_pexels(client, pexels_key, query))
        if unsplash_key:
            jobs.append(search_unsplash(client, unsplash_key, query))
        if not prefer_commons:
            jobs.append(search_commons(client, query))
        for job in jobs:
            try:
                candidates += await job
            except Exception:
                continue  # one provider failing must not stop the pipeline
        landscape = [c for c in candidates if c.get("width", 0) >= 1000 and c.get("width", 0) >= c.get("height", 0)]
        pool = landscape or candidates
        if not pool:
            return None
        best = max(pool, key=lambda c: score_relevance(c.get("alt", ""), query))
        if best["provider"] == "unsplash" and best.get("download_location"):
            try:
                await client.get(best["download_location"], headers={"Authorization": f"Client-ID {unsplash_key}"})
            except Exception:
                pass
        return best
