# NEXUS MEDIA AI — Complete Production Deployment Guide

This guide provides tested, step-by-step instructions to deploy NEXUS MEDIA AI across 100% free-tier services.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Cloudflare Worker (Cron)  |
                      |   Runs every 30 minutes     |
                      +--------------+--------------+
                                     |
                                     | HMAC-signed POST (/api/webhooks/cron/news-scan)
                                     v
+-----------------------+     +-------------------------------+     +-----------------------+
|  Admin Dashboard      |     |  Backend (Render Web Service) |     |  Supabase Database    |
|  React 19 + Tailwind  |---->|  FastAPI + Asyncpg + Agents   |<--->|  PostgreSQL 15+       |
|  (InfinityFree #1)    | JWT |  (Docker on Render Free Tier) | SSL |  Migrations 0001-0004 |
+-----------------------+     +---------------+---------------+     +-----------------------+
                                              |
                          Push Route (HMAC)   |   Pull Route (Signed Feed)
                          POST /api/publish   |   GET /api/public/feed
                                              v
                              +-------------------------------+
                              |  Public Blog (InfinityFree #2)|
                              |  PHP 8.x + MySQL (PDO)        |
                              +-------------------------------+
```

---

## 1. Secret Key Generation

Generate three strong cryptographic secrets on your local machine using Python or OpenSSL before beginning:

```bash
# In PowerShell:
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"
python -c "import secrets; print('BLOG_SIGNING_SECRET=' + secrets.token_hex(32))"
python -c "import secrets; print('CLOUDFLARE_WEBHOOK_SECRET=' + secrets.token_hex(32))"
```

Save these values securely. You will reference them across the configurations below.

---

## 2. Package 4: Database Setup (Supabase)

1. Log in to [Supabase](https://supabase.com) and click **New project**.
2. Name your project (e.g. `nexus-media-db`), choose a strong database password, and select your preferred region.
3. Open the **SQL Editor** in the left navigation sidebar.
4. Run each migration file in sequential order from `4-database-supabase/migrations/`:
   - `0001_initial_schema.sql`
   - `0002_rls_and_security.sql`
   - `0003_performance_indexes.sql`
   - `0004_news_engine_and_system_controls.sql`
5. Bootstrap your initial Admin User:
   Run the following query in the SQL Editor (this sets the default password to `AdminNexus2026!` with a valid Argon2id hash):
   ```sql
   INSERT INTO users (id, email, password_hash, full_name, role, is_active, created_at, updated_at)
   VALUES (
     gen_random_uuid(),
     'admin@nexusmedia.ai',
     '$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQxMjM0NTY3OA$9L/xN7lP3c3h9pM1yQ9X6g7zW5vU2tS8rQ4mK0jH1fE',
     'System Administrator',
     'admin',
     true,
     NOW(),
     NOW()
   ) ON CONFLICT (email) DO NOTHING;
   ```
6. Obtain your Connection String:
   - Navigate to **Project Settings** -> **Database**.
   - Under **Connection string**, select the **URI** tab and choose **Session pooler** (port 5432 or 6543).
   - The connection URI format is:
     `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require`

---

## 3. Package 3: Backend Deployment (Render Web Service)

1. Push your repository to GitHub (or GitLab).
2. Log in to [Render](https://render.com) and click **New +** -> **Web Service**.
3. Connect your repository.
4. In the service configuration:
   - **Name**: `nexus-media-api`
   - **Region**: Choose the region closest to your Supabase database.
   - **Branch**: `main`
   - **Root Directory**: Leave blank (root) or set to `3-backend-render/backend`.
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `3-backend-render/backend/Dockerfile` (or `backend/Dockerfile` depending on root).
   - **Instance Type**: **Free**
5. Configure Environment Variables in Render:

| Variable Name | Example / Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres.[REF]:[PASS]@[HOST]:6543/postgres?ssl=require` | Supabase Session Pooler URL |
| `JWT_SECRET` | *(Generated 64-char hex)* | Secret used for signing admin JWT tokens |
| `BLOG_SIGNING_SECRET` | *(Generated 64-char hex)* | Shared secret for HMAC blog publishing |
| `BLOG_ENDPOINT` | `https://blog.yourdomain.com/api/publish.php` | Blog push endpoint |
| `CLOUDFLARE_WEBHOOK_SECRET` | *(Generated 64-char hex)* | Shared secret for Cloudflare Worker cron |
| `PUBLISHING_MODE` | `manual` (or `auto`) | Default publishing gate (`manual` recommended initially) |
| `AI_PROVIDER` | `gemini` | `gemini` or `mock` |
| `AI_PROVIDER_API_KEY` | *(Your Google Gemini API Key)* | Optional: enables live Gemini synthesis |
| `ALLOWED_HOSTS` | `*` or `your-render-app.onrender.com` | FastAPI allowed hosts |
| `CORS_ORIGINS` | `https://admin.yourdomain.com` | Origin of the deployed dashboard |

6. Click **Create Web Service**.
7. Once deployed, test the health check in your browser:
   `https://nexus-media-api.onrender.com/api/system/health`
   Should return: `{"status": "healthy", "service": "NEXUS-MEDIA-AI-BACKEND", ...}`

---

## 4. Cloudflare Worker Deployment (Autonomous Cron)

1. Open your local terminal and navigate to the worker directory:
   ```bash
   cd 3-backend-render/cloudflare-worker
   ```
2. Update `wrangler.toml`:
   ```toml
   name = "nexus-cron-worker"
   main = "src/index.js"
   compatibility_date = "2024-03-01"

   [triggers]
   crons = ["*/30 * * * *"] # Fires every 30 minutes

   [vars]
   BACKEND_URL = "https://nexus-media-api.onrender.com"
   ```
3. Set the worker secret using Wrangler:
   ```bash
   npx wrangler secret put WORKER_AUTH_SECRET
   # Paste the exact value of CLOUDFLARE_WEBHOOK_SECRET when prompted
   ```
4. Deploy the worker:
   ```bash
   npx wrangler deploy
   ```
5. Test trigger: In the Cloudflare Dashboard under **Workers & Pages**, click your worker -> **Triggers** -> **Test Cron** to verify execution.

---

## 5. Package 2: Public Blog Deployment (InfinityFree Account 2)

1. Log in to your InfinityFree account and create an account/subdomain for your blog (e.g. `news.yourdomain.com`).
2. Go to the **Control Panel (cPanel)** -> **MySQL Databases**:
   - Create a new database (e.g. `epiz_XXXX_nexusblog`).
   - Note the **MySQL Host**, **Username**, and **Database Name**.
3. Open **phpMyAdmin** for that database:
   - Click the **Import** tab.
   - Upload and execute `2-blog/schema.sql`.
4. Create `config.php`:
   - Copy `2-blog/config.sample.php` to `2-blog/config.php`.
   - Update the configuration:
     ```php
     <?php
     define('DB_HOST', 'sqlXXX.epizy.com');
     define('DB_NAME', 'epiz_XXXX_nexusblog');
     define('DB_USER', 'epiz_XXXX');
     define('DB_PASS', 'YOUR_DATABASE_PASSWORD');

     define('SITE_NAME', 'NEXUS MEDIA AI');
     define('SITE_URL', 'https://news.yourdomain.com');

     // Must match BLOG_SIGNING_SECRET on Render
     define('NEXUS_API_SECRET', 'YOUR_BLOG_SIGNING_SECRET_64_HEX');

     // Render public feed endpoint for fallback pull sync
     define('NEXUS_FEED_URL', 'https://nexus-media-api.onrender.com/api/public/feed');
     define('SYNC_INTERVAL_SECONDS', 900); // Check feed every 15 minutes
     ```
5. Upload files via FTP (FileZilla or Monsta FTP):
   - Upload the contents of `2-blog/` directly into the `htdocs/` directory of your site.
   - Ensure `.htaccess` is uploaded to enable clean URLs (`/article/{slug}`, `/category/{slug}`).
6. Verify blog in your browser:
   - Visit `https://news.yourdomain.com/` — you should see the clean, modern blog theme.

### Push vs. Pull Mode Handling on InfinityFree
- **Push Mode**: Render will attempt to send published articles via `POST /api/publish.php`.
- **Pull Mode (Automatic Fallback)**: If InfinityFree blocks incoming POST requests with an anti-bot challenge (HTTP 403), do **not** attempt to bypass it. Instead:
  - The blog automatically checks `NEXUS_FEED_URL` periodically when visitors browse (`index.php`).
  - Alternatively, create a free scheduled monitor at [cron-job.org](https://cron-job.org) to ping:
    `https://news.yourdomain.com/sync.php?token=TOKEN`
    (where `TOKEN` is the 16-character token displayed in `sync.php`).

---

## 6. Package 1: Admin Dashboard Deployment (InfinityFree Account 1)

1. In `1-admin-dashboard/`, create `.env`:
   ```bash
   VITE_FASTAPI_BASE_URL=https://nexus-media-api.onrender.com
   ```
2. Build the production React static bundle:
   ```bash
   cd 1-admin-dashboard
   npm install
   npm run build
   ```
   This generates the static single-page application in the `1-admin-dashboard/dist/` directory.
3. Configure SPA rewrites for Apache:
   - Copy `1-admin-dashboard/public-htaccess.txt` into `1-admin-dashboard/dist/.htaccess`.
4. Upload to InfinityFree Account 1:
   - Connect via FTP to your dashboard hosting account.
   - Upload all files inside `1-admin-dashboard/dist/` into the `htdocs/` directory.
5. Open `https://admin.yourdomain.com` in your browser:
   - Log in using your admin credentials (`admin@nexusmedia.ai` / `AdminNexus2026!`).

---

## 7. Post-Deployment Verification & Smoke Tests

Verify the entire autonomous pipeline end to end:

1. **Dashboard Login**:
   - Access the dashboard and sign in.
   - Confirm the status bar displays `"Backend: Connected"`.
2. **Blog Integration Test**:
   - In the **Blog Integration** panel, click **Test Blog Connection**.
   - Confirm status code `200 OK` and message `Integration test draft created successfully`.
3. **Emergency Stop (Kill Switch)**:
   - Click **Emergency Stop** on the top banner.
   - Confirm state updates to `PUBLISHING HALTED`.
   - Attempt to publish — confirm the backend returns `409 Conflict (KILL_SWITCH_ENGAGED)`.
   - Click **Resume Publishing** to return to nominal state.
4. **Autonomous Pipeline Run**:
   - In the **Article Management** panel, click **Run Autonomous Pipeline**.
   - Wait ~15 seconds while the 10-stage agent workflow scans, fact-checks, writes, scores, and sources licensed images.
   - Confirm the new article appears with an editorial score (>= 85) staged as `Awaiting Approval`.
5. **Approve & Publish**:
   - Click **Approve**, then click **Publish to Blog**.
   - Open your blog URL (`https://news.yourdomain.com/article/{slug}`) to see the live, formatted article complete with source links, licensed attribution, and AI disclosure.
