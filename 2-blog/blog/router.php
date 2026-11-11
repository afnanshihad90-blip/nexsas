<?php
// Local development router that matches .htaccess rewrite rules
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Serve static assets if they exist
$file = __DIR__ . $uri;
if ($uri !== '/' && file_exists($file) && !is_dir($file)) {
    // Check forbidden files matching .htaccess
    if (preg_match('/(config\.php|schema.*\.sql)$/', $file) || str_starts_with($uri, '/includes/')) {
        http_response_code(403);
        echo 'Access denied';
        exit;
    }
    return false; // let PHP built-in server serve static file
}

// 1. article/{slug}
if (preg_match('#^/article/([a-z0-9-]+)/?$#', $uri, $m)) {
    $_GET['slug'] = $m[1];
    require __DIR__ . '/article.php';
    exit;
}

// 2. page/{page}
if (preg_match('#^/page/([a-z-]+)/?$#', $uri, $m)) {
    $_GET['p'] = $m[1];
    require __DIR__ . '/page.php';
    exit;
}

// 3. category
if (preg_match('#^/(business|world|technology|science)/?$#', $uri, $m)) {
    $_GET['c'] = $m[1];
    require __DIR__ . '/category.php';
    exit;
}

// 4. sitemap.xml
if ($uri === '/sitemap.xml') {
    require __DIR__ . '/sitemap.php';
    exit;
}

// 5. robots.txt
if ($uri === '/robots.txt') {
    header('Content-Type: text/plain');
    readfile(__DIR__ . '/robots.txt');
    exit;
}

// 6. Direct script access: /search.php, /api/publish.php, /sync.php, /index.php, /
if ($uri === '/' || $uri === '/index.php') {
    require __DIR__ . '/index.php';
    exit;
}

$script = __DIR__ . $uri;
if (file_exists($script) && str_ends_with($script, '.php')) {
    require $script;
    exit;
}

http_response_code(404);
echo 'Not found';
