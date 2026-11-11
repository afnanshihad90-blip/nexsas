<?php
// POST /api/publish_direct.php - Browser-based direct sync (bypasses hosting firewall)
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Allow-Methods: POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once __DIR__ . '/../includes/bootstrap.php';
require_once __DIR__ . '/../includes/sync_lib.php';
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'POST only']);
    exit;
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data) || empty($data['title']) || empty($data['slug'])) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'title and slug required']);
    exit;
}

if (empty($data['content'])) {
    $data['content'] = $data['excerpt'] ?? $data['title'];
}

try {
    $id = upsert_article($data);
    echo json_encode([
        'ok' => true,
        'id' => $id,
        'slug' => $data['slug'],
        'synced' => 1
    ]);
} catch (Throwable $t) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $t->getMessage()]);
}
