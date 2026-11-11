<?php
$pageTitle = $pageTitle ?? SITE_NAME;
$metaDesc  = $metaDesc ?? SITE_TAGLINE;
$canonical = $canonical ?? SITE_URL . strtok($_SERVER['REQUEST_URI'] ?? '/', '?');
$ogImage   = $ogImage ?? '';
$jsonLd    = $jsonLd ?? '';
?><!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= e($pageTitle) ?></title>
<meta name="description" content="<?= e($metaDesc) ?>">
<link rel="canonical" href="<?= e($canonical) ?>">
<meta property="og:title" content="<?= e($pageTitle) ?>"><meta property="og:description" content="<?= e($metaDesc) ?>">
<meta property="og:type" content="<?= !empty($isArticle) ? 'article' : 'website' ?>"><meta property="og:url" content="<?= e($canonical) ?>">
<?php if ($ogImage): ?><meta property="og:image" content="<?= e($ogImage) ?>"><meta name="twitter:card" content="summary_large_image"><?php endif; ?>
<link rel="stylesheet" href="/assets/style.css">
<?php if ($jsonLd): ?><script type="application/ld+json"><?= $jsonLd ?></script><?php endif; ?>
<?php if (ADSENSE_CLIENT !== ''): ?><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=<?= e(ADSENSE_CLIENT) ?>" crossorigin="anonymous"></script><?php endif; ?>
<?php if (GA4_ID !== ''): ?><script async src="https://www.googletagmanager.com/gtag/js?id=<?= e(GA4_ID) ?>"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','<?= e(GA4_ID) ?>');</script><?php endif; ?>
</head><body>
<header class="site-header"><div class="wrap bar">
  <a class="brand" href="/"><?= e(SITE_NAME) ?></a>
  <nav><?php foreach (categories() as $slug => $label): ?><a href="/<?= e($slug) ?>/"><?= e($label) ?></a><?php endforeach; ?></nav>
  <form class="search" action="/search.php" method="get"><input name="q" placeholder="Search" aria-label="Search"></form>
</div></header>
<main class="wrap">
