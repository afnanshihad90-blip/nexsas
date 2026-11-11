<?php
if (!function_exists('upsert_article')) {
function upsert_article(array $a): int {
  $pdo = db();
  $slug = slugify($a['slug'] ?? ($a['title'] ?? ($a['headline'] ?? '')));
  $title = trim((string)($a['title'] ?? ($a['headline'] ?? '')));
  $content = (string)($a['content'] ?? ($a['body_markdown'] ?? ($a['excerpt'] ?? $title)));
  if ($slug === '' || $title === '') throw new InvalidArgumentException('title and slug required');
  if ($content === '') $content = $title;

  $cats = categories();
  $catMap = [
    'science-space' => 'science',
    'ai-technology' => 'technology',
    'business-finance' => 'business',
    'world-trending-news' => 'world',
    'science' => 'science',
    'technology' => 'technology',
    'business' => 'business',
    'world' => 'world',
    'markets-economy' => 'business',
    'global-affairs' => 'world',
    'scientific-discovery' => 'science',
    'technology-compute' => 'technology',
  ];
  $incomingCat = strtolower(trim((string)($a['category'] ?? '')));
  $cat = $catMap[$incomingCat] ?? (isset($cats[$incomingCat]) ? $incomingCat : 'technology');

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
  $imgCredit = $img['credit'] ?? $img['photographer'] ?? $a['image_credit'] ?? 'Original Wire Press Photo';
  $imgCreditUrl = safe_url($img['credit_url'] ?? $img['source_url'] ?? $a['image_credit_url'] ?? $imgUrl);
  $imgLicense = $img['license'] ?? $a['image_license'] ?? 'Editorial Use';
  $pub = $status === 'published' ? date('Y-m-d H:i:s', !empty($a['published_at']) && strtotime($a['published_at']) ? strtotime($a['published_at']) : time()) : null;
  $meta = mb_substr((string)($a['meta_description'] ?? ($a['excerpt'] ?? $title)), 0, 300);
  $excerpt = mb_substr((string)($a['excerpt'] ?? ($a['summary'] ?? $title)), 0, 600);
  $sources = json_encode(array_values(array_filter($a['sources'] ?? [], fn($s) => is_array($s) && safe_url($s['url'] ?? ''))));

  // Check if article already exists by slug
  $existSt = $pdo->prepare("SELECT id FROM articles WHERE slug=?");
  $existSt->execute([$slug]);
  $existingId = $existSt->fetchColumn();

  if ($existingId) {
    $up = $pdo->prepare("UPDATE articles SET 
      title = :title,
      excerpt = :excerpt,
      content = :content,
      category = :cat,
      status = :status,
      meta_description = :meta,
      image_url = COALESCE(:iu, image_url),
      image_alt = COALESCE(:ia, image_alt),
      image_credit = COALESCE(:ic, image_credit),
      image_credit_url = COALESCE(:icu, image_credit_url),
      image_license = COALESCE(:il, image_license),
      sources_json = :src,
      published_at = COALESCE(published_at, :pub),
      updated_at = CURRENT_TIMESTAMP
      WHERE id = :id");
    $up->execute([
      ':title' => mb_substr($title, 0, 300),
      ':excerpt' => $excerpt,
      ':content' => $content,
      ':cat' => $cat,
      ':status' => $status,
      ':meta' => $meta,
      ':iu' => $imgUrl ?: null,
      ':ia' => $imgAlt,
      ':ic' => $imgCredit,
      ':icu' => $imgCreditUrl ?: null,
      ':il' => $imgLicense,
      ':src' => $sources,
      ':pub' => $pub,
      ':id' => $existingId
    ]);
    return (int)$existingId;
  } else {
    $ins = $pdo->prepare("INSERT INTO articles 
      (slug, title, excerpt, content, category, status, meta_description, image_url, image_alt, image_credit, image_credit_url, image_license, sources_json, published_at)
      VALUES 
      (:slug, :title, :excerpt, :content, :cat, :status, :meta, :iu, :ia, :ic, :icu, :il, :src, :pub)");
    $ins->execute([
      ':slug' => $slug,
      ':title' => mb_substr($title, 0, 300),
      ':excerpt' => $excerpt,
      ':content' => $content,
      ':cat' => $cat,
      ':status' => $status,
      ':meta' => $meta,
      ':iu' => $imgUrl ?: null,
      ':ia' => $imgAlt,
      ':ic' => $imgCredit,
      ':icu' => $imgCreditUrl ?: null,
      ':il' => $imgLicense,
      ':src' => $sources,
      ':pub' => $pub,
    ]);
    return (int)$pdo->lastInsertId();
  }
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
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $raw = @curl_exec($ch);
    @curl_close($ch);
  }
  if ($raw === false || $raw === '') {
    $ctx = stream_context_create(['http' => [
      'method' => 'GET',
      'timeout' => 6,
      'ignore_errors' => true,
      'header' => implode("\r\n", $headers) . "\r\n"
    ]]);
    $raw = @file_get_contents(NEXUS_FEED_URL, false, $ctx);
  }

  $result = ['synced' => 0, 'error' => null];
  if ($raw === false || $raw === '') {
    $result['error'] = 'feed unreachable from host (free hosting outgoing connection block)';
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
