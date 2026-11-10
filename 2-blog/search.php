<?php require_once __DIR__ . '/includes/bootstrap.php'; require_once __DIR__ . '/includes/card.php';
$q = trim((string)($_GET['q'] ?? '')); $rows = [];
if (mb_strlen($q) >= 2) {
  $like = '%' . str_replace(['%', '_'], ['\\%', '\\_'], $q) . '%';
  $st = db()->prepare("SELECT * FROM articles WHERE status='published' AND (title LIKE ? OR excerpt LIKE ?) ORDER BY published_at DESC LIMIT 30");
  $st->execute([$like, $like]); $rows = $st->fetchAll();
}
$pageTitle = 'Search — ' . SITE_NAME; require __DIR__ . '/includes/header.php'; ?>
<h1>Search</h1><p class="small"><?= $q !== '' ? count($rows) . ' result(s) for “' . e($q) . '”' : 'Type at least 2 characters.' ?></p>
<?php foreach ($rows as $a) article_card($a); ?>
<?php require __DIR__ . '/includes/footer.php'; ?>
