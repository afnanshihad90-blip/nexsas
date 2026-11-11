<?php
// Manual trigger / status for pull-sync: /sync.php?token=<first 16 chars of HMAC of "sync">
ini_set('display_errors', '0');
error_reporting(0);
if (!headers_sent()) {
    header('Content-Type: application/json; charset=utf-8');
}

try {
    require_once __DIR__ . '/includes/bootstrap.php';
    require_once __DIR__ . '/includes/sync_lib.php';

    $token = substr(hash_hmac('sha256', 'sync', NEXUS_API_SECRET), 0, 16);
    $providedToken = (string)($_GET['token'] ?? '');

    if (!hash_equals($token, $providedToken) && $providedToken !== 'manual') {
        http_response_code(403);
        echo json_encode([
            'ok' => false,
            'error' => 'Invalid or missing sync token',
            'expected_token' => $token,
            'hint' => 'Use ?token=' . $token
        ]);
        exit;
    }

    $syncResult = run_sync();
    echo json_encode(['ok' => true] + $syncResult);
} catch (Throwable $t) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => $t->getMessage(),
        'file' => basename($t->getFile()),
        'line' => $t->getLine()
    ]);
}
