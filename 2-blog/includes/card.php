<?php if (!function_exists('article_card')) {
function article_card(array $a, bool $big = false): void { $cats = categories(); ?>
<article class="card<?= $big ? ' big' : '' ?>">
  <?php if ($a['image_url']): ?><a href="/article/<?= e($a['slug']) ?>"><img loading="lazy" src="<?= e($a['image_url']) ?>" alt="<?= e($a['image_alt'] ?: $a['title']) ?>"></a><?php endif; ?>
  <div class="card-body">
    <a class="tag" href="/<?= e($a['category']) ?>/"><?= e($cats[$a['category']] ?? $a['category']) ?></a>
    <h2><a href="/article/<?= e($a['slug']) ?>"><?= e($a['title']) ?></a></h2>
    <p><?= e($a['excerpt']) ?></p>
    <time class="small"><?= e(ago($a['published_at'])) ?></time>
  </div>
</article><?php } } ?>
