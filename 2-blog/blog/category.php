<?php require_once __DIR__ . '/includes/bootstrap.php'; require_once __DIR__ . '/includes/card.php'; maybe_sync();
$cats = categories(); $c = strtolower(trim((string)($_GET['c'] ?? '')));
if (!isset($cats[$c])) { http_response_code(404); exit('Category not found'); }
$page = max(1, (int)($_GET['page'] ?? 1)); $per = 12;
$rows = [];
try {
  $st = db()->prepare("SELECT * FROM articles WHERE status='published' AND category=? ORDER BY published_at DESC LIMIT $per OFFSET " . (($page - 1) * $per));
  $st->execute([$c]);
  $rows = $st->fetchAll();
} catch (Throwable $t) {}
$pageTitle = $cats[$c] . ' — ' . SITE_NAME; $metaDesc = 'Latest ' . $cats[$c] . ' news and analysis.';
require __DIR__ . '/includes/header.php'; ?>
<h1><?= e($cats[$c]) ?></h1><?php ad_slot('top'); ?>
<div class="layout"><section id="articles-container" data-category="<?= e($c) ?>">
<?php if (!$rows): ?><p class="empty" id="empty-notice">Checking latest <?= e($cats[$c]) ?> stories from news wire...</p><?php endif; ?>
<?php foreach ($rows as $a) article_card($a); ?>
<p class="pager"><?php if ($page > 1): ?><a href="?page=<?= $page - 1 ?>">← Newer</a><?php endif; ?> <?php if (count($rows) === $per): ?><a href="?page=<?= $page + 1 ?>">Older →</a><?php endif; ?></p>
</section><?php require __DIR__ . '/includes/sidebar.php'; ?></div>
<?php require __DIR__ . '/includes/footer.php'; ?>
