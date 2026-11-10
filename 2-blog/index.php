<?php require_once __DIR__ . '/includes/bootstrap.php'; require_once __DIR__ . '/includes/card.php'; maybe_sync();
$rows = db()->query("SELECT * FROM articles WHERE status='published' ORDER BY published_at DESC LIMIT 25")->fetchAll();
$pageTitle = SITE_NAME . ' — ' . SITE_TAGLINE; require __DIR__ . '/includes/header.php'; ?>
<?php ad_slot('top'); ?>
<div class="layout"><section>
<?php if (!$rows): ?><p class="empty">No articles yet. The first stories will appear here once published.</p><?php endif; ?>
<?php foreach ($rows as $i => $a) { article_card($a, $i === 0); if ($i === 4) ad_slot('inarticle'); } ?>
</section><?php require __DIR__ . '/includes/sidebar.php'; ?></div>
<?php require __DIR__ . '/includes/footer.php'; ?>
