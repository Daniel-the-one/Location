/* Essivivi — déclaration publique d’un bien. Le front valide, le serveur décide. */
(function () {
  'use strict';

  var form = document.getElementById('declaration-form');
  if (!form) return;

  var apiBase = (window.ESSIVIVI_API_URL || '').replace(/\/+$/, '');
  var note = document.getElementById('declaration-note');
  var notice = document.getElementById('api-notice');
  var submit = document.getElementById('submit-declaration');
  var panel = document.getElementById('declaration-form-panel');
  var receipt = document.getElementById('receipt');
  var receiptId = document.getElementById('receipt-id');
  var receiptText = document.getElementById('receipt-text');

  /* Menu mobile, identique à celui de la vitrine. */
  (function initMenu() {
    var toggle = document.querySelector('.menu-toggle');
    var nav = document.querySelector('.mobile-nav');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      toggle.setAttribute('aria-label', open ? 'Ouvrir le menu' : 'Fermer le menu');
      nav.classList.toggle('is-open', !open);
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        toggle.setAttribute('aria-expanded', 'false');
        nav.classList.remove('is-open');
      }
    });
  })();

  if (!apiBase) {
    notice.hidden = false;
    notice.textContent = 'Le service de déclaration n’est pas encore connecté. Le formulaire est désactivé : aucune donnée ne serait enregistrée.';
    notice.classList.add('is-warning');
    submit.disabled = true;
    Array.prototype.forEach.call(form.elements, function (el) {
      if (el !== submit) el.disabled = true;
    });
    return;
  }

  var fieldNames = [
    'first_name', 'last_name', 'email', 'phone', 'password', 'title', 'property_type',
    'address', 'neighborhood', 'city', 'rent', 'charges', 'deposit', 'rooms_count',
    'description', 'entrance_photo', 'identity_document', 'consent'
  ];

  function showErrors(errors) {
    fieldNames.forEach(function (name) {
      var error = document.getElementById('error-' + name);
      if (error) { error.hidden = true; error.textContent = ''; }
      var input = form.elements[name];
      if (input && input.setAttribute) input.setAttribute('aria-invalid', 'false');
    });
    var firstInvalid = null;
    Object.keys(errors || {}).forEach(function (name) {
      var error = document.getElementById('error-' + name);
      var input = form.elements[name];
      var message = Array.isArray(errors[name]) ? errors[name].join(' ') : String(errors[name]);
      if (error) { error.textContent = message; error.hidden = false; }
      if (input && input.setAttribute) input.setAttribute('aria-invalid', 'true');
      if (!firstInvalid && input && input.focus) firstInvalid = input;
    });
    if (firstInvalid) firstInvalid.focus();
  }

  function localErrors() {
    var data = new FormData(form);
    var errors = {};
    function requireText(name, label) {
      if (!String(data.get(name) || '').trim()) errors[name] = 'Indiquez ' + label + '.';
    }
    requireText('first_name', 'votre prénom');
    requireText('last_name', 'votre nom');
    requireText('email', 'votre adresse e-mail');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(data.get('email') || ''))) {
      errors.email = 'Adresse e-mail invalide.';
    }
    if (String(data.get('password') || '').length < 8) errors.password = '8 caractères minimum.';
    requireText('title', 'un titre');
    requireText('address', 'l’adresse');
    requireText('neighborhood', 'le quartier');
    requireText('city', 'la ville');
    if (!data.get('property_type')) errors.property_type = 'Choisissez un type de bien.';
    if (Number(data.get('rent')) < 1000) errors.rent = 'Le loyer minimum est de 1 000 FCFA.';
    if (!data.get('entrance_photo') || !data.get('entrance_photo').name) {
      errors.entrance_photo = 'Ajoutez une photo du bien.';
    }
    if (!data.get('identity_document') || !data.get('identity_document').name) {
      errors.identity_document = 'Ajoutez votre pièce d’identité.';
    }
    if (!data.get('consent')) errors.consent = 'Votre accord est obligatoire.';
    return errors;
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var errors = localErrors();
    if (Object.keys(errors).length) {
      showErrors(errors);
      note.textContent = 'Vérifiez les champs signalés.';
      return;
    }

    showErrors({});
    note.textContent = 'Envoi en cours… ne fermez pas cette page.';
    submit.disabled = true;

    fetch(apiBase + '/api/declarations/', {
      method: 'POST',
      body: new FormData(form),
      headers: { 'Accept': 'application/json' }
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var err = new Error('HTTP ' + response.status);
          err.status = response.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    }).then(function (data) {
      panel.hidden = true;
      receipt.hidden = false;
      receiptId.textContent = data.dossier || 'dossier enregistré';
      receiptText.textContent = data.detail || 'Déclaration reçue.';
      receipt.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }).catch(function (err) {
      if (err.status === 429) {
        note.textContent = 'Trop de déclarations depuis cette connexion. Réessayez dans une heure.';
      } else if (err.status === 400 && err.data) {
        showErrors(err.data);
        note.textContent = 'Le serveur a refusé certains champs.';
      } else {
        note.textContent = 'Envoi impossible pour le moment. Vérifiez votre connexion, puis réessayez. Aucune déclaration n’a été enregistrée.';
      }
    }).then(function () {
      submit.disabled = false;
    });
  });

  document.getElementById('new-declaration').addEventListener('click', function () {
    form.reset();
    showErrors({});
    receipt.hidden = true;
    panel.hidden = false;
    note.textContent = '';
    submit.disabled = false;
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
})();
