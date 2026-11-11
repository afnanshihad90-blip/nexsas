<?php
// POST/GET /api/publish_direct.php - Browser-based direct sync (bypasses hosting firewall)
ini_set('display_errors', '0');
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED);

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

header('Content-Type: application/json; charset=utf-8');

try {
    require_once __DIR__ . '/../includes/bootstrap.php';
    require_once __DIR__ . '/../includes/sync_lib.php';

    // Support both raw JSON (php://input), standard form POST ($_POST) and GET fallback
    $raw = file_get_contents('php://input');
    $data = [];
    if (!empty($raw)) {
        $decoded = json_decode($raw, true);
        if (is_array($decoded)) {
            $data = $decoded;
        }
    }
    if (empty($data)) {
        $data = !empty($_POST) ? $_POST : $_GET;
    }

    if (empty($data['title']) && empty($data['headline'])) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'title or headline required']);
        exit;
    }

    if (empty($data['title']) && !empty($data['headline'])) {
        $data['title'] = $data['headline'];
    }

    if (empty($data['slug'])) {
        $data['slug'] = slugify($data['title']);
    }

    if (empty($data['content'])) {
        $data['content'] = $data['body_markdown'] ?? $data['excerpt'] ?? $data['summary'] ?? $data['title'];
    }

    if (empty($data['category'])) {
        $data['category'] = 'technology';
    }

    $data['status'] = 'published';

    $id = upsert_article($data);

    echo json_encode([
        'ok' => true,
        'id' => $id,
        'slug' => $data['slug'],
        'title' => $data['title'],
        'category' => $data['category'],
        'synced' => 1
    ]);
} catch (Throwable $t) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => $t->getMessage(),
        'file' => basename($t->getFile()),
        'line' => $t->getLine()
    ]);
}
