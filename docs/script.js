// SweetVibe docs site — shared by index.html and docs.html

(function () {
  'use strict';

  /* ── Download button ──────────────────────────────────────────────────
     One button on the page. Resolve the newest installer once so the link
     never points at a stale version, and fall back to the releases page. */
  var ASSET = 'Setup_Windows_x64.exe';
  var API = 'https://api.github.com/repos/RandomCatUser/SweetVibe/releases/latest';
  var RELEASES = 'https://github.com/RandomCatUser/SweetVibe/releases/latest';

  var toast = document.getElementById('download-toast');
  var toastTimer;

  function hideToast() {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.classList.remove('show');
  }

  function showToast() {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.classList.add('show');
    toastTimer = setTimeout(hideToast, 5000);
  }

  function initDownload() {
    var links = document.querySelectorAll('[data-download]');
    if (!links.length) return;

    var close = toast && toast.querySelector('.toast-close');
    if (close) close.addEventListener('click', hideToast);

    links.forEach(function (link) {
      link.addEventListener('click', showToast);
    });

    // Resolve the real asset URL in the background; the href already points
    // somewhere sensible, so a failed lookup is harmless.
    fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (release) {
        var asset = (release.assets || []).filter(function (a) {
          return a.name === ASSET;
        })[0];
        if (!asset || !asset.browser_download_url) return;
        links.forEach(function (link) { link.href = asset.browser_download_url; });
      })
      .catch(function () { /* keep the releases-page fallback */ });
  }

  /* ── Dancing girl ASCII ───────────────────────────────────────────────
     Frames are extracted verbatim from plugins/girl.py (see girl-frames.js).
     ~10fps matches the plugin's own default interval. */
  function initGirl() {
    var art = document.getElementById('girl-art');
    if (!art) return;

    var frames = window.SWEETVIBE_GIRL_FRAMES;
    if (!frames || !frames.length) return;

    var label = document.getElementById('girl-state');
    var i = 0;
    var timer = null;

    function draw() { art.textContent = frames[i].join('\n'); }
    function step() {
      i = (i + 1) % frames.length;
      draw();
    }
    function play() {
      if (timer) return;
      timer = setInterval(step, 100);
      if (label) label.textContent = 'click to pause';
    }
    function pause() {
      clearInterval(timer);
      timer = null;
      if (label) label.textContent = 'paused — click to resume';
    }

    draw();

    // Respect the OS setting: show one still frame and leave it there.
    var reduced = window.matchMedia &&
                  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduced) {
      if (label) label.textContent = 'motion reduced';
    } else {
      play();
      art.addEventListener('click', function () {
        if (timer) { pause(); } else { play(); }
      });
    }
  }

  /* ── Docs sidebar ─────────────────────────────────────────────────────
     Highlights the entry for whichever section is currently in view. */
  function initSidebar() {
    var nav = document.getElementById('side-nav');
    if (!nav) return;

    var links = Array.prototype.slice.call(nav.querySelectorAll('.side-link'));
    if (!links.length) return;

    // Map each link to the heading it points at.
    var items = links.map(function (link) {
      var target = document.getElementById((link.getAttribute('href') || '').slice(1));
      return { link: link, target: target };
    }).filter(function (i) { return i.target; });

    if (!items.length) return;

    function mark(id) {
      items.forEach(function (i) {
        i.link.classList.toggle('active', i.target.id === id);
      });
    }

    function onScroll() {
      // The section whose top is closest to (but not far below) the nav bar.
      var line = 96;
      var current = items[0].target.id;
      items.forEach(function (i) {
        if (i.target.getBoundingClientRect().top <= line) current = i.target.id;
      });
      // At the very bottom of the page, favour the last section.
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 4) {
        current = items[items.length - 1].target.id;
      }
      mark(current);
    }

    var ticking = false;
    function request() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        onScroll();
        ticking = false;
      });
    }

    window.addEventListener('scroll', request, { passive: true });
    window.addEventListener('resize', request);
    onScroll();
  }

  function init() {
    initDownload();
    initGirl();
    initSidebar();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
