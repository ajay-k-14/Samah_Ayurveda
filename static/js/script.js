/* =========================================================
   Samah Ayurveda – front-end behaviour (vanilla JS)
   Modules: Header · Menu · Reveal · Gallery · Services
            · Forms · ServiceLinks · MapModule · Footer
   ========================================================= */
(() => {
  'use strict';

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /* ---------- Sticky header: transparent -> solid ivory ---------- */
  const Header = {
    init() {
      const header = $('#siteHeader');
      if (!header) return;
      const update = () => header.classList.toggle('is-scrolled', window.scrollY > 24);
      update();
      window.addEventListener('scroll', update, { passive: true });

      // Highlight the nav link of the section currently in view
      const links = $$('.primary-nav li a');
      const map = new Map(links.map((a) => [a.getAttribute('href'), a]));
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          const link = map.get('#' + e.target.id);
          if (link && e.isIntersecting) {
            links.forEach((l) => l.classList.remove('is-current'));
            link.classList.add('is-current');
          }
        });
      }, { rootMargin: '-45% 0px -50% 0px' });
      $$('main section[id]').forEach((s) => io.observe(s));
    },
  };

  /* ---------- Mobile hamburger menu ---------- */
  const Menu = {
    init() {
      const btn = $('#menuToggle');
      const nav = $('#primaryNav');
      if (!btn || !nav) return;
      const set = (open) => {
        nav.classList.toggle('open', open);
        btn.setAttribute('aria-expanded', String(open));
        btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
        document.body.style.overflow = open ? 'hidden' : '';
      };
      btn.addEventListener('click', () => set(!nav.classList.contains('open')));
      nav.addEventListener('click', (e) => { if (e.target.closest('a')) set(false); });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') set(false); });
      window.matchMedia('(min-width: 1021px)').addEventListener('change', () => set(false));
    },
  };

  /* ---------- Fade-up / image reveal on scroll ---------- */
  const Reveal = {
    init() {
      const targets = $$('.reveal, .img-reveal');
      if (!('IntersectionObserver' in window)) { targets.forEach((t) => t.classList.add('in')); return; }
      const io = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); }
        });
      }, { threshold: 0.15 });
      targets.forEach((t) => io.observe(t));
    },
  };

  /* ---------- Gallery category filter ---------- */
  const Gallery = {
    init() {
      const buttons = $$('.filter');
      const items = $$('.g-item');
      buttons.forEach((btn) => btn.addEventListener('click', () => {
        const f = btn.dataset.filter;
        buttons.forEach((b) => b.classList.toggle('is-active', b === btn));
        items.forEach((it) => {
          const show = f === 'all' || it.dataset.cat.split(' ').includes(f);
          it.classList.toggle('is-hidden', !show);
        });
      }));
    },
  };

  /* ---------- Keep the service <select> in sync with the API ---------- */
  const Services = {
    async init() {
      const select = $('#a-service');
      if (!select) return;
      try {
        const res = await fetch('/api/services');
        if (!res.ok) return;
        const { services } = await res.json();
        const current = select.value;
        select.innerHTML = '<option value="">Choose a service</option>';
        [...services.map((s) => s.name), 'General Consultation'].forEach((name) => {
          const o = document.createElement('option');
          o.textContent = name;
          select.appendChild(o);
        });
        select.value = current;
      } catch (_) { /* keep the static options */ }
    },
  };

  /* ---------- Buttons that pre-select a service ---------- */
  const ServiceLinks = {
    init() {
      $$('[data-service]').forEach((a) => a.addEventListener('click', () => {
        const select = $('#a-service');
        if (select) select.value = a.dataset.service;
      }));
    },
  };

  /* ---------- Forms: validation + POST to Flask ---------- */
  const validators = {
    name: (v) => (v.trim().length >= 2 ? '' : 'Please enter your full name.'),
    phone: (v) => (/^(?:\+91|0)?[\s-]?[6-9]\d{4}[\s-]?\d{5}$/.test(v.trim()) ? '' : 'Enter a valid 10-digit Indian mobile number.'),
    email: (v, f) => {
      if (!v.trim()) return f.required ? 'Enter your email address.' : '';
      return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.trim()) ? '' : 'Enter a valid email address.';
    },
    service: (v) => (v ? '' : 'Please choose a service.'),
    date: (v) => {
      if (!v) return 'Choose a preferred date.';
      const today = new Date(); today.setHours(0, 0, 0, 0);
      return new Date(v + 'T00:00:00') >= today ? '' : 'Choose today or a future date.';
    },
    time: (v) => (v ? '' : 'Choose a preferred time.'),
    message: (v, f) => (f.required && v.trim().length < 5 ? 'Please write a short message.' : ''),
  };

  const Forms = {
    init() {
      const dateInput = $('#a-date');
      if (dateInput) dateInput.min = new Date().toISOString().split('T')[0];
      $$('form[data-endpoint]').forEach((form) => this.bind(form));
    },

    setError(form, name, msg) {
      const field = form.elements[name]?.closest('.field');
      const slot = $(`.err[data-for="${name}"]`, form);
      if (field) field.classList.toggle('invalid', Boolean(msg));
      if (slot) slot.textContent = msg || '';
    },

    validate(form) {
      let ok = true;
      [...form.elements].forEach((el) => {
        const check = validators[el.name];
        if (!check) return;
        const msg = check(el.value, { required: el.required });
        this.setError(form, el.name, msg);
        if (msg) ok = false;
      });
      return ok;
    },

    bind(form) {
      const status = $('.form-status', form);
      const btn = $('button[type="submit"]', form);

      // Clear an error as soon as the person fixes the field
      form.addEventListener('input', (e) => {
        const check = validators[e.target.name];
        if (check) this.setError(form, e.target.name, check(e.target.value, { required: e.target.required }));
      });

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        status.className = 'form-status';
        status.textContent = '';
        if (!this.validate(form)) {
          const first = $('.invalid input, .invalid select, .invalid textarea', form);
          if (first) first.focus();
          return;
        }

        const payload = Object.fromEntries(new FormData(form).entries());
        btn.disabled = true;
        try {
          const res = await fetch(form.dataset.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json().catch(() => ({}));
          if (res.ok && data.ok) {
            form.reset();
            status.classList.add('ok');
            status.textContent = form.id === 'appointmentForm'
              ? 'Thank you! Your appointment request has been received. Our team will contact you shortly.'
              : 'Thank you! Your message has been received. We will get back to you soon.';
          } else if (data.errors) {
            Object.entries(data.errors).forEach(([k, m]) => this.setError(form, k, m));
          } else {
            throw new Error(data.error || 'Request failed');
          }
        } catch (err) {
          status.classList.add('fail');
          status.textContent = 'We could not send your request. Please call +91 63636 25258 and we will book you in.';
        } finally {
          btn.disabled = false;
        }
      });
    },
  };

  /* ---------- Google Map (themed) with keyless fallback ---------- */
  const MapModule = {
    // Muted palette so the map matches the site
    styles: [
      { elementType: 'geometry', stylers: [{ color: '#f1ead9' }] },
      { elementType: 'labels.text.fill', stylers: [{ color: '#55645a' }] },
      { elementType: 'labels.text.stroke', stylers: [{ color: '#f7f1e5' }] },
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#c9d8c0' }] },
      { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#dce3c9' }] },
      { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#fffaf0' }] },
      { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#e9dcc8' }] },
      { featureType: 'poi', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
    ],

    init() {
      const el = $('#map');
      if (!el) return;
      const cfg = window.SAMAH_CONFIG || {};
      if (cfg.mapsKey) this.loadApi(el, cfg); else this.fallback(el);
    },

    loadApi(el, cfg) {
      window.__samahMapReady = () => {
        const pos = { lat: cfg.lat, lng: cfg.lng };
        const map = new google.maps.Map(el, {
          center: pos, zoom: 15, styles: this.styles,
          mapTypeControl: false, streetViewControl: false, fullscreenControl: false,
        });
        new google.maps.Marker({ position: pos, map, title: 'Samah Ayurveda' });
      };
      const s = document.createElement('script');
      s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(cfg.mapsKey)}&callback=__samahMapReady`;
      s.async = true;
      s.onerror = () => this.fallback(el);
      document.head.appendChild(s);
    },

    fallback(el) {
      const q = encodeURIComponent(el.dataset.query || 'Lalbagh, Mangalore');
      el.innerHTML = `<iframe title="Samah Ayurveda location" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q=${q}&output=embed"></iframe>`;
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    [Header, Menu, Reveal, Gallery, Services, ServiceLinks, Forms, MapModule].forEach((m) => m.init());
  });
})();
