# NEXUS MEDIA AI — CHANGELOG

All notable changes, bug fixes, and architectural improvements across the 4 packages of NEXUS MEDIA AI are documented here.

---

## [1.0.0] - 2026-11-10

### 1. Package 1: Admin Dashboard (`1-admin-dashboard`)

#### Fixed & Resolved
- **Package Dependency Incompatibilities (`package.json`)**:
  - *Problem*: `package.json` had fictitious and unresolved versions (`typescript: ^7.0.0`, `vite: ^8.0.0`, `@vitejs/plugin-react: ^6.0.0`).
  - *Fix*: Pinned to stable production releases: Vite 6.2.0, React 19.0.0, `@vitejs/plugin-react` 4.3.4, TypeScript 5.7.3, TailwindCSS 4.0.9, tsx 4.21.0. Resolved clean `npm install` with 0 vulnerabilities.
- **Node ESM Test Execution Failure**:
  - *Problem*: Default test script `node --test src/**/*.test.ts` crashed with `ERR_UNKNOWN_FILE_EXTENSION` because Node's native test runner does not transpile TypeScript or resolve extensionless imports (`./apiService`).
  - *Fix*: Configured `npm test` to use `tsx --test src/**/*.test.ts`. All 16 unit tests now pass cleanly.
- **TypeScript Type Checking (`npm run lint`)**:
  - *Problem*: Missing type declarations and stricter type checks in React 19 components.
  - *Fix*: Corrected component typings and prop interfaces across all views. `npm run lint` (`tsc --noEmit`) passes with 0 errors.
- **Fabricated Live Metrics Removed**:
  - *Problem*: Dashboard showed static mock numbers for revenue, views, and article counts even when disconnected, violating the design rule ("Unknown = Not connected").
  - *Fix*: Updated `src/utils/dashboardLogic.ts` so that when `backendConnected === false`, metrics explicitly display `"Not connected"` rather than fake figures.

#### Added
- **Authentication Modal (`src/components/LoginModal.tsx`)**:
  - Added user login interface communicating with FastAPI backend `POST /api/auth/login`. Handles JWT token storage in `localStorage` and header injection.
- **Blog Integration Panel (`src/components/BlogIntegrationPanel.tsx`)**:
  - Added administrative panel with a one-click "Test Blog Connection" button calling `POST /api/blog/test`. Displays HTTP status, response payload, and deployment hints (push vs pull mode).
- **Article Editorial & Publishing Panel (`src/components/ArticleManagementPanel.tsx`)**:
  - Added controls to view staged articles, execute one-click manual approvals (`POST /api/articles/{id}/approve`), trigger direct publishing (`POST /api/blog/publish/{id}`), and run the autonomous editorial pipeline (`POST /api/articles/pipeline/run`).
- **Emergency Stop Banner (`src/components/EmergencyStopBanner.tsx`)**:
  - Added prominent header banner displaying live kill-switch status with toggle control (`POST /api/system/kill-switch`).

---

### 2. Package 2: Blog (`2-blog`)

#### Fixed & Resolved
- **PHP Syntax Validation**:
  - Validated all PHP scripts (`index.php`, `article.php`, `category.php`, `page.php`, `search.php`, `sitemap.php`, `sync.php`, `api/publish.php`, and `includes/*.php`) using `php -l`. All files compiled cleanly with 0 syntax errors.
- **HMAC Signature Canonical Compatibility**:
  - *Problem*: Cross-language signing between Python and PHP had potential mismatches in timestamp formatting and payload concatenation.
  - *Fix*: Enforced canonical format `hash_hmac('sha256', "{$timestamp}.{$idempotencyKey}.{$rawBody}", $secret)` across `blog/api/publish.php` and `blog/includes/sync_lib.php`. Verified by automated cross-language test suite.
- **Apache Rewrite Rules (`.htaccess`)**:
  - Verified and tuned Apache mod_rewrite rules for SEO-friendly URLs (`/article/{slug}`, `/category/{slug}`, `/page/{slug}`, `/sitemap.xml`) to ensure compatibility with shared hosting like InfinityFree.

#### Added
- **Local Testing Support (`router.php` & `schema_sqlite.sql`)**:
  - Added SQLite schema and custom PHP built-in server router (`router.php`) to enable full offline and automated test execution of all blog endpoints without requiring an external MySQL daemon.
- **Automated Page Verification Suite (`scripts/test_blog_pages.php`)**:
  - Created automated test script verifying HTTP 200 responses and valid HTML/XML output for homepage, all 4 categories, article view, search, static pages, and sitemap.

---

### 3. Package 3: Backend & Cloudflare Worker (`3-backend-render`)

#### Fixed & Resolved
- **Render Dockerfile Context Incompatibility (`ModuleNotFoundError: No module named 'app'`)**:
  - *Problem*: Render build context defaults to repository root, while local builds typically execute from `backend/`.
  - *Fix*: Re-engineered `backend/Dockerfile` using a multi-stage adaptive copy strategy that detects whether the build context is the repository root or the `backend/` directory. Verified with real Docker syntax and path checks.
- **Pytest-Asyncio Configuration**:
  - *Problem*: Running `pytest` produced asyncio loop scope warnings and failed asynchronous fixtures.
  - *Fix*: Created `pytest.ini` with `asyncio_mode = auto` and `asyncio_default_loop_scope = function`. Pytest suite now runs 50 tests with 100% pass rate.
- **SQLAlchemy Model & Migration Schema Mismatch**:
  - *Problem*: `app/services/operations.py` and `app/models/entities.py` used outdated column names (`title`, `content`) conflicting with Supabase SQL migrations (`headline`, `summary`, `body_markdown`, `stage`, etc.). Additionally, `story_clusters` lacked `primary_category`.
  - *Fix*: Aligned all models, Pydantic schemas (`app/schemas/payloads.py`), and operational services to the authoritative database schema.
- **Supabase vs Alembic Conflict**:
  - *Problem*: Two migration systems co-existed out of sync.
  - *Fix*: Formally established Supabase SQL migrations (`4-database-supabase/migrations/`) as the single source of truth and documented database governance in `DATABASE_SCHEMA.md`.

#### Added
- **Live Google Gemini API Provider & Offline Fallback (`app/agents/provider.py`)**:
  - Implemented `AIProvider` calling the official Google Gemini REST API (`gemini-2.5-flash`) when `AI_PROVIDER_API_KEY` (or `GEMINI_API_KEY`) is set.
  - Added deterministic, high-quality offline generation fallback when running without API keys or in air-gapped test environments.
- **Human-Quality Editorial Writing Rules & Scoring Rubric (`app/agents/specialists.py`)**:
  - Built 100-point quality scoring function (`score_editorial_quality`):
    - Accuracy & Source Attribution: 25 pts
    - Originality & Analysis: 20 pts
    - Readability & Flow: 20 pts
    - Research Depth: 15 pts
    - Natural Sentence Variety: 10 pts
    - Audience Value: 10 pts
  - Enforced strict writing rules in `NewsWriterAgent`: markdown source citations (`[Publisher](url)`), varied sentence lengths, no clickbait or invented facts, and a mandatory automated newsroom disclosure paragraph.
  - Set quality threshold >= 85 for automated publishing.
- **Licensed Image Sourcing Guardrails (`app/content/image_sourcing.py`)**:
  - Enforced license filtering for Wikimedia Commons, Pexels, and Unsplash. Strictly rejects AI-generated media; verifies CC BY-SA, CC0, or platform-approved public licenses.
- **Dual Publishing Modes (`PUBLISHING_MODE=manual|auto`)**:
  - In `auto` mode: requires trend score >= 60, >= 3 independent sources, quality score >= 85, no conflicts, and kill switch disengaged.
  - In `manual` mode (default): stages all articles as `Awaiting Approval` for editorial sign-off.
- **Global Emergency Stop / Kill Switch (`app/api/system.py`)**:
  - Implemented `GET /api/system/kill-switch` and `POST /api/system/kill-switch`.
  - Blocks all publishing requests (`409 Conflict: KILL_SWITCH_ENGAGED`) and stops orchestrator pipeline execution immediately when active.
- **Autonomous Editorial Pipeline (`app/services/pipeline.py`)**:
  - Created end-to-end autonomous pipeline executing all 10 agent stages (scan → cluster → research → fact-check → write → editorial review → media sourcing → SEO → approval/publishing).
  - Exposed via `POST /api/articles/pipeline/run`.
- **Social Media Distribution Adapters (`app/publishing/social.py`)**:
  - Built extensible social publishing architecture (`BaseSocialAdapter`, `XTwitterAdapter`, `FacebookPageAdapter`).
  - Accurately returns `status: "not_connected"` when API credentials are absent, adhering to honest telemetry rules.
- **Cloudflare Worker Cron Ingestion & Webhook Security (`app/api/blog.py`)**:
  - Validates incoming worker cron webhooks via HMAC SHA-256 with a 300-second replay window and slot-based mutex locks to prevent overlapping executions during Render spin-up.

---

### 4. Package 4: Database (`4-database-supabase`)

#### Added
- **Migration 0004 (`migrations/0004_news_engine_and_system_controls.sql`)**:
  - Added `primary_category` column to `story_clusters`.
  - Added `system_controls` table for persisting global kill-switch state.
  - Added composite indexes for rapid article stage querying (`stage, scheduled_at`).
- **Database Schema Documentation (`DATABASE_SCHEMA.md`)**:
  - Documented table relationships, constraints, column mappings, and migration procedures.
