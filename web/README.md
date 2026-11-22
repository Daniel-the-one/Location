# Essivivi — site vitrine

Site vitrine public, statique, complémentaire de l'application Flutter (`app/`) et de
l'API Django (`backend/`). Il présente le concept de visite 360°, explique le parcours
propriétaire et affiche les annonces publiées lorsque l'API est connectée.

**Aucune compilation, aucune dépendance npm.** Le dossier `web/` est publié tel quel.

## Lancer en local

Depuis ce dossier :

```powershell
python -m http.server 8080
```

Ouvrir ensuite `http://localhost:8080/`. Pour que le panneau de visite fonctionne, le
serveur doit servir `index.html`, `styles.css`, `app.js`, `config.js` et `assets/`.

## Brancher l'API Django

Par défaut, `config.js` laisse `window.ESSIVIVI_API_URL = ""` : la page affiche un
**aperçu de démonstration** explicitement signalé comme tel. Pour charger les annonces
réelles, renseigner l'URL publique du backend :

```js
window.ESSIVIVI_API_URL = "https://essivivi-api.onrender.com";
```

Requêtes effectuées : `GET /api/properties/` avec `city`, `property_type`, `max_rent`.
Champs utilisés : `title`, `property_type`, `neighborhood`, `city`, `rent`,
`entrance_photo`, `has_virtual_tour`. Aucune écriture n'est faite depuis ce site.

Côté backend, l'origine du site doit être autorisée dans `CORS_ALLOWED_ORIGINS`, et
l'hôte dans `ALLOWED_HOSTS`. Si l'API est momentanément indisponible, la page revient à
l'aperçu **en l'annonçant** ; elle ne prétend jamais afficher des données live.

Le formulaire de contact valide les champs côté client. Il **n'envoie rien** : un message
l'indique clairement après validation.

## Structure

```
web/
├── index.html              Page sémantique, lisible sans CSS ni JavaScript
├── styles.css              Design system (tokens OKLCH, responsive, a11y)
├── app.js                  Panorama 360°, filtres, menu, formulaire
├── config.js               Point de branchement de l'API
├── design/COMMIT-SHEET.md  Décisions artistiques et anti-slop
└── assets/
    ├── *.jpg               Photographies Pexels, téléchargées localement
    └── ATTRIBUTION.md      Licence et identifiants des images
```

## Accessibilité

- Skip link, focus visibles, `aria-*` sur le panorama et le menu mobile.
- Panorama manipulable à la souris, au doigt et au clavier (flèches, Home, End).
- `prefers-reduced-motion` : plus de translation ni de glisser automatique.
- Sans JavaScript, tout le contenu reste visible ; seules les animations disparaissent.

## Déploiement Render

Le fichier `render.yaml` à la racine du dépôt décrit un **Static Site** :

- `staticPublishPath: ./web`
- en-têtes de sécurité (`nosniff`, `X-Frame-Options`, `Referrer-Policy`)
- cache d'un jour sur `/assets/*`

Le backend Django reste commenté dans le blueprint : il sera activé quand une base de
production sera choisie (les identifiants MySQL ne sont pas encore définis).

## Crédits

Photographies : Pexels, licence Pexels. Voir `assets/ATTRIBUTION.md`.
Couleur de marque : `#1F6F5C`, relevée dans `app/lib/main.dart`.
