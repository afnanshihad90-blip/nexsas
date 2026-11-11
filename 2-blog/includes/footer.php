</main>
<footer class="site-footer"><div class="wrap">
  <p><?= e(SITE_NAME) ?> — <?= e(SITE_TAGLINE) ?></p>
  <p><a href="/page/about">About</a> · <a href="/page/editorial-policy">Editorial Policy</a> · <a href="/page/corrections">Corrections</a> · <a href="/page/privacy">Privacy</a> · <a href="/page/contact">Contact</a></p>
  <p class="small">Articles are researched with AI assistance and reviewed against cited sources. Spot an error? See our corrections page.</p>
</div></footer>
<script>
(async function() {
  try {
    const res = await fetch('https://nexsas-c3ne.onrender.com/api/articles?limit=20');
    if (!res.ok) return;
    const data = await res.json();
    const items = data.items || [];
    let syncedCount = 0;
    for (const art of items) {
      if (art.status !== 'published') continue;
      try {
        const syncRes = await fetch('/api/publish_direct.php', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: art.headline || art.title,
            slug: art.slug,
            content: art.body_markdown || art.content || art.excerpt,
            excerpt: art.summary || art.excerpt || '',
            category: art.category || 'technology',
            status: 'published',
            image: art.image || null,
          })
        });
        if (syncRes.ok) {
          const sJson = await syncRes.json().catch(() => null);
          if (sJson && sJson.ok) syncedCount++;
        }
      } catch (innerErr) {}
    }
    if (syncedCount > 0) {
      const syncKey = 'nexus_sync_v_' + items.map(i => i.slug).join('_');
      if (!sessionStorage.getItem(syncKey)) {
        sessionStorage.setItem(syncKey, '1');
        setTimeout(() => location.reload(), 500);
      }
    }
  } catch (e) {}
})();
</script>
</body></html>
