<?php
if (!file_exists(__DIR__ . '/../config.php')) { http_response_code(500); exit('Missing config.php'); }
require_once __DIR__ . '/../config.php';

if (!function_exists('db')) {
function db(): PDO {
  static $pdo = null;
  if ($pdo === null) {
    if ((defined('DB_DRIVER') && DB_DRIVER === 'sqlite') || (defined('DB_HOST') && (DB_HOST === 'sqlite' || substr(DB_NAME, -3) === '.db'))) {
      $pdo = new PDO('sqlite:' . DB_NAME, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
      ]);
      try {
        $pdo->exec('PRAGMA journal_mode = DELETE;');
      } catch (Throwable $t) {}
      $pdo->exec("
        CREATE TABLE IF NOT EXISTS articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          slug TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          excerpt TEXT,
          content TEXT NOT NULL,
          category TEXT NOT NULL DEFAULT 'technology',
          status TEXT NOT NULL DEFAULT 'draft',
          meta_description TEXT,
          image_url TEXT,
          image_alt TEXT,
          image_credit TEXT,
          image_credit_url TEXT,
          image_license TEXT,
          sources_json TEXT,
          views INTEGER NOT NULL DEFAULT 0,
          published_at DATETIME NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS idempotency_keys (
          k TEXT PRIMARY KEY,
          slug TEXT NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sync_state (
          id INTEGER PRIMARY KEY,
          last_run INTEGER NOT NULL DEFAULT 0,
          last_status TEXT
        );
        INSERT OR IGNORE INTO sync_state (id, last_run) VALUES (1, 0);
      ");
    } else {
      $pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4', DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
      ]);
    }
  }
  return $pdo;
}
}

if (!function_exists('e')) {
function e($s): string { return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
}

if (!function_exists('categories')) {
function categories(): array { return json_decode(CATEGORIES, true); }
}

if (!function_exists('safe_url')) {
function safe_url($u): string { return preg_match('#^https?://#i', (string)$u) ? (string)$u : ''; }
}

if (!function_exists('slugify')) {
function slugify($s): string {
  $s = strtolower(trim(preg_replace('/[^a-zA-Z0-9]+/', '-', (string)$s), '-'));
  return substr($s, 0, 160);
}
}

if (!function_exists('ago')) {
function ago($dt): string { return $dt ? date('M j, Y', strtotime($dt)) : ''; }
}

// Minimal, safe Markdown: escapes HTML first, then supports headings, bold, italic, links, lists.
if (!function_exists('render_markdown')) {
function render_markdown(string $md): string {
  $md = str_replace(["\r\n", "\r"], "\n", e($md));
  $blocks = preg_split("/\n{2,}/", trim($md));
  $html = '';
  foreach ($blocks as $b) {
    $b = trim($b);
    if ($b === '') continue;
    if (preg_match('/^(#{1,4})\s+(.+)$/s', $b, $m)) {
      $lvl = min(4, strlen($m[1]) + 1);
      $html .= "<h$lvl>" . inline_md($m[2]) . "</h$lvl>\n";
    } elseif (preg_match('/^([-*]\s+.+)(\n[-*]\s+.+)*$/s', $b)) {
      $items = preg_split('/\n/', $b);
      $html .= '<ul>' . implode('', array_map(fn($i) => '<li>' . inline_md(preg_replace('/^[-*]\s+/', '', $i)) . '</li>', $items)) . "</ul>\n";
    } else {
      $html .= '<p>' . nl2br(inline_md($b)) . "</p>\n";
    }
  }
  return $html;
}
}

if (!function_exists('inline_md')) {
function inline_md(string $t): string {
  $t = preg_replace('/\*\*(.+?)\*\*/s', '<strong>$1</strong>', $t);
  $t = preg_replace('/(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)/s', '<em>$1</em>', $t);
  $t = preg_replace_callback('/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/', function ($m) {
    return '<a href="' . $m[2] . '" rel="noopener nofollow" target="_blank">' . $m[1] . '</a>';
  }, $t);
  return $t;
}
}

// Ad slot: prints nothing unless AdSense is configured. Never fake ads.
if (!function_exists('ad_slot')) {
function ad_slot(string $name): void {
  $map = ['top' => ADSENSE_SLOT_TOP, 'inarticle' => ADSENSE_SLOT_INARTICLE, 'bottom' => ADSENSE_SLOT_BOTTOM, 'sidebar' => ADSENSE_SLOT_SIDEBAR];
  if (ADSENSE_CLIENT === '' || empty($map[$name])) return;
  echo '<div class="ad ad-' . e($name) . '"><span class="ad-label">Advertisement</span>'
     . '<ins class="adsbygoogle" style="display:block" data-ad-client="' . e(ADSENSE_CLIENT) . '" data-ad-slot="' . e($map[$name])
     . '" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>';
}
}

// Lazy pull-sync: works even if the host blocks server-to-server POSTs.
if (!function_exists('maybe_sync')) {
function maybe_sync(): void {
  if (!defined('NEXUS_FEED_URL') || NEXUS_FEED_URL === '' || strpos(NEXUS_FEED_URL, 'YOUR-') !== false) return;
  try {
    $pdo = db();
    $last = (int)$pdo->query('SELECT last_run FROM sync_state WHERE id=1')->fetchColumn();
    if (time() - $last < SYNC_INTERVAL_SECONDS) return;
    $pdo->prepare('UPDATE sync_state SET last_run=? WHERE id=1')->execute([time()]); // claim the slot
    require_once __DIR__ . '/sync_lib.php';
    run_sync();
  } catch (Throwable $t) { /* never break page rendering */ }
}
}
