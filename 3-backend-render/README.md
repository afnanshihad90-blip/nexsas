# 3 — Backend (Render) + Scheduler (Cloudflare Worker)
Render: GitHub এ push করো, New → Web Service, Root Directory = `backend`,
Build: `pip install -r requirements.txt`, Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
Health: `/api/system/health`. Env var গুলো `backend/.env.example` এ দেখো।
Worker: `cd cloudflare-worker && npx wrangler secret put WORKER_AUTH_SECRET && npx wrangler deploy`
