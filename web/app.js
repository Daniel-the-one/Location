/* Essivivi — site vitrine. Aucune bibliothèque, aucune dépendance de build. */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------------- *
   * 1. Fenêtre 360° : glisser (souris / tactile) + flèches du clavier.
   *    Transform direct, sans état framework, sans écouteur de scroll.
   * ---------------------------------------------------------------------- */
  (function initPanorama() {
    var windowEl = document.getElementById('hero-panorama');
    if (!windowEl) return;
    var image = windowEl.querySelector('img');
    if (!image) return;

    var offset = 0;
    var maxOffset = 0;
    var dragging = false;
    var startX = 0;
    var startOffset = 0;
    var pointerId = null;
    var pendingX = 0;
    var frame = 0;

    function measure() {
      var previousRatio = maxOffset > 0 ? -offset / maxOffset : 0.5;
      maxOffset = Math.max(0, image.offsetWidth - windowEl.clientWidth);
      offset = -Math.round(previousRatio * maxOffset);
      render();
    }

    function render() {
      image.style.transform = 'translate3d(' + offset + 'px, 0, 0)';
    }

    function clamp(value) {
      return Math.max(-maxOffset, Math.min(0, value));
    }

    function move(delta) {
      if (maxOffset === 0) return;
      offset = clamp(offset + delta);
      render();
    }

    windowEl.addEventListener('pointerdown', function (event) {
      if (event.button !== 0 && event.pointerType === 'mouse') return;
      dragging = true;
      pointerId = event.pointerId;
      startX = event.clientX;
      pendingX = event.clientX;
      startOffset = offset;
      windowEl.classList.add('is-dragging');
      if (windowEl.setPointerCapture) windowEl.setPointerCapture(pointerId);
    });

    // Un seul write DOM par frame : le pointeur peut émettre 120+ événements/s.
    function scheduleRender() {
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        offset = clamp(startOffset + (pendingX - startX));
        render();
      });
    }

    windowEl.addEventListener('pointermove', function (event) {
      if (!dragging || event.pointerId !== pointerId) return;
      pendingX = event.clientX;
      scheduleRender();
    });

    function endDrag(event) {
      if (!dragging || (event && event.pointerId !== pointerId)) return;
      dragging = false;
      if (frame) { cancelAnimationFrame(frame); frame = 0; }
      windowEl.classList.remove('is-dragging');
      if (pointerId !== null && windowEl.releasePointerCapture) {
        try { windowEl.releasePointerCapture(pointerId); } catch (e) { /* déjà relâché */ }
      }
      pointerId = null;
    }
    windowEl.addEventListener('pointerup', endDrag);
    windowEl.addEventListener('pointercancel', endDrag);

    windowEl.addEventListener('keydown', function (event) {
      var step = event.shiftKey ? 200 : 80;
      // Le calque se translate vers la gauche : regarder à droite diminue l’offset.
      if (event.key === 'ArrowRight') { move(-step); event.preventDefault(); }
      else if (event.key === 'ArrowLeft') { move(step); event.preventDefault(); }
      else if (event.key === 'Home') { offset = 0; render(); event.preventDefault(); }
      else if (event.key === 'End') { offset = -maxOffset; render(); event.preventDefault(); }
    });

    if (image.complete) measure();
    else image.addEventListener('load', measure);
    window.addEventListener('resize', measure);
  })();

  /* ---------------------------------------------------------------------- *
   * 2. Reveals — les classes sont posées ici, donc sans JS rien n’est caché.
   * ---------------------------------------------------------------------- */
  (function initReveals() {
    var targets = document.querySelectorAll(
      '.section-head, .concept-statement, .concept-detail, .step-list li, ' +
      '.tour-photo, .tour-copy, .listings-head, .listing-item, ' +
      '.owner-copy, .owner-photo, .faq-head, .faq-list, .contact-inner > div'
    );
    if (!('IntersectionObserver' in window) || reduceMotion) {
      // Mouvement réduit ou pas d’observateur : aucune cible ne doit rester masquée.
      Array.prototype.forEach.call(document.querySelectorAll('.reveal, .reveal-image'), function (el) {
        el.classList.add('is-visible');
      });
      return;
    }

    Array.prototype.forEach.call(targets, function (el) {
      el.classList.add(el.classList.contains('tour-photo') || el.classList.contains('owner-photo')
        ? 'reveal-image' : 'reveal');
    });

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.1 });

    Array.prototype.forEach.call(document.querySelectorAll('.reveal, .reveal-image'), function (el) {
      observer.observe(el);
    });
  })();

  /* ---------------------------------------------------------------------- *
   * 3. Navigation mobile
   * ---------------------------------------------------------------------- */
  (function initMenu() {
    var toggle = document.querySelector('.menu-toggle');
    var nav = document.getElementById('navigation');
    if (!toggle || !nav) return;

    function close() {
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Ouvrir le menu');
    }
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      if (open) { close(); return; }
      nav.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Fermer le menu');
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) close();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') close();
    });
  })();

  /* ---------------------------------------------------------------------- *
   * 4. Logements — API Django si ESSIVIVI_API_URL est renseigné, sinon aperçu.
   * ---------------------------------------------------------------------- */
  (function initListings() {
    var list = document.getElementById('listing-list');
    var form = document.getElementById('filters');
    var statusEl = document.getElementById('listings-status');
    var footEl = document.getElementById('listings-foot');
    if (!list || !form) return;

    var apiBase = (window.ESSIVIVI_API_URL || '').replace(/\/+$/, '');
    // Aperçu fidèle au modèle Django : seuls des champs existants, jamais de faux avis.
    var sample = [
      { id: 1, property_type: 'apartment', title: 'Appartement deux pièces, Akosombo',
        neighborhood: 'Akosombo', city: 'Lomé', rent: 85000, rooms_count: 2,
        has_virtual_tour: true, entrance_photo: 'assets/living-room.jpg' },
      { id: 2, property_type: 'house', title: 'Maison avec cour, Quartier nord',
        neighborhood: 'Quartier nord', city: 'Kara', rent: 60000, rooms_count: 4,
        has_virtual_tour: true, entrance_photo: 'assets/house.jpg' },
      { id: 3, property_type: 'studio', title: 'Studio meublé, centre-ville',
        neighborhood: 'Centre-ville', city: 'Lomé', rent: 45000, rooms_count: 1,
        has_virtual_tour: false, entrance_photo: 'assets/bedroom.jpg' },
      { id: 4, property_type: 'villa', title: 'Villa avec terrasse, zone résidentielle',
        neighborhood: 'Zone résidentielle', city: 'Lomé', rent: 180000, rooms_count: 5,
        has_virtual_tour: true, entrance_photo: 'assets/terrace.jpg' }
    ];

    var labels = {
      studio: 'Studio', room: 'Chambre', apartment: 'Appartement',
      house: 'Maison', villa: 'Villa'
    };

    function escapeHtml(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    }

    function formatRent(amount) {
      return new Intl.NumberFormat('fr-FR').format(Number(amount) || 0);
    }

    function itemMarkup(item) {
      var photo = item.entrance_photo || 'assets/apartment.jpg';
      return '' +
        '<article class="listing-item">' +
          '<div class="listing-photo"><img src="' + escapeHtml(photo) + '" alt="Photo d’entrée : ' +
            escapeHtml(item.title) + '" loading="lazy" width="1200" height="900"></div>' +
          '<div class="listing-body">' +
            '<p class="listing-type">' + escapeHtml(labels[item.property_type] || 'Logement') + '</p>' +
            '<h3>' + escapeHtml(item.title) + '</h3>' +
            '<p class="listing-place">' + escapeHtml(item.neighborhood || '') +
              (item.city ? ' · ' + escapeHtml(item.city) : '') + '</p>' +
            '<div class="listing-meta">' +
              '<p class="listing-rent">' + formatRent(item.rent) + ' F<small>loyer mensuel · FCFA</small></p>' +
              (item.has_virtual_tour
                ? '<span class="listing-badge">Visite 360° prête</span>'
                : '<span class="listing-badge">Visite en préparation</span>') +
            '</div>' +
          '</div>' +
        '</article>';
    }

    function render(items) {
      if (!items.length) {
        list.innerHTML = '<p class="listing-empty">Aucun logement ne correspond à ces filtres. ' +
          'Élargissez la ville ou le budget.</p>';
        return;
      }
      list.innerHTML = items.slice(0, 6).map(itemMarkup).join('');
    }

    function filterSample() {
      var city = form.elements.city.value.trim().toLowerCase();
      var type = form.elements.property_type.value;
      var maxRent = parseInt(form.elements.max_rent.value, 10);
      return sample.filter(function (item) {
        if (city && item.city.toLowerCase() !== city) return false;
        if (type && item.property_type !== type) return false;
        if (maxRent && Number(item.rent) > maxRent) return false;
        return true;
      });
    }

    function fetchListings(params) {
      var query = params.toString();
      var url = apiBase + '/api/properties/' + (query ? '?' + query : '');
      return fetch(url, { headers: { 'Accept': 'application/json' } })
        .then(function (response) {
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        })
        .then(function (data) {
          var items = Array.isArray(data) ? data : (data.results || []);
          render(items);
          statusEl.textContent = items.length + ' annonce' + (items.length > 1 ? 's' : '') + ' publiée' + (items.length > 1 ? 's' : '');
          footEl.textContent = 'Annonces chargées depuis l’API Essivivi.';
        })
        .catch(function () {
          // Dès que l’API est configurée, on ne présente jamais l’aperçu comme du live.
          list.innerHTML = '<p class="listing-empty">Les annonces ne peuvent pas être chargées pour le moment. Revenez dans un instant.</p>';
          statusEl.textContent = 'API momentanément indisponible.';
          footEl.textContent = 'Aucune annonce de démonstration n’est affichée quand le service est connecté.';
        });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!apiBase) { render(filterSample()); return; }
      var params = new URLSearchParams();
      ['city', 'property_type', 'max_rent'].forEach(function (key) {
        if (form.elements[key].value) params.set(key, form.elements[key].value);
      });
      fetchListings(params);
    });

    if (apiBase) {
      list.innerHTML = '<p class="listing-empty">Chargement des annonces publiées…</p>';
      statusEl.textContent = 'Chargement…';
      fetchListings(new URLSearchParams());
    } else {
      render(filterSample());
    }
  })();

  /* ---------------------------------------------------------------------- *
   * 5. Formulaire de contact — validation côté client, sans prétendre envoyer.
   * ---------------------------------------------------------------------- */
  (function initContact() {
    var form = document.getElementById('contact-form');
    if (!form) return;
    var note = document.getElementById('form-note');

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var fields = [
        { id: 'contact-name', error: 'error-name', valid: function (v) { return v.trim().length > 1; } },
        { id: 'contact-email', error: 'error-email', valid: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()); } },
        { id: 'contact-message', error: 'error-message', valid: function (v) { return v.trim().length > 9; } }
      ];
      var ok = true;
      fields.forEach(function (field) {
        var input = document.getElementById(field.id);
        var error = document.getElementById(field.error);
        var valid = field.valid(input.value);
        input.setAttribute('aria-invalid', valid ? 'false' : 'true');
        error.hidden = valid;
        if (!valid && ok) input.focus();
        if (!valid) ok = false;
      });
      note.textContent = ok
        ? 'Message vérifié. L’envoi sera actif dès que le formulaire sera relié à l’API.'
        : '';
      if (ok) form.reset();
    });
  })();
})();
