<?php
// Manual trigger / status for pull-sync: /sync.php?token=<first 16 chars of HMAC of "sync">
require_once __DIR__ . '/includes/bootstrap.php';
require_once __DIR__ . '/includes/sync_lib.php';
if (!headers_sent()) { header('Content-Type: application/json'); }
$token = substr(hash_hmac('sha256', 'sync', NEXUS_API_SECRET), 0, 16);
if (!hash_equals($token, (string)($_GET['token'] ?? ''))) { http_response_code(403); echo '{"ok":false}'; exit; }
echo json_encode(['ok' => true] + run_sync());
