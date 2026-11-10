<?php require_once __DIR__ . '/includes/bootstrap.php';
$pages = [
 'about' => ['About', 'Nexus Media covers business, world affairs, AI and science. Stories are researched with AI assistance, checked against multiple cited sources, and published with source links.'],
 'editorial-policy' => ['Editorial Policy', "We use AI tools to research and draft. Every article is checked against cited sources, important claims need multiple independent sources, and we do not publish unverified financial figures or breaking claims.\n\nImages come from licensed libraries (Pexels, Unsplash, Wikimedia Commons) and are credited. Advertising is separate from editorial content."],
 'corrections' => ['Corrections', 'If you find an error, email the address on the Contact page with the article link. Corrections are applied promptly and the updated date changes.'],
 'privacy' => ['Privacy Policy', "We use analytics and, once approved, Google AdSense, which may use cookies to serve and measure ads. Third-party vendors, including Google, use cookies to serve ads based on prior visits. You can manage ad personalization in Google's ad settings. We do not sell personal data.\n\nReplace this text with a full policy that covers your region's consent requirements (e.g. GDPR) before launch."],
 'contact' => ['Contact', 'Add your contact email here.'],
];
$k = $_GET['p'] ?? ''; if (!isset($pages[$k])) { http_response_code(404); exit('Not found'); }
$pageTitle = $pages[$k][0] . ' — ' . SITE_NAME; require __DIR__ . '/includes/header.php'; ?>
<article class="post"><h1><?= e($pages[$k][0]) ?></h1><div class="body"><?= render_markdown($pages[$k][1]) ?></div></article>
<?php require __DIR__ . '/includes/footer.php'; ?>
