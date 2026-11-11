<aside class="sidebar">
<?php ad_slot('sidebar');
$rows = db()->query("SELECT slug,title FROM articles WHERE status='published' ORDER BY views DESC, published_at DESC LIMIT 5")->fetchAll(); ?>
<h3>Popular</h3><ol class="popular"><?php foreach ($rows as $r): ?><li><a href="/article/<?= e($r['slug']) ?>"><?= e($r['title']) ?></a></li><?php endforeach; ?></ol>
<div class="newsletter"><h3>Newsletter</h3><p class="small">Daily briefing — coming soon.</p></div>
</aside>
