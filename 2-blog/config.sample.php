<?php
// Copy to config.php and fill in. NEVER commit config.php.
define('DB_HOST', 'sqlXXX.infinityfree.com');
define('DB_NAME', 'if0_XXXX_nexus');
define('DB_USER', 'if0_XXXX');
define('DB_PASS', 'CHANGE_ME');

define('SITE_NAME', 'Nexus Media');
define('SITE_URL', 'https://YOUR-BLOG-DOMAIN');          // no trailing slash
define('SITE_TAGLINE', 'Business, World, AI & Science — explained.');

// Must equal BLOG_SIGNING_SECRET on Render.
define('NEXUS_API_SECRET', 'CHANGE_ME_LONG_RANDOM');
// Pull-sync: backend feed URL (Render) used by sync.php
define('NEXUS_FEED_URL', 'https://YOUR-RENDER-SERVICE.onrender.com/api/public/feed');
define('SYNC_INTERVAL_SECONDS', 600);

// Ads (leave empty until AdSense approves you; empty = no ad code is output)
define('ADSENSE_CLIENT', '');            // e.g. ca-pub-1234567890123456
define('ADSENSE_SLOT_TOP', '');
define('ADSENSE_SLOT_INARTICLE', '');
define('ADSENSE_SLOT_BOTTOM', '');
define('ADSENSE_SLOT_SIDEBAR', '');
define('GA4_ID', '');                    // e.g. G-XXXXXXX

define('CATEGORIES', json_encode([
  'business'   => 'Business & Finance',
  'world'      => 'World',
  'technology' => 'AI & Technology',
  'science'    => 'Science & Space',
]));
