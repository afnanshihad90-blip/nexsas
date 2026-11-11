<?php
// Local test configuration for Nexus Blog
define('DB_HOST', 'sqlite');
define('DB_NAME', __DIR__ . '/test_blog.db');
define('DB_USER', '');
define('DB_PASS', '');

define('SITE_NAME', 'Nexus Media');
$proto = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https://' : 'http://';
$host = $_SERVER['HTTP_HOST'] ?? 'nexusnews.site.je';
define('SITE_URL', $proto . $host);
define('SITE_TAGLINE', 'Business, World, AI & Science — explained.');

define('NEXUS_API_SECRET', 'test-cross-language-signing-secret-key-12345');
define('NEXUS_FEED_URL', 'https://nexsas-c3ne.onrender.com/api/public/feed');
define('SYNC_INTERVAL_SECONDS', 60);

define('ADSENSE_CLIENT', '');
define('ADSENSE_SLOT_TOP', '');
define('ADSENSE_SLOT_INARTICLE', '');
define('ADSENSE_SLOT_BOTTOM', '');
define('ADSENSE_SLOT_SIDEBAR', '');
define('GA4_ID', '');

define('CATEGORIES', json_encode([
  'business'   => 'Business & Finance',
  'world'      => 'World',
  'technology' => 'AI & Technology',
  'science'    => 'Science & Space',
]));
