# NEXUS MEDIA AI — FastAPI Backend, Multi-Agent System & News Intelligence Engine (Steps 3, 4 & 5)

Production-grade Python 3.12+ FastAPI control plane, Multi-Agent Intelligence System, and News Intelligence Engine for **NEXUS MEDIA AI**, designed to connect asynchronously to the Supabase PostgreSQL database and serve the React control dashboard.

---

## 1. Directory Structure

```text
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 202611090002_step4_multi_agent_intelligence.py
│       └── 202611090003_step5_news_intelligence_engine.py
├── app/
│   ├── main.py                  # FastAPI factory, CORS, middleware, safe error handlers
│   ├── config.py                # Pydantic Settings with secret redaction & pooler support
│   ├── database.py              # Async SQLAlchemy 2.x engine, SSL, Supabase Session Pooler
│   ├── dependencies.py          # Auth dependencies, RBAC guards, pagination
│   ├── agents/
│   │   ├── orchestrator.py      # Central Orchestrator Agent & 10-Stage Workflow Engine
│   │   ├── specialists.py       # All 9 Specialist Agents & domain guardrails
│   │   ├── schemas.py           # Typed AgentTaskInput / AgentTaskOutput & code-injection guard
│   │   ├── queue.py             # Reliable Task Queue (idempotency, timeouts, retries, DLQ, cancel)
│   │   └── provider.py          # Modular AI Provider Abstraction (Gemini / OpenAI / Anthropic / Mock)
│   ├── intelligence/            # Step 5: News Intelligence Engine
│   │   ├── __init__.py
│   │   ├── security.py          # SSRF protection & untrusted article text / prompt-injection sanitizer
│   │   ├── connectors.py        # Modular RSS, GDELT, News API, and Admin RSS connectors
│   │   ├── deduplication.py     # 3-Stage duplicate detection & StoryCluster event clustering
│   │   ├── scoring.py           # Weighted TrendScoringEngine (25/25/20/15/10/5 breakdown)
│   │   ├── classifier.py        # Hybrid rule-based + AI fallback classifier across 4 primary niches
│   │   └── engine.py            # NewsIntelligenceEngine & Cloudflare Worker cron scan coordinator
│   ├── api/
│   │   ├── health.py            # GET /api/system/health, GET /api/system/health/database
│   │   ├── agents.py            # Agent registry, Orchestrator status, enable/disable/pause/resume/config/history
│   │   ├── articles.py          # GET/POST /api/articles, approve, publish
│   │   ├── news.py              # All 12 Step 5 News Intelligence endpoints
│   │   ├── publishing.py        # GET /api/publishing/jobs
│   │   ├── analytics.py         # GET /api/analytics/traffic, GET /api/analytics/revenue
│   │   └── logs.py              # GET /api/logs
│   ├── models/
│   │   └── entities.py          # SQLAlchemy 2.x models (Steps 2, 4, and 5)
│   ├── schemas/
│   │   └── payloads.py          # Strict Pydantic v2 request/response schemas
│   ├── services/
│   │   └── operations.py        # Async repository & business operations
│   ├── middleware/
│   │   └── security_headers.py  # Security headers, rate limiting, secret log redaction
│   └── security/
│       └── auth.py              # Argon2id password hashing, JWT signing, RBAC roles
├── tests/
│   ├── test_api.py              # Pytest + FastAPI TestClient integration suite
│   ├── test_foundation_unit.py  # Standard library unittest verification suite (Step 3)
│   ├── test_multi_agent_system.py # Automated test suite for Step 4 Multi-Agent System
│   └── test_news_intelligence.py  # Automated test suite for Step 5 News Intelligence Engine
├── alembic.ini
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 2. How to Configure Real News Sources & Cloudflare Worker Cron (Step 5)

The Step 5 News Intelligence Engine (`backend/app/intelligence/`) never assumes a news source is connected until a real test succeeds:
- **Initial State**: All sources default to `NOT_CONNECTED`.
- **Copyright & Terms Compliance**: Connectors store only headline, canonical URL, timestamps, author, language, category, and a short metadata description (truncated to <= 320 characters). Full copyrighted articles are never copied into the database.
- **SSRF & Prompt Injection Protection**: All source URLs and article links are validated by `validate_safe_external_url()` (blocking `localhost`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and cloud metadata `169.254.169.254`). Fetched text is sanitized by `sanitize_untrusted_article_text()` to strip HTML/scripts and neutralize prompt-injection directives.

### Registering & Testing Real News Sources
1. Start the FastAPI server and set `VITE_FASTAPI_BASE_URL` in your frontend environment.
2. In the dashboard sidebar, open **Intelligence → News Sources** or call `POST /api/news/sources` with an Admin Bearer JWT:
   ```json
   {
     "name": "Financial Times Global Economy RSS",
     "endpoint_url": "https://www.ft.com/rss/home",
     "connector_type": "admin_rss",
     "protocol": "RSS 2.0",
     "reliability_score": 94.0,
     "poll_interval_seconds": 300,
     "category_slug": "business-finance",
     "robots_txt_compliant": true,
     "terms_approved": true
   }
   ```
3. Click **Test Connection** in the UI (or call `PATCH /api/news/sources/{source_id}` with `{"test_connection": true}`) to execute a live fetch and transition the source status from `NOT_CONNECTED` to `CONNECTED`.

### Connecting Cloudflare Worker Cron Scheduler
Configure a Cloudflare Worker Cron Trigger (e.g. `*/5 * * * *`) to invoke `POST /api/news/scan`:
```bash
curl -X POST "https://your-backend.onrender.com/api/news/scan" \
  -H "Authorization: Bearer <OPERATOR_OR_CRON_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "cron-2026-11-09T14:35Z", "trigger_source": "cloudflare_worker_cron"}'
```
The scan engine prevents overlapping scans (`HTTP 409 SCAN_OVERLAP_PREVENTED`) and deduplicates replayed idempotency keys.

---

## 3. How to Configure a Real AI Provider (Step 4)

1. Open `backend/.env` (created from `backend/.env.example`) or your Render service's **Environment** tab.
2. Set the desired provider and server-side API key:
   ```env
   AI_PROVIDER="gemini"
   AI_PROVIDER_API_KEY="your-real-provider-api-key"
   ```

---

## 4. Database Migrations (Steps 2, 4 & 5)

Apply the Supabase SQL migrations in order in your Supabase SQL Editor or via Alembic:
1. `supabase/migrations/20261109000001_nexus_media_ai_foundation.sql` (Step 2 — 39 core tables)
2. `supabase/migrations/20261109000002_nexus_media_ai_multi_agent_system.sql` (Step 4 — Multi-Agent System tables)
3. `supabase/migrations/20261109000003_nexus_media_ai_news_intelligence_engine.sql` (Step 5 — News Intelligence Engine tables: `story_clusters`, `trend_scores`, `news_classifications`, `collection_runs`, `source_fetch_logs`, and 4 seeded primary categories)

---

## 5. Running Automated Tests

```bash
# Zero-dependency standard library unittest verification (Steps 3, 4 & 5)
python3 -m compileall backend
python3 -m unittest discover -s backend/tests -p "test_*.py" -v
```
