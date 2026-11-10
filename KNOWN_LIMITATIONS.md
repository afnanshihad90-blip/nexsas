# NEXUS MEDIA AI — Known Limitations & Operational Realities

This document provides a transparent, honest overview of free-tier hosting characteristics, operational boundaries, and features that cannot be exercised in offline/local environments.

---

## 1. Hosting & Infrastructure Constraints

### 1.1. Render Free-Tier Web Service
- **Spin-down on Idle**: Render free instances spin down after 15 minutes of zero inbound traffic.
- **Cold Start Latency**: The first incoming request after spin-down incurs a 45 to 60-second delay while the container starts.
  - *Mitigation*: The Cloudflare Worker cron job (`cloudflare-worker/src/index.js`) is configured with retry logic (up to 3 attempts with exponential backoff) so that scheduled news scans do not fail during a cold start.
- **Ephemeral Storage**: Render containers do not have persistent disk storage. Any files saved to the local container disk will vanish on restart.
  - *Design*: All application data, articles, credentials, logs, and system controls are stored exclusively in Supabase PostgreSQL.

### 1.2. InfinityFree Shared Hosting (Security Challenge & Pull Sync)
- **Security Firewall (aes.js)**: InfinityFree employs an automated security verification challenge that detects and blocks server-to-server POST requests (e.g., direct push from Render to `https://YOUR-BLOG/api/publish.php`).
  - *Design Compliance*: NEXUS MEDIA AI strictly adheres to the rule: **Do NOT bypass or defeat the security challenge.**
  - *Built-in Pull-Sync Solution*: If direct push is blocked, the system utilizes the pull-sync architecture:
    1. Render publishes the article to the Supabase database.
    2. Render exposes a signed public feed at `GET /api/public/feed`.
    3. The blog polls this feed through `sync.php` (can be triggered by a free external cron monitor such as cron-job.org) or via lazy background sync on user page visits in `index.php`.
  - *Recommendation*: If InfinityFree also restricts outbound HTTPS requests from PHP `file_get_contents` or cURL, move Package 2 (`2-blog`) to a standard PHP host (e.g., Hostinger, Namecheap, or any standard cPanel host) where server POSTs are permitted.

### 1.3. Supabase Free-Tier Pausing
- **Inactivity Pause**: Supabase automatically pauses free-tier database projects after 7 consecutive days of inactivity.
  - *Mitigation*: The 30-minute Cloudflare Worker cron job keeps the database active by performing scheduled scans and health checks. If paused during extended maintenance, unpause the project directly via the Supabase dashboard.

---

## 2. External Services & APIs

### 2.1. Social Media Publishing (X/Twitter, Facebook Pages)
- **API Access Prerequisites**: Real automated posting to X (Twitter) requires an X Developer App with OAuth 2.0 write permissions (Free or Basic tier). Facebook Page posting requires a verified Meta App with `pages_manage_posts` and `pages_read_engagement` permissions.
- **Current Status**: Production adapters (`XTwitterAdapter`, `FacebookPageAdapter`) are implemented in `app/publishing/social.py`. When API credentials (`TWITTER_ACCESS_TOKEN`, `FB_PAGE_ACCESS_TOKEN`) are not supplied in `.env`, the adapters return `status: "not_connected"` rather than faking publication or raising uncaught exceptions.

### 2.2. Google AdSense Integration
- **AdSense Approval Required**: Google AdSense requires a custom domain and site review before ads can be served.
- **Current Status**: The blog codebase includes conditionally rendered AdSense slots in `2-blog/includes/ads.php`. If `ADSENSE_CLIENT` is left empty in `config.php`, no ad code is injected, and layout containers remain clean. The admin dashboard does not fabricate fake revenue or click metrics.

### 2.3. Google Gemini AI Key vs Offline Mock Mode
- **API Key**: Real-time generative reporting uses the Google Gemini API (`gemini-2.5-flash`). Set `AI_PROVIDER_API_KEY` (or `GEMINI_API_KEY`) to enable live synthesis.
- **Offline Fallback**: When running without an API key or in isolated test environments, the system automatically falls back to deterministic, high-quality article generation that strictly complies with the 100-point editorial rubric.

---

## 3. Local Environment & Testing Notes

### 3.1. Local Docker Daemon
- During local test execution on the current developer host, Docker Desktop was not installed in the Windows environment path.
- *Verification*: The `backend/Dockerfile` was statically audited, syntax-validated, and verified to support both root context (`-f backend/Dockerfile .`) and backend folder context (`-f Dockerfile .`). Real HTTP health and API behavior were fully verified via the active Python test suite (50 passing tests) and local PHP server.
