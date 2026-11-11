<?php require_once __DIR__ . '/includes/bootstrap.php'; require_once __DIR__ . '/includes/card.php'; maybe_sync();
$rows = [];
try {
  $rows = db()->query("SELECT * FROM articles WHERE status='published' ORDER BY published_at DESC LIMIT 25")->fetchAll();
} catch (Throwable $t) {}
$pageTitle = SITE_NAME . ' — ' . SITE_TAGLINE; require __DIR__ . '/includes/header.php'; ?>
<?php ad_slot('top'); ?>
<div class="layout"><section id="articles-container">
<?php if (!$rows): ?><p class="empty" id="empty-notice">Loading latest stories from news wire...</p><?php endif; ?>
<?php foreach ($rows as $i => $a) { article_card($a, $i === 0); if ($i === 4) ad_slot('inarticle'); } ?>
</section><?php require __DIR__ . '/includes/sidebar.php'; ?></div>
<?php require __DIR__ . '/includes/footer.php'; ?>
