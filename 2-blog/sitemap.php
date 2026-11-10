<?php require_once __DIR__ . '/includes/bootstrap.php'; if (!headers_sent()) { header('Content-Type: application/xml; charset=utf-8'); }
echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n";
echo '<url><loc>' . e(SITE_URL) . "/</loc></url>\n";
foreach (array_keys(categories()) as $c) echo '<url><loc>' . e(SITE_URL . "/$c/") . "</loc></url>\n";
foreach (db()->query("SELECT slug,updated_at FROM articles WHERE status='published' ORDER BY published_at DESC LIMIT 5000") as $r)
  echo '<url><loc>' . e(SITE_URL . '/article/' . $r['slug']) . '</loc><lastmod>' . date('c', strtotime($r['updated_at'])) . "</lastmod></url>\n";
echo '</urlset>';
