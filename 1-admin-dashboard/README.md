# 1 — Admin Dashboard (InfinityFree account 1)
InfinityFree-এ Node চলে না, তাই আগে নিজের কম্পিউটারে build করতে হবে:

1. `.env.example` কপি করে `.env` নাম দাও, লেখো: `VITE_FASTAPI_BASE_URL="https://YOUR-RENDER-URL.onrender.com"`
   (secret key কখনো এখানে দেবে না)
2. `npm install` তারপর `npm run build`
3. `dist/` ফোল্ডারের ভেতরের সব ফাইল InfinityFree `htdocs/`-এ upload করো
4. `public-htaccess.txt` কে `.htaccess` নাম দিয়ে htdocs-এ রাখো
5. Render backend-এর `CORS_ALLOWED_ORIGINS` এ এই dashboard-এর URL বসাও
