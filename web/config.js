/*
 * Configuration du site Essivivi et des deux espaces applicatifs.
 *
 * Laissez la chaîne vide pour afficher l’aperçu de démonstration intégré à app.js.
 * Renseignez l’URL publique du backend Django (sans slash final) pour charger les
 * annonces réelles, activer la déclaration publique (declarer.html) et la console
 * de modération (admin.html) :
 *
 *   window.ESSIVIVI_API_URL = "https://essivivi-api.onrender.com";
 *
 * Le backend doit autoriser l’origine du site dans CORS_ALLOWED_ORIGINS et,
 * en production, dans ALLOWED_HOSTS. Les visiteurs lisent uniquement
 * GET /api/properties/ (force le statut published). La déclaration publique
 * utilise POST /api/declarations/ ; la console utilise /api/admin/* avec un
 * jeton JWT conservé en sessionStorage, jamais dans une URL ni localStorage.
 */
window.ESSIVIVI_API_URL = "";
