/* 三角带行业资讯 — 前端脚本（原生 JS，无依赖） */
(function () {
  'use strict';

  /* 页脚年份 */
  var y = document.getElementById('year');
  if (y) { y.textContent = String(new Date().getFullYear()); }

  /* 移动端导航：点击链接后自动收起 */
  var toggle = document.getElementById('nav-toggle');
  if (toggle) {
    document.querySelectorAll('.nav a').forEach(function (a) {
      a.addEventListener('click', function () { toggle.checked = false; });
    });
  }

  /* 文章目录高亮：滚动时定位当前章节 */
  var toc = document.querySelector('.side-box .toc');
  if (toc) {
    var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    var targets = links.map(function (a) {
      var id = decodeURIComponent(a.getAttribute('href').slice(1));
      return { link: a, el: document.getElementById(id) };
    }).filter(function (t) { return t.el; });

    if (targets.length) {
      var ticking = false;
      var sync = function () {
        ticking = false;
        var offset = 92;
        var current = targets[0];
        for (var i = 0; i < targets.length; i++) {
          if (targets[i].el.getBoundingClientRect().top - offset <= 0) { current = targets[i]; }
        }
        targets.forEach(function (t) { t.link.classList.remove('is-current'); });
        if (current) { current.link.classList.add('is-current'); }
      };
      window.addEventListener('scroll', function () {
        if (!ticking) { ticking = true; window.requestAnimationFrame(sync); }
      }, { passive: true });
      sync();
    }
  }

  /* 平滑滚动（考虑吸顶头部高度） */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = a.getAttribute('href');
      if (!href || href === '#') { return; }
      var id = decodeURIComponent(href.slice(1));
      var el = document.getElementById(id);
      if (!el) { return; }
      e.preventDefault();
      var top = el.getBoundingClientRect().top + window.pageYOffset - 78;
      window.scrollTo({ top: top, behavior: 'smooth' });
      history.replaceState(null, '', '#' + id);
    });
  });

  /* 站内搜索 */
  var input = document.getElementById('q');
  var box = document.getElementById('search-results');
  if (input && box) {
    var countEl = document.getElementById('search-count');
    var indexUrl = '/search-index.json';
    var data = null;
    var loading = false;

    var escapeHtml = function (s) {
      return String(s).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    };

    /* 高亮：对纯文本做安全转义后再插入 mark */
    var highlight = function (text, terms) {
      var safe = escapeHtml(text);
      if (!terms.length) { return safe; }
      var pattern = terms
        .filter(function (t) { return t.length > 0; })
        .map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); })
        .join('|');
      if (!pattern) { return safe; }
      try {
        return safe.replace(new RegExp('(' + pattern + ')', 'gi'), '<mark>$1</mark>');
      } catch (err) {
        return safe;
      }
    };

    /* 命中位置摘要：截取含关键词的一段 */
    var snippet = function (text, terms) {
      if (!text) { return ''; }
      if (!terms.length) { return text.slice(0, 130); }
      var lower = text.toLowerCase();
      var pos = -1;
      for (var i = 0; i < terms.length; i++) {
        var p = lower.indexOf(terms[i].toLowerCase());
        if (p >= 0 && (pos < 0 || p < pos)) { pos = p; }
      }
      if (pos < 0) { return text.slice(0, 130); }
      var start = Math.max(0, pos - 42);
      var end = Math.min(text.length, start + 150);
      return (start > 0 ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '');
    };

    var render = function (query) {
      var q = String(query || '').trim();
      if (!q) {
        box.innerHTML = '<p class="sr-empty">输入关键词开始检索。</p>';
        if (countEl) { countEl.textContent = ''; }
        return;
      }
      if (!data) { return; }

      var terms = q.split(/\s+/).filter(Boolean);
      var results = [];

      data.forEach(function (item) {
        var title = (item.title || '').toLowerCase();
        var kws = (item.keywords || '').toLowerCase();
        var cat = (item.category || '').toLowerCase();
        var desc = (item.desc || '').toLowerCase();
        var body = (item.body || '').toLowerCase();

        var score = 0;
        var allHit = true;
        terms.forEach(function (t0) {
          var t = t0.toLowerCase();
          var hit = false;
          if (title.indexOf(t) >= 0) { score += 100; hit = true; }
          if (kws.indexOf(t) >= 0) { score += 45; hit = true; }
          if (cat.indexOf(t) >= 0) { score += 25; hit = true; }
          if (desc.indexOf(t) >= 0) { score += 20; hit = true; }
          if (body.indexOf(t) >= 0) { score += 8; hit = true; }
          if (!hit) { allHit = false; }
        });
        if (allHit && score > 0) { results.push({ item: item, score: score }); }
      });

      results.sort(function (a, b) {
        if (b.score !== a.score) { return b.score - a.score; }
        return String(b.item.date || '').localeCompare(String(a.item.date || ''));
      });

      if (countEl) {
        countEl.textContent = results.length
          ? '找到 ' + results.length + ' 条结果'
          : '未找到匹配内容';
      }

      if (!results.length) {
        box.innerHTML = '<p class="sr-empty">没有匹配的内容。可尝试更换关键词，例如「选型」「SPB」「张紧」「断裂」。</p>';
        return;
      }

      box.innerHTML = results.map(function (r) {
        var it = r.item;
        return '<a class="sr-item" href="' + it.url + '">'
          + '<h3>' + highlight(it.title, terms) + '</h3>'
          + '<div class="sr-meta">' + escapeHtml(it.category_name || '') + ' · ' + escapeHtml(it.date || '') + '</div>'
          + '<p>' + highlight(snippet(it.desc || it.body || '', terms), terms) + '</p>'
          + '</a>';
      }).join('');
    };

    var load = function (cb) {
      if (data || loading) { if (data && cb) { cb(); } return; }
      loading = true;
      fetch(indexUrl, { cache: 'force-cache' })
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (d) { data = Array.isArray(d) ? d : []; loading = false; if (cb) { cb(); } })
        .catch(function () {
          loading = false;
          box.innerHTML = '<p class="sr-empty">索引加载失败，请刷新页面重试。</p>';
        });
    };

    var initial = new URLSearchParams(window.location.search).get('q') || '';
    input.value = initial;
    if (initial) {
      load(function () { render(initial); });
    } else {
      box.innerHTML = '<p class="sr-empty">输入关键词开始检索。</p>';
    }

    var timer = null;
    input.addEventListener('input', function () {
      var v = input.value;
      clearTimeout(timer);
      timer = setTimeout(function () { load(function () { render(v); }); }, 180);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        var v = input.value;
        load(function () { render(v); });
        history.replaceState(null, '', v ? ('?q=' + encodeURIComponent(v)) : window.location.pathname);
      }
    });
    var form = document.getElementById('search-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var v = input.value;
        load(function () { render(v); });
        history.replaceState(null, '', v ? ('?q=' + encodeURIComponent(v)) : window.location.pathname);
      });
    }
  }
})();
