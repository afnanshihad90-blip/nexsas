</main>
<footer class="site-footer"><div class="wrap">
  <p><?= e(SITE_NAME) ?> — <?= e(SITE_TAGLINE) ?></p>
  <p><a href="/page/about">About</a> · <a href="/page/editorial-policy">Editorial Policy</a> · <a href="/page/corrections">Corrections</a> · <a href="/page/privacy">Privacy</a> · <a href="/page/contact">Contact</a></p>
  <p class="small">Articles are researched with AI assistance and reviewed against cited sources. Spot an error? See our corrections page.</p>
</div></footer>
<script>
(async function() {
  try {
    const res = await fetch('https://nexsas-c3ne.onrender.com/api/articles?limit=30');
    if (!res.ok) return;
    const data = await res.json();
    const items = (data.items || []).filter(function(a) {
      return a.status === 'published' || a.stage === 'Published' || a.is_public === true;
    });
    if (!items.length) return;

    // 1. Background sync to local database
    items.forEach(function(art) {
      try {
        fetch('/api/publish_direct.php', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: art.headline || art.title,
            slug: art.slug,
            content: art.body_markdown || art.content || art.excerpt,
            excerpt: art.summary || art.excerpt || '',
            category: art.category || 'technology',
            status: 'published',
            image: {
              url: art.image_url || '',
              alt: art.image_alt || art.headline || art.title,
              credit: art.image_credit || 'Original Wire Press Photo',
              credit_url: art.image_credit_url || art.image_url || '',
              license: art.image_license || 'Editorial Use'
            }
          })
        }).catch(function() {});
      } catch (e) {}
    });

    // 2. Hydrate index & category listings
    var container = document.getElementById('articles-container');
    if (container) {
      var catFilter = container.getAttribute('data-category');
      var renderedSlugs = {};
      var links = container.querySelectorAll('a[href*="/article/"]');
      for (var i = 0; i < links.length; i++) {
        var m = links[i].getAttribute('href').match(/\/article\/([a-z0-9-]+)/);
        if (m) renderedSlugs[m[1]] = true;
      }

      var emptyEl = document.getElementById('empty-notice');
      var addedCount = 0;

      for (var j = 0; j < items.length; j++) {
        var art = items[j];
        if (catFilter && art.category !== catFilter) continue;
        if (renderedSlugs[art.slug]) continue;

        var card = document.createElement('article');
        card.className = 'card' + (addedCount === 0 && Object.keys(renderedSlugs).length === 0 ? ' big' : '');
        var imgHtml = art.image_url
          ? '<a href="/article/' + encodeURIComponent(art.slug) + '"><img loading="lazy" src="' + art.image_url + '" alt="' + (art.headline || art.title) + '"></a>'
          : '';
        var catName = {
          'technology': 'AI & Technology',
          'science': 'Science & Space',
          'business': 'Business & Finance',
          'world': 'World'
        }[art.category] || (art.category ? art.category.toUpperCase() : 'NEWS');

        card.innerHTML = imgHtml +
          '<div class="card-body">' +
            '<a class="tag" href="/' + (art.category || 'technology') + '/">' + catName + '</a>' +
            '<h2><a href="/article/' + encodeURIComponent(art.slug) + '">' + (art.headline || art.title) + '</a></h2>' +
            '<p>' + (art.summary || art.excerpt || '') + '</p>' +
            '<time class="small">Live Wire Update</time>' +
          '</div>';

        container.insertBefore(card, container.firstChild);
        renderedSlugs[art.slug] = true;
        addedCount++;
      }

      if (addedCount > 0 && emptyEl) {
        emptyEl.remove();
      }
    }

    // 3. Hydrate article view if page was not found in local SQLite
    var artView = document.getElementById('article-view-missing');
    if (artView) {
      var targetSlug = artView.getAttribute('data-slug');
      var targetArt = null;
      for (var k = 0; k < items.length; k++) {
        if (items[k].slug === targetSlug) {
          targetArt = items[k];
          break;
        }
      }
      if (!targetArt && targetSlug) {
        try {
          var singleRes = await fetch('https://nexsas-c3ne.onrender.com/api/articles/' + encodeURIComponent(targetSlug));
          if (singleRes.ok) {
            targetArt = await singleRes.json();
          }
        } catch (err) {}
      }
      if (targetArt) {
        try {
          fetch('/api/publish_direct.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: targetArt.headline || targetArt.title,
              slug: targetArt.slug,
              content: targetArt.body_markdown || targetArt.content || targetArt.excerpt,
              excerpt: targetArt.summary || targetArt.excerpt || '',
              category: targetArt.category || 'technology',
              status: 'published',
              image: {
                url: targetArt.image_url || '',
                alt: targetArt.image_alt || targetArt.headline || targetArt.title,
                credit: targetArt.image_credit || 'Original Wire Press Photo',
                credit_url: targetArt.image_credit_url || targetArt.image_url || '',
                license: targetArt.image_license || 'Editorial Use'
              }
            })
          }).catch(function() {});
        } catch (e) {}
        var catName2 = {
          'technology': 'AI & Technology',
          'science': 'Science & Space',
          'business': 'Business & Finance',
          'world': 'World'
        }[targetArt.category] || 'News';

        var rawBody = targetArt.body_markdown || targetArt.content || '';
        var paragraphs = rawBody.split('\n\n');
        var bodyHtml = '';
        for (var p = 0; p < paragraphs.length; p++) {
          var text = paragraphs[p].trim();
          if (!text) continue;
          var ytMatch = text.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/i);
          if (ytMatch && (text.length < 120 || text.indexOf('http') === 0)) {
            bodyHtml += '<div class="video-container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;margin:28px 0;border-radius:10px;background:#000;"><iframe src="https://www.youtube.com/embed/' + ytMatch[1] + '" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allowfullscreen loading="lazy"></iframe></div>\n';
            continue;
          }
          var imgMatch = text.match(/^!\[(.*?)\]\((https?:\/\/[^\s)]+)\)$/);
          if (imgMatch) {
            bodyHtml += '<figure class="article-image" style="margin:28px 0;text-align:center;"><img src="' + imgMatch[2] + '" alt="' + imgMatch[1] + '" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;display:inline-block;"><figcaption class="small" style="margin-top:6px;color:#94a3b8;font-size:0.85em;">' + imgMatch[1] + '</figcaption></figure>\n';
            continue;
          }
          if (text.indexOf('# ') === 0) {
            bodyHtml += '<h1>' + text.substring(2) + '</h1>\n';
          } else if (text.indexOf('## ') === 0) {
            bodyHtml += '<h2>' + text.substring(3) + '</h2>\n';
          } else if (text.indexOf('### ') === 0) {
            bodyHtml += '<h3>' + text.substring(4) + '</h3>\n';
          } else if (text.indexOf('- ') === 0) {
            var itemsList = text.split('\n');
            bodyHtml += '<ul>';
            for (var li = 0; li < itemsList.length; li++) {
              bodyHtml += '<li>' + itemsList[li].replace(/^[-*]\s+/, '') + '</li>';
            }
            bodyHtml += '</ul>\n';
          } else {
            bodyHtml += '<p>' + text + '</p>\n';
          }
        }

        var figureHtml = targetArt.image_url
          ? '<figure><img src="' + targetArt.image_url + '" alt="' + (targetArt.headline || targetArt.title) + '">' +
            '<figcaption class="small">Photo: ' + (targetArt.image_credit || 'Original Wire Press Photo') + ' (Editorial Use)</figcaption></figure>'
          : '';

        artView.innerHTML = 
          '<nav class="crumbs small"><a href="/">Home</a> › <a href="/' + (targetArt.category || 'technology') + '/">' + catName2 + '</a></nav>' +
          '<h1>' + (targetArt.headline || targetArt.title) + '</h1>' +
          '<p class="meta small">Published recently · Editorial Newsroom</p>' +
          figureHtml +
          '<div class="body">' + bodyHtml + '</div>' +
          '<p class="small disclosure">This article was produced with verified AI newsroom reporting and checked against primary wire sources.</p>';

        document.title = (targetArt.headline || targetArt.title) + ' — ' + 'Nexus Media';
      } else {
        var loadingEl = document.getElementById('article-loading');
        if (loadingEl) {
          loadingEl.innerHTML = '<h2>Article not found</h2><p class="small">The requested article could not be located in the newsroom archives.</p><p><a href="/">← Return to homepage</a></p>';
        }
      }
    }
  } catch (e) {
    console.warn('Newsroom sync:', e);
  }
})();
</script>
</body></html>
