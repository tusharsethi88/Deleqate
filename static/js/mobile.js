/* ═══════════════════════════════════════════════════════
   DELEQATE — Mobile JS
   Hamburger menu · Touch helpers · iOS/Android fixes
   No dependencies. Loads deferred on all pages.
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── 1. HAMBURGER MENU ─────────────────────────────── */
  function initHamburger() {
    var toggle = document.querySelector('.nav-toggle');
    var nav    = document.querySelector('.navbar-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = nav.classList.toggle('open');
      toggle.classList.toggle('open', isOpen);
      toggle.setAttribute('aria-expanded', isOpen);
      // Prevent body scroll when menu open
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
      if (!toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });

    // Close on nav link tap
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      });
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        nav.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });
  }

  /* ── 2. STATUS TIMELINE: wrap in scrollable div on mobile ── */
  function wrapTimeline() {
    if (window.innerWidth > 600) return;
    document.querySelectorAll('.status-track').forEach(function (track) {
      if (track.parentElement.classList.contains('status-track-wrap')) return;
      var wrapper = document.createElement('div');
      wrapper.className = 'status-track-wrap';
      wrapper.style.cssText = 'overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;';
      track.parentNode.insertBefore(wrapper, track);
      wrapper.appendChild(track);
    });
  }

  /* ── 3. ADMIN TABLE: add mobile-cards class on small screens ── */
  function mobileAdminTables() {
    if (window.innerWidth > 480) return;
    document.querySelectorAll('.table-wrap').forEach(function (wrap) {
      wrap.classList.add('mobile-cards');
      // Stamp data-label on each td from thead
      var headers = [];
      wrap.querySelectorAll('thead th').forEach(function (th) {
        headers.push(th.textContent.trim());
      });
      wrap.querySelectorAll('tbody tr').forEach(function (row) {
        row.querySelectorAll('td').forEach(function (td, i) {
          if (headers[i]) td.setAttribute('data-label', headers[i]);
        });
      });
    });
  }

  /* ── 4. HERO CARD: wrap in centered div on mobile ── */
  function mobileHeroCard() {
    if (window.innerWidth > 768) return;
    var card = document.querySelector('.hero-card');
    if (!card) return;
    var parent = card.parentElement;
    if (parent.classList.contains('hero-card-wrap')) return;
    var wrapper = document.createElement('div');
    wrapper.className = 'hero-card-wrap';
    wrapper.style.cssText = 'display:flex;justify-content:center;margin-top:2.5rem;';
    parent.parentNode.insertBefore(wrapper, parent);
    wrapper.appendChild(parent);
  }

  /* ── 5. SMOOTH SCROLL for anchor links ── */
  function smoothAnchors() {
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var target = document.querySelector(a.getAttribute('href'));
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  /* ── 6. PREVENT iOS DOUBLE-TAP ZOOM on buttons ── */
  function preventDoubleTapZoom() {
    var lastTap = 0;
    document.querySelectorAll('.btn, .sku-card, .option-card-label, .chip label').forEach(function (el) {
      el.addEventListener('touchend', function (e) {
        var now = Date.now();
        if (now - lastTap < 300) e.preventDefault();
        lastTap = now;
      }, { passive: false });
    });
  }

  /* ── 7. FIX VIEWPORT HEIGHT on mobile browsers (address bar issue) ── */
  function fixVh() {
    function setVh() {
      document.documentElement.style.setProperty('--real-vh', (window.innerHeight * 0.01) + 'px');
    }
    setVh();
    window.addEventListener('resize', setVh, { passive: true });
  }

  /* ── 8. TOUCH-FRIENDLY COMPARISON SLIDER ── */
  function touchSlider() {
    document.querySelectorAll('.slider-wrap, [id^="sliderWrap"]').forEach(function (wrap) {
      var dragging = false;
      function getPos(e) {
        return e.touches ? e.touches[0].clientX : e.clientX;
      }
      function update(clientX) {
        var rect = wrap.getBoundingClientRect();
        var pct  = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1) * 100;
        var overlay = wrap.querySelector('[id^="sliderOverlay"], .slider-overlay');
        var handle  = wrap.querySelector('[id^="sliderHandle"], .slider-handle');
        if (overlay) overlay.style.clipPath = 'inset(0 ' + (100 - pct) + '% 0 0)';
        if (handle)  handle.style.left = pct + '%';
      }
      wrap.addEventListener('touchstart', function () { dragging = true; }, { passive: true });
      wrap.addEventListener('touchmove', function (e) {
        if (!dragging) return;
        e.preventDefault();
        update(e.touches[0].clientX);
      }, { passive: false });
      wrap.addEventListener('touchend', function () { dragging = false; }, { passive: true });
    });
  }

  /* ── INIT ── */
  document.addEventListener('DOMContentLoaded', function () {
    initHamburger();
    wrapTimeline();
    mobileAdminTables();
    mobileHeroCard();
    smoothAnchors();
    preventDoubleTapZoom();
    fixVh();
    touchSlider();
  });

})();
