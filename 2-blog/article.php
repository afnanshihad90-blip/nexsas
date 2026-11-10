<?php require_once __DIR__ . '/includes/bootstrap.php'; require_once __DIR__ . '/includes/card.php';
$slug = slugify($_GET['slug'] ?? '');
$st = db()->prepare("SELECT * FROM articles WHERE slug=? AND status='published'"); $st->execute([$slug]); $a = $st->fetch();
if (!$a) { http_response_code(404); $pageTitle = 'Not found'; require __DIR__ . '/includes/header.php'; echo '<h1>Article not found</h1>'; require __DIR__ . '/includes/footer.php'; exit; }
db()->prepare('UPDATE articles SET views=views+1 WHERE id=?')->execute([$a['id']]);
$cats = categories(); $isArticle = true;
$pageTitle = $a['title'] . ' — ' . SITE_NAME; $metaDesc = $a['meta_description'] ?: $a['excerpt'];
$canonical = SITE_URL . '/article/' . $a['slug']; $ogImage = $a['image_url'] ?: '';
$jsonLd = json_encode(['@context' => 'https://schema.org', '@type' => 'NewsArticle', 'headline' => $a['title'],
  'datePublished' => date('c', strtotime($a['published_at'])), 'dateModified' => date('c', strtotime($a['updated_at'])),
  'image' => $a['image_url'] ? [$a['image_url']] : [], 'author' => ['@type' => 'Organization', 'name' => SITE_NAME],
  'publisher' => ['@type' => 'Organization', 'name' => SITE_NAME], 'mainEntityOfPage' => $canonical], JSON_UNESCAPED_SLASHES);
$sources = json_decode($a['sources_json'] ?: '[]', true) ?: [];
$related = db()->prepare("SELECT * FROM articles WHERE status='published' AND category=? AND id<>? ORDER BY published_at DESC LIMIT 3");
$related->execute([$a['category'], $a['id']]); $related = $related->fetchAll();
// split body so an ad can sit mid-article
$html = render_markdown($a['content']); $parts = explode("</p>\n", $html, 4);
require __DIR__ . '/includes/header.php'; ?>
<?php ad_slot('top'); ?>
<div class="layout"><article class="post">
  <nav class="crumbs small"><a href="/">Home</a> › <a href="/<?= e($a['category']) ?>/"><?= e($cats[$a['category']] ?? '') ?></a></nav>
  <h1><?= e($a['title']) ?></h1>
  <p class="meta small">Published <?= e(ago($a['published_at'])) ?> · Updated <?= e(ago($a['updated_at'])) ?> · <?= max(1, (int)round(str_word_count(strip_tags($a['content'])) / 220)) ?> min read</p>
  <?php if ($a['image_url']): ?><figure><img src="<?= e($a['image_url']) ?>" alt="<?= e($a['image_alt'] ?: $a['title']) ?>">
    <figcaption class="small">Photo: <?php if (safe_url($a['image_credit_url'])): ?><a href="<?= e($a['image_credit_url']) ?>" rel="noopener nofollow"><?= e($a['image_credit']) ?></a><?php else: echo e($a['image_credit']); endif; ?> <?= $a['image_license'] ? '(' . e($a['image_license']) . ')' : '' ?></figcaption></figure><?php endif; ?>
  <div class="body">
    <?php foreach ($parts as $i => $p) { echo $p . ($i < count($parts) - 1 ? "</p>\n" : ''); if ($i === 1) ad_slot('inarticle'); } ?>
  </div>
  <?php ad_slot('bottom'); ?>
  <?php if ($sources): ?><section class="sources"><h3>Sources</h3><ul><?php foreach ($sources as $s): ?><li><a href="<?= e($s['url']) ?>" rel="noopener nofollow" target="_blank"><?= e($s['title'] ?? $s['url']) ?></a></li><?php endforeach; ?></ul></section><?php endif; ?>
  <p class="small disclosure">This article was produced with AI assistance and checked against the sources above. See our <a href="/page/editorial-policy">editorial policy</a>; report errors via <a href="/page/corrections">corrections</a>.</p>
  <?php if ($related): ?><section><h3>Related</h3><div class="grid"><?php foreach ($related as $r) article_card($r); ?></div></section><?php endif; ?>
</article><?php require __DIR__ . '/includes/sidebar.php'; ?></div>
<?php require __DIR__ . '/includes/footer.php'; ?>
