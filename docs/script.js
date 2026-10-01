(function () {
  'use strict';

  var ASSET = 'Setup_Windows_x64.exe';
  var API = 'https://api.github.com/repos/RandomCatUser/SweetVibe/releases/latest';
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
      .catch(function () {});
  }

  var scrollHandlers = [];
  var scrollQueued = false;

  function onScroll(fn) { scrollHandlers.push(fn); }

  window.addEventListener('scroll', function () {
    if (scrollQueued) return;
    scrollQueued = true;
    window.requestAnimationFrame(function () {
      for (var i = 0; i < scrollHandlers.length; i++) scrollHandlers[i](110);
      scrollQueued = false;
    });
  }, { passive: true });

  function initDocs() {
    var nav = document.getElementById('side-nav');
    var toc = document.getElementById('page-toc');
    var inner = document.querySelector('.doc-inner');
    if (!inner) return;

    if (toc) {
      var heads = inner.querySelectorAll('h2, h3');
      var tocItems = [];
      var group = null;

      for (var i = 0; i < heads.length; i++) {
        var h = heads[i];
        if (h.tagName === 'H2' || !group) {
          group = document.createElement('div');
          group.className = 'toc-group';
          toc.appendChild(group);
        }
        var host = h.parentNode && h.parentNode.id ? h.parentNode : h;
        if (!host.id) host.id = 'sec-' + (i + 1);
        var a = document.createElement('a');
        a.href = '#' + host.id;
        a.textContent = h.textContent;
        if (h.tagName === 'H3') a.className = 'sub';
        group.appendChild(a);
        tocItems.push({ link: a, target: host });
      }

      if (tocItems.length) {
        tocItems[0].link.setAttribute('aria-current', 'true');
        onScroll(function (line) {
          var current = tocItems[0].target.id;
          tocItems.forEach(function (it) {
            if (it.target.getBoundingClientRect().top <= line) current = it.target.id;
          });
          tocItems.forEach(function (it) {
            if (it.target.id === current) it.link.setAttribute('aria-current', 'true');
            else it.link.removeAttribute('aria-current');
          });
        });
      }
    }

    if (nav) {
      var items = Array.prototype.slice.call(nav.querySelectorAll('a'))
        .map(function (link) {
          return {
            link: link,
            target: document.getElementById((link.getAttribute('href') || '').slice(1))
          };
        })
        .filter(function (x) { return x.target; });

      if (items.length) {
        items[0].link.setAttribute('aria-current', 'true');
        onScroll(function (line) {
          var current = items[0].target.id;
          items.forEach(function (it) {
            if (it.target.getBoundingClientRect().top <= line) current = it.target.id;
          });
          if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 4) {
            current = items[items.length - 1].target.id;
          }
          items.forEach(function (it) {
            if (it.target.id === current) it.link.setAttribute('aria-current', 'true');
            else it.link.removeAttribute('aria-current');
          });
        });
      }
    }
  }

  function initNav() {
    var btn = document.getElementById('nav-toggle');
    var nav = document.getElementById('side-nav');
    var scrim = document.getElementById('nav-scrim');
    if (!btn || !nav) return;

    function set(open) {
      nav.classList.toggle('open', open);
      document.body.classList.toggle('nav-open', open);
      if (scrim) {
        scrim.classList.toggle('show', open);
        if (open) scrim.removeAttribute('hidden');
        else scrim.setAttribute('hidden', '');
      }
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? 'Close documentation menu' : 'Open documentation menu');
    }

    btn.addEventListener('click', function () {
      set(!nav.classList.contains('open'));
    });

    if (scrim) scrim.addEventListener('click', function () { set(false); });

    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) set(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') set(false);
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth > 860) set(false);
    });
  }

  function init() {
    initDownload();
    initNav();
    initDocs();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
