<?php
// POST /api/publish.php  — accepts signed articles from the backend.
require_once __DIR__ . '/../includes/bootstrap.php';
require_once __DIR__ . '/../includes/sync_lib.php';
if (!headers_sent()) { header('Content-Type: application/json; charset=utf-8'); }

function fail(int $code, string $msg): void { http_response_code($code); echo json_encode(['ok' => false, 'error' => $msg]); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail(405, 'POST only');
$raw = file_get_contents('php://input');
if (strlen($raw) > 2000000) fail(413, 'Payload too large');

$h = function ($n) { $k = 'HTTP_' . strtoupper(str_replace('-', '_', $n)); return $_SERVER[$k] ?? ''; };
$ts = $h('X-Nexus-Timestamp'); $key = $h('Idempotency-Key'); $sig = $h('X-Nexus-Signature');
if (!ctype_digit($ts) || abs(time() - (int)$ts) > 300) fail(401, 'Stale or missing timestamp');
if ($key === '' || strlen($key) > 180) fail(400, 'Idempotency-Key required');
$expected = hash_hmac('sha256', $ts . '.' . $key . '.' . $raw, NEXUS_API_SECRET);
if (!hash_equals($expected, $sig)) fail(401, 'Invalid signature');

$data = json_decode($raw, true);
if (!is_array($data)) fail(400, 'Invalid JSON');

try {
  $pdo = db();
  $seen = $pdo->prepare('SELECT slug FROM idempotency_keys WHERE k=?');
  $seen->execute([$key]);
  if ($row = $seen->fetch()) { echo json_encode(['ok' => true, 'duplicate' => true, 'slug' => $row['slug']]); exit; }
  $id = upsert_article($data);
  $slug = slugify($data['slug']);
  if ($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite') {
    $pdo->prepare('INSERT OR IGNORE INTO idempotency_keys (k, slug) VALUES (?,?)')->execute([$key, $slug]);
  } else {
    $pdo->prepare('INSERT IGNORE INTO idempotency_keys (k, slug) VALUES (?,?)')->execute([$key, $slug]);
  }
  http_response_code(201);
  echo json_encode(['ok' => true, 'id' => $id, 'slug' => $slug, 'url' => SITE_URL . '/article/' . $slug]);
} catch (InvalidArgumentException $t) { fail(400, $t->getMessage()); }
catch (Throwable $t) { fail(500, 'Server error'); }
