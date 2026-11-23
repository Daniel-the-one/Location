/* Essivivi — console de modération. Le jeton reste en sessionStorage, jamais dans une URL. */
(function () {
  'use strict';

  var apiBase = (window.ESSIVIVI_API_URL || '').replace(/\/+$/, '');
  var TOKEN_KEY = 'essivivi.admin.token';
  var loginPanel = document.getElementById('login-panel');
  var loginForm = document.getElementById('login-form');
  var loginNote = document.getElementById('login-note');
  var consoleEl = document.getElementById('console');
  var logoutBtn = document.getElementById('logout');
  var note = document.getElementById('console-note');
  var statsEl = document.getElementById('stats');
  var propertyList = document.getElementById('property-list');
  var identityList = document.getElementById('identity-list');
  var propertyStatus = document.getElementById('property-status');
  var propertySource = document.getElementById('property-source');
  var identityStatus = document.getElementById('identity-status');

  (function initMenu() {
    var toggle = document.querySelector('.menu-toggle');
    var nav = document.querySelector('.mobile-nav');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      nav.classList.toggle('is-open', !open);
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) { toggle.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); }
    });
  })();

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function token() { return sessionStorage.getItem(TOKEN_KEY) || ''; }

  function setNote(message, isError) {
    note.textContent = message || '';
    note.classList.toggle('is-error', Boolean(isError));
  }

  function api(path, options) {
    options = options || {};
    var headers = Object.assign({ 'Accept': 'application/json' }, options.headers || {});
    if (token()) headers['Authorization'] = 'Bearer ' + token();
    return fetch(apiBase + path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body
    }).then(function (response) {
      if (response.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY);
        showLogin();
        throw new Error('Session expirée. Reconnectez-vous.');
      }
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var err = new Error(data.detail || ('HTTP ' + response.status));
          err.data = data;
          err.status = response.status;
          throw err;
        }
        return data;
      });
    });
  }

  var STATUS_LABELS = {
    draft: 'Brouillon', pending: 'En attente', published: 'Publié',
    rejected: 'Refusé', suspended: 'Suspendu'
  };
  var IDENTITY_LABELS = { pending: 'À vérifier', approved: 'Vérifiée', rejected: 'Refusée' };
  var TYPE_LABELS = {
    studio: 'Studio', room: 'Chambre', apartment: 'Appartement',
    house: 'Maison', villa: 'Villa'
  };

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    return isNaN(d.getTime()) ? String(value).slice(0, 10) : d.toLocaleDateString('fr-FR');
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('fr-FR').format(Number(value) || 0) + ' F';
  }

  function statusBadge(status) {
    var key = STATUS_LABELS[status] ? status : 'draft';
    return '<span class="badge badge-' + escapeHtml(key) + '">' + escapeHtml(STATUS_LABELS[key]) + '</span>';
  }

  function identityBadge(status) {
    var key = IDENTITY_LABELS[status] ? status : 'pending';
    return '<span class="badge badge-' + (key === 'approved' ? 'published' : key === 'rejected' ? 'rejected' : 'pending') + '">' +
      escapeHtml(IDENTITY_LABELS[key]) + '</span>';
  }

  function reasonBox(type, id) {
    return '<div class="reason-box" hidden>' +
      '<label for="reason-' + type + '-' + id + '">Motif (5 caractères minimum)</label>' +
      '<input id="reason-' + type + '-' + id + '" type="text" maxlength="255">' +
      '<button class="btn btn-solid btn-small" type="button" data-action="confirm-reject" data-type="' + type + '" data-id="' + id + '">Confirmer le refus</button>' +
      '</div>';
  }

  function propertyCard(item) {
    var id = item.id;
    var photo = item.entrance_photo_url
      ? '<img src="' + escapeHtml(item.entrance_photo_url) + '" alt="Photo d’entrée : ' + escapeHtml(item.title) + '" loading="lazy">'
      : '<div class="card-photo-empty">Photo à venir</div>';
    var actions = '';
    if (item.status === 'pending') {
      actions = '<button class="btn btn-solid btn-small" type="button" data-action="approve-property" data-id="' + id + '">Publier</button>' +
        '<button class="btn btn-ghost btn-small" type="button" data-action="reject" data-type="property" data-id="' + id + '">Refuser</button>';
    } else if (item.status === 'published') {
      actions = '<button class="btn btn-ghost btn-small" type="button" data-action="suspend" data-id="' + id + '">Suspendre</button>';
    } else if (item.status === 'suspended' && item.suspended_by_admin) {
      actions = '<button class="btn btn-solid btn-small" type="button" data-action="unsuspend" data-id="' + id + '">Rétablir</button>';
    }
    return '<article class="mod-card" id="property-' + id + '">' +
      '<div class="card-photo">' + photo + '</div>' +
      '<div class="card-body">' +
        '<div class="card-topline">' + statusBadge(item.status) +
          (item.source === 'web' ? '<span class="badge badge-source">Déclaration web</span>' : '<span class="badge badge-plain">Application</span>') +
          '<span class="card-dossier">' + escapeHtml(item.dossier) + '</span></div>' +
        '<h2>' + escapeHtml(item.title) + '</h2>' +
        '<p class="card-meta">' + escapeHtml(TYPE_LABELS[item.property_type] || 'Logement') + ' · ' +
          escapeHtml(item.neighborhood) + (item.city ? ' · ' + escapeHtml(item.city) : '') + ' · ' +
          formatMoney(item.rent) + '</p>' +
        '<p class="card-address">' + escapeHtml(item.address) + '</p>' +
        '<p class="card-owner">Propriétaire : <strong>' + escapeHtml(item.owner_name) + '</strong> · ' +
          escapeHtml(item.owner_email) + (item.owner_phone ? ' · ' + escapeHtml(item.owner_phone) : '') + '</p>' +
        '<p class="card-identity">Identité : ' + identityBadge(item.identity_status) +
          ' · Signalé le ' + escapeHtml(formatDate(item.created_at)) + '</p>' +
        (item.rejection_reason ? '<p class="card-reason">Motif : ' + escapeHtml(item.rejection_reason) + '</p>' : '') +
        '<div class="card-actions">' + actions + '</div>' + reasonBox('property', id) +
      '</div></article>';
  }

  function identityCard(item) {
    var id = item.id;
    var actions = '';
    if (item.status === 'pending') {
      actions = '<button class="btn btn-ghost btn-small" type="button" data-action="view-document" data-id="' + id + '">Voir la pièce</button>' +
        '<button class="btn btn-solid btn-small" type="button" data-action="approve-identity" data-id="' + id + '">Vérifier</button>' +
        '<button class="btn btn-ghost btn-small" type="button" data-action="reject" data-type="identity" data-id="' + id + '">Refuser</button>';
    } else {
      actions = '<button class="btn btn-ghost btn-small" type="button" data-action="view-document" data-id="' + id + '">Voir la pièce</button>';
    }
    return '<article class="mod-card mod-card-compact" id="identity-' + id + '">' +
      '<div class="card-body">' +
        '<div class="card-topline">' + identityBadge(item.status) + '<span class="card-dossier">ID-' + String(id).padStart(6, '0') + '</span></div>' +
        '<h2>' + escapeHtml(item.user_name) + '</h2>' +
        '<p class="card-owner">' + escapeHtml(item.user_email) + (item.user_phone ? ' · ' + escapeHtml(item.user_phone) : '') + '</p>' +
        '<p class="card-meta">Déposée le ' + escapeHtml(formatDate(item.created_at)) +
          (item.reviewed_at ? ' · traitée le ' + escapeHtml(formatDate(item.reviewed_at)) : '') + '</p>' +
        (item.rejection_reason ? '<p class="card-reason">Motif : ' + escapeHtml(item.rejection_reason) + '</p>' : '') +
        '<div class="card-actions">' + actions + '</div>' + reasonBox('identity', id) +
      '</div></article>';
  }

  function renderStats(data) {
    var p = data.properties || {};
    var i = data.identities || {};
    var cards = [
      ['Biens en attente', p.pending, 'À traiter'],
      ['Pièces à vérifier', i.pending, 'Identité'],
      ['Biens publiés', p.published, 'Visibles sur le site'],
      ['Déclarations web', data.web_declarations, 'Depuis le formulaire public']
    ];
    statsEl.innerHTML = cards.map(function (c) {
      return '<div class="stat"><span class="stat-value">' + escapeHtml(c[1]) + '</span>' +
        '<span class="stat-label">' + escapeHtml(c[0]) + '</span><span class="stat-sub">' + escapeHtml(c[2]) + '</span></div>';
    }).join('');
    document.getElementById('tab-properties-count').textContent = p.pending || 0;
    document.getElementById('tab-identities-count').textContent = i.pending || 0;
  }

  function loadProperties() {
    var params = new URLSearchParams();
    if (propertyStatus.value) params.set('status', propertyStatus.value);
    if (propertySource.value) params.set('source', propertySource.value);
    return api('/api/admin/properties/?' + params.toString()).then(function (data) {
      var items = data.results || [];
      propertyList.innerHTML = items.length ? items.map(propertyCard).join('')
        : '<p class="card-empty">Aucun bien dans cette catégorie.</p>';
    });
  }

  function loadIdentities() {
    var params = new URLSearchParams();
    if (identityStatus.value) params.set('status', identityStatus.value);
    return api('/api/admin/identities/?' + params.toString()).then(function (data) {
      var items = data.results || [];
      identityList.innerHTML = items.length ? items.map(identityCard).join('')
        : '<p class="card-empty">Aucune pièce dans cette catégorie.</p>';
    });
  }

  function loadAll() {
    setNote('Chargement…');
    api('/api/admin/overview/').then(function (data) {
      renderStats(data);
      return Promise.allSettled([loadProperties(), loadIdentities()]);
    }).then(function (results) {
      var failed = results.some(function (r) { return r.status === 'rejected'; });
      setNote(failed ? 'Certaines listes n’ont pas pu être chargées.' : 'Données à jour.', failed);
    }).catch(function (err) { setNote(err.message, true); });
  }

  function showConsole() {
    loginPanel.hidden = true;
    consoleEl.hidden = false;
    logoutBtn.hidden = false;
    loadAll();
  }

  function showLogin(message) {
    sessionStorage.removeItem(TOKEN_KEY);
    loginPanel.hidden = false;
    consoleEl.hidden = true;
    logoutBtn.hidden = true;
    if (message) loginNote.textContent = message;
  }

  loginForm.addEventListener('submit', function (event) {
    event.preventDefault();
    loginNote.textContent = 'Connexion…';
    fetch(apiBase + '/api/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({
        email: loginForm.elements.email.value.trim().toLowerCase(),
        password: loginForm.elements.password.value
      })
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) throw new Error(data.detail || 'Identifiants incorrects.');
        if (!data.user || data.user.role !== 'admin') {
          throw new Error('Ce compte n’est pas un compte administrateur.');
        }
        sessionStorage.setItem(TOKEN_KEY, data.access);
        showConsole();
      });
    }).catch(function (err) {
      loginNote.textContent = err.message;
    });
  });

  logoutBtn.addEventListener('click', function () {
    showLogin('Vous êtes déconnecté.');
    loginForm.reset();
  });

  document.getElementById('refresh').addEventListener('click', loadAll);
  propertyStatus.addEventListener('change', loadProperties);
  propertySource.addEventListener('change', loadProperties);
  identityStatus.addEventListener('change', loadIdentities);

  Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (tab) {
    tab.addEventListener('click', function () {
      Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (other) {
        var active = other === tab;
        other.classList.toggle('is-active', active);
        other.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      document.getElementById('panel-properties').hidden = tab.dataset.tab !== 'properties';
      document.getElementById('panel-identities').hidden = tab.dataset.tab !== 'identities';
    });
  });

  document.addEventListener('click', function (event) {
    var button = event.target.closest('button[data-action]');
    if (!button) return;
    var action = button.dataset.action;
    var id = button.dataset.id;
    var type = button.dataset.type;
    var card = button.closest('.mod-card');
    var box = card ? card.querySelector('.reason-box') : null;

    if (action === 'reject') {
      if (box) { box.hidden = false; var input = box.querySelector('input'); if (input) input.focus(); }
      return;
    }
    if (action === 'confirm-reject') {
      var reasonEl = box && box.querySelector('input');
      var reason = reasonEl ? reasonEl.value.trim() : '';
      if (reason.length < 5) { setNote('Indiquez un motif d’au moins 5 caractères.', true); return; }
      decide(type, id, 'reject', { reason: reason }, button);
      return;
    }
    if (action === 'view-document') {
      viewDocument(id, button);
      return;
    }
    var endpoint = action === 'approve-property' ? 'properties' :
      action === 'approve-identity' ? 'identities' :
      action === 'suspend' ? 'properties' :
      action === 'unsuspend' ? 'properties' : null;
    if (!endpoint) return;
    var step = action.replace('-property', '').replace('-identity', '');
    if (action === 'suspend') step = 'suspend';
    if (action === 'unsuspend') step = 'unsuspend';
    var body = action === 'suspend' ? { reason: '' } : undefined;
    decide(endpoint, id, step, body, button, action === 'approve-property');
  });

  function decide(endpoint, id, step, body, button, confirmIdentityFirst) {
    setNote('Décision enregistrée…');
    button.disabled = true;
    api('/api/admin/' + endpoint + '/' + id + '/' + step + '/', {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined
    }).then(function () {
      setNote('Décision enregistrée.');
      return loadAll();
    }).catch(function (err) {
      var msg = err.message;
      if (err.status === 409) {
        msg = 'Validez d’abord la pièce d’identité dans l’onglet Identités, puis republiez le bien.';
      }
      setNote(msg, true);
      button.disabled = false;
    });
  }

  function viewDocument(id, button) {
    setNote('Ouverture du document…');
    button.disabled = true;
    fetch(apiBase + '/api/admin/identities/' + id + '/document/', {
      headers: { 'Authorization': 'Bearer ' + token(), 'Accept': '*/*' }
    }).then(function (response) {
      if (response.status === 401) { sessionStorage.removeItem(TOKEN_KEY); showLogin('Session expirée.'); throw new Error('Session expirée.'); }
      if (!response.ok) throw new Error('Document indisponible (' + response.status + ').');
      return response.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var opened = window.open(url, '_blank', 'noopener');
      if (!opened) setNote('Ouvrez la pièce depuis le blocage de fenêtres du navigateur.', true);
      else setNote('Document ouvert dans un nouvel onglet. Lien temporaire, valable pour cette session uniquement.');
      window.setTimeout(function () { URL.revokeObjectURL(url); }, 120000);
    }).catch(function (err) { setNote(err.message, true); })
      .then(function () { button.disabled = false; });
  }

  if (!apiBase) {
    loginNote.textContent = 'Le backend n’est pas encore configuré. La connexion sera active dès son déploiement.';
    loginForm.querySelector('button[type="submit"]').disabled = true;
    return;
  }

  if (token()) {
    api('/api/auth/me/').then(function (user) {
      if (user.role === 'admin') showConsole();
      else showLogin('Ce compte n’est pas un compte administrateur.');
    }).catch(function () { showLogin(); });
  }
})();
