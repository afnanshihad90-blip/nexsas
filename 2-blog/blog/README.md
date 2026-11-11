# 2 — Blog (InfinityFree account 2)
1. InfinityFree panel এ MySQL database বানাও, phpMyAdmin এ `schema.sql` import করো
2. `config.sample.php` কপি করে `config.php` করো, DB info + `SITE_URL` + `NEXUS_API_SECRET` বসাও
   (NEXUS_API_SECRET = Render এর BLOG_SIGNING_SECRET একই হবে)
3. সব ফাইল `htdocs/` এ upload করো (`README.md` বাদ দিলেও চলবে)
4. `robots.txt` এ YOUR-BLOG-DOMAIN বদলাও
5. Render এ `BLOG_ENDPOINT=https://YOUR-BLOG/api/publish.php` দাও
InfinityFree POST block করলে `NEXUS_FEED_URL` দিয়ে pull-sync চলবে।
