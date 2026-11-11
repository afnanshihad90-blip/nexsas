<?php
try {
  require_once __DIR__ . '/includes/bootstrap.php';
  require_once __DIR__ . '/includes/card.php';
  $slug = slugify($_GET['slug'] ?? '');
  $a = false;
  if ($slug !== '') {
    try {
      $st = db()->prepare("SELECT * FROM articles WHERE slug=? AND status='published'");
      $st->execute([$slug]);
      $a = $st->fetch();
    } catch (Throwable $t) {}
  }

  $cats = categories();
  $isArticle = true;

  if ($a) {
    try {
      db()->prepare('UPDATE articles SET views=views+1 WHERE id=?')->execute([$a['id']]);
    } catch (Throwable $t) {}

    $pageTitle = ($a['title'] ?? 'News Article') . ' — ' . SITE_NAME;
    $metaDesc = $a['meta_description'] ?: ($a['excerpt'] ?: $a['title']);
    $canonical = SITE_URL . '/article/' . $a['slug'];
    $ogImage = $a['image_url'] ?: '';

    $pubTime = !empty($a['published_at']) && strtotime($a['published_at']) ? strtotime($a['published_at']) : time();
    $upTime = !empty($a['updated_at']) && strtotime($a['updated_at']) ? strtotime($a['updated_at']) : $pubTime;

    $jsonLd = json_encode([
      '@context' => 'https://schema.org',
      '@type' => 'NewsArticle',
      'headline' => $a['title'],
      'datePublished' => date('c', $pubTime),
      'dateModified' => date('c', $upTime),
      'image' => $a['image_url'] ? [$a['image_url']] : [],
      'author' => ['@type' => 'Organization', 'name' => SITE_NAME],
      'publisher' => ['@type' => 'Organization', 'name' => SITE_NAME],
      'mainEntityOfPage' => $canonical
    ], JSON_UNESCAPED_SLASHES);

    $sources = json_decode($a['sources_json'] ?: '[]', true) ?: [];
    $related = [];
    try {
      $relSt = db()->prepare("SELECT * FROM articles WHERE status='published' AND category=? AND id<>? ORDER BY published_at DESC LIMIT 3");
      $relSt->execute([$a['category'], $a['id']]);
      $related = $relSt->fetchAll();
    } catch (Throwable $t) {}

    $html = render_markdown($a['content'] ?? '');
    // If body begins with the same image as hero image, strip duplicate
    if (!empty($a['image_url'])) {
      $imgUrlEsc = preg_quote($a['image_url'], '#');
      $html = preg_replace('#^<figure[^>]*><img[^>]+src=[\'"]' . $imgUrlEsc . '[\'"][^>]*>.*?</figure>\s*#i', '', $html, 1);
    }
    $parts = explode("</p>\n", $html, 4);

    require __DIR__ . '/includes/header.php';
?>
<?php ad_slot('top'); ?>
<div class="layout"><article class="post">
  <nav class="crumbs small"><a href="/">Home</a> › <a href="/<?= e($a['category']) ?>/"><?= e($cats[$a['category']] ?? $a['category']) ?></a></nav>
  <h1><?= e($a['title']) ?></h1>
  <p class="meta small">Published <?= e(ago($a['published_at'])) ?> · Updated <?= e(ago($a['updated_at'])) ?> · <?= max(1, (int)round(str_word_count(strip_tags($a['content'])) / 220)) ?> min read</p>
  <?php if ($a['image_url']): ?><figure><img src="<?= e($a['image_url']) ?>" alt="<?= e($a['image_alt'] ?: $a['title']) ?>">
    <figcaption class="small">Photo: <?php if (safe_url($a['image_credit_url'])): ?><a href="<?= e($a['image_credit_url']) ?>" rel="noopener nofollow"><?= e($a['image_credit']) ?></a><?php else: echo e($a['image_credit'] ?: 'Wire Press'); endif; ?> <?= $a['image_license'] ? '(' . e($a['image_license']) . ')' : '' ?></figcaption></figure><?php endif; ?>
  <div class="body">
    <?php foreach ($parts as $i => $p) { echo $p . ($i < count($parts) - 1 ? "</p>\n" : ''); if ($i === 1) ad_slot('inarticle'); } ?>
  </div>
  <?php ad_slot('bottom'); ?>
  <?php if ($sources): ?><section class="sources"><h3>Sources</h3><ul><?php foreach ($sources as $s): ?><li><a href="<?= e($s['url']) ?>" rel="noopener nofollow" target="_blank"><?= e($s['title'] ?? $s['url']) ?></a></li><?php endforeach; ?></ul></section><?php endif; ?>
  <p class="small disclosure">This article was produced with AI assistance and checked against primary sources. See our <a href="/page/editorial-policy">editorial policy</a>.</p>
  <?php if ($related): ?><section><h3>Related</h3><div class="grid"><?php foreach ($related as $r) article_card($r); ?></div></section><?php endif; ?>
</article><?php require __DIR__ . '/includes/sidebar.php'; ?></div>
<?php
    require __DIR__ . '/includes/footer.php';
  } else {
    // If not found in SQLite yet, render dynamic container that loads from cloud newsroom
    $pageTitle = 'Loading Story — ' . SITE_NAME;
    require __DIR__ . '/includes/header.php';
?>
<div class="layout">
  <article class="post" id="article-view-missing" data-slug="<?= e($slug) ?>">
    <div id="article-loading" style="padding:60px 0;text-align:center;">
      <h2 style="margin-bottom:12px;">Loading article from newsroom...</h2>
      <p class="small" style="color:#64748b;">Syncing verified wire reporting, photographs, and citations...</p>
    </div>
  </article>
  <?php require __DIR__ . '/includes/sidebar.php'; ?>
</div>
<?php
    require __DIR__ . '/includes/footer.php';
  }
} catch (Throwable $e) {
  http_response_code(500);
  echo '<div style="font-family:sans-serif;padding:30px;max-width:800px;margin:0 auto;"><h1>Unable to load article</h1><p>' . htmlspecialchars($e->getMessage()) . '</p><p><a href="/">← Return to homepage</a></p></div>';
}
