<?php
if (!function_exists('upsert_article')) {
function upsert_article(array $a): int {
  $pdo = db();
  $slug = slugify($a['slug'] ?? '');
  $title = trim((string)($a['title'] ?? ''));
  $content = (string)($a['content'] ?? '');
  if ($slug === '' || $title === '' || $content === '') throw new InvalidArgumentException('title, slug, content required');
  $cats = categories();
  $cat = isset($cats[$a['category'] ?? '']) ? $a['category'] : 'technology';
  $status = (($a['status'] ?? 'draft') === 'published') ? 'published' : 'draft';
  $img = is_array($a['image'] ?? null) ? $a['image'] : [];
  $imgUrl = safe_url($img['url'] ?? $img['source_url'] ?? $a['image_url'] ?? '');
  if (!$imgUrl) {
    $fallbacks = [
      'science' => 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80',
      'technology' => 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&auto=format&fit=crop&q=80',
      'business' => 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&auto=format&fit=crop&q=80',
      'world' => 'https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1200&auto=format&fit=crop&q=80',
    ];
    $imgUrl = $fallbacks[$cat] ?? $fallbacks['technology'];
  }
  $imgAlt = $img['alt'] ?? $img['alt_text'] ?? $a['image_alt'] ?? $title;
  $imgCredit = $img['credit'] ?? $img['photographer'] ?? $a['image_credit'] ?? 'Editorial Archive';
  $imgCreditUrl = safe_url($img['credit_url'] ?? $img['source_url'] ?? $a['image_credit_url'] ?? $imgUrl);
  $imgLicense = $img['license'] ?? $a['image_license'] ?? 'CC BY-SA 4.0';
  $pub = $status === 'published' ? date('Y-m-d H:i:s', isset($a['published_at']) && strtotime($a['published_at']) ? strtotime($a['published_at']) : time()) : null;
  $isSqlite = ($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
  if ($isSqlite) {
    $st = $pdo->prepare('INSERT INTO articles (slug,title,excerpt,content,category,status,meta_description,image_url,image_alt,image_credit,image_credit_url,image_license,sources_json,published_at)
      VALUES (:slug,:title,:excerpt,:content,:cat,:status,:meta,:iu,:ia,:ic,:icu,:il,:src,:pub)
      ON CONFLICT(slug) DO UPDATE SET title=excluded.title,excerpt=excluded.excerpt,content=excluded.content,category=excluded.category,
        status=excluded.status,meta_description=excluded.meta_description,
        image_url=COALESCE(excluded.image_url,articles.image_url),image_alt=COALESCE(excluded.image_alt,articles.image_alt),
        image_credit=COALESCE(excluded.image_credit,articles.image_credit),image_credit_url=COALESCE(excluded.image_credit_url,articles.image_credit_url),
        image_license=COALESCE(excluded.image_license,articles.image_license),sources_json=excluded.sources_json,
        published_at=COALESCE(articles.published_at,excluded.published_at)');
  } else {
    $st = $pdo->prepare('INSERT INTO articles (slug,title,excerpt,content,category,status,meta_description,image_url,image_alt,image_credit,image_credit_url,image_license,sources_json,published_at)
      VALUES (:slug,:title,:excerpt,:content,:cat,:status,:meta,:iu,:ia,:ic,:icu,:il,:src,:pub)
      ON DUPLICATE KEY UPDATE title=VALUES(title),excerpt=VALUES(excerpt),content=VALUES(content),category=VALUES(category),
        status=VALUES(status),meta_description=VALUES(meta_description),
        image_url=COALESCE(VALUES(image_url),image_url),image_alt=COALESCE(VALUES(image_alt),image_alt),
        image_credit=COALESCE(VALUES(image_credit),image_credit),image_credit_url=COALESCE(VALUES(image_credit_url),image_credit_url),
        image_license=COALESCE(VALUES(image_license),image_license),sources_json=VALUES(sources_json),
        published_at=COALESCE(published_at,VALUES(published_at))');
  }
  $st->execute([
    ':slug' => $slug, ':title' => mb_substr($title, 0, 300), ':excerpt' => mb_substr((string)($a['excerpt'] ?? ''), 0, 600),
    ':content' => $content, ':cat' => $cat, ':status' => $status, ':meta' => mb_substr((string)($a['meta_description'] ?? ''), 0, 300),
    ':iu' => $imgUrl ?: null, ':ia' => $imgAlt, ':ic' => $imgCredit,
    ':icu' => $imgCreditUrl ?: null, ':il' => $imgLicense,
    ':src' => json_encode(array_values(array_filter($a['sources'] ?? [], fn($s) => is_array($s) && safe_url($s['url'] ?? '')))),
    ':pub' => $pub,
  ]);
  return (int)$pdo->query("SELECT id FROM articles WHERE slug=" . $pdo->quote($slug))->fetchColumn();
}
}

if (!function_exists('run_sync')) {
function run_sync(): array {
  $ts = (string)time();
  $sig = hash_hmac('sha256', $ts . '..feed', NEXUS_API_SECRET);
  $headers = [
    "X-Nexus-Timestamp: $ts",
    "X-Nexus-Signature: $sig",
    "User-Agent: NexusBlogSync/1.0",
    "Accept: application/json"
  ];

  $raw = false;
  if (function_exists('curl_init')) {
    $ch = curl_init(NEXUS_FEED_URL);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $raw = curl_exec($ch);
    curl_close($ch);
  }
  if ($raw === false || $raw === '') {
    $ctx = stream_context_create(['http' => [
      'method' => 'GET',
      'timeout' => 12,
      'ignore_errors' => true,
      'header' => implode("\r\n", $headers) . "\r\n"
    ]]);
    $raw = @file_get_contents(NEXUS_FEED_URL, false, $ctx);
  }

  $result = ['synced' => 0, 'error' => null];
  if ($raw === false || $raw === '') {
    $result['error'] = 'feed unreachable from host';
  } else {
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['items'])) {
      $result['error'] = 'bad feed response: ' . substr((string)$raw, 0, 150);
    } else {
      foreach ($data['items'] as $item) {
        try {
          upsert_article($item);
          $result['synced']++;
        } catch (Throwable $t) {
          $result['error'] = $t->getMessage();
        }
      }
    }
  }
  try {
    db()->prepare('UPDATE sync_state SET last_status=? WHERE id=1')->execute([$result['error'] ?? ('ok:' . $result['synced'])]);
  } catch (Throwable $t) {}
  return $result;
}
}
