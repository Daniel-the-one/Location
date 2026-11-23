# Essivivi — déclaration propriétaire et modération

Spécification du parcours demandé : **un propriétaire déclare son bien sur le site public,
le développeur/admin modère, puis le bien apparaît sur le site client**. Version 1,
éclaircie le 23 novembre 2026.

## 1. Problème

La vitrine statique livrée précédemment était lisible mais « pas cool » sur le plan
fonctionnel : elle affichait quatre annonces de démonstration, aucun propriétaire ne
pouvait déclarer un bien, et l'administration se limitait à `/django-admin/` (interface
Django générique, peu adaptée à une modération quotidienne).

Le backend Django contient déjà l'essentiel : modèles `Property`/`Room`/`Panorama`,
états `DRAFT → PENDING → PUBLISHED` (+ `REJECTED`, `SUSPENDED`), services métier
`submit_for_review`, `approve_property`, `reject_property`, suspension, et pièces
d'identité stockées hors web. Il manquait l'entrée publique, l'interface de modération
et le branchement de la vitrine sur l'API.

## 2. Périmètre du MVP

**Inclus**
1. Page publique `/declarer.html` : un propriétaire déclare un bien sans compte préalable.
2. Endpoint public `POST /api/declarations/` : crée le compte propriétaire, le bien en
   attente et la pièce d'identité en attente.
3. Console admin `/admin.html` : connexion JWT, tableau de bord, file de modération,
   décisions sur les biens et sur les identités, accès sécurisé aux documents.
4. API admin `GET/POST /api/admin/...` protégée par `IsPlatformAdmin`.
5. Vitrine branchée sur `GET /api/properties/` : seuls les biens `PUBLISHED` sont listés.
6. Déploiement Render : Web Service Django + Postgres, blueprint mis à jour.

**Hors périmètre (volontairement)**
- Paiement, envoi d'e-mail transactional configuré, CRM, messagerie admin.
- Refonte du parcours Flutter (déjà complet) ; la déclaration web est un raccourci,
  pas un doublon de l'assistant « plan de pièces ».
- Création automatique des panoramas 360° depuis la déclaration web : le bien est
  publié avec le badge « visite en préparation » ; le propriétaire pourra compléter
  les pièces plus tard depuis l'application.

## 3. Acteurs et droits

| Acteur | Droits |
| --- | --- |
| Visiteur | Lit les annonces publiées ; soumet une déclaration (une par heure/IP). |
| Propriétaire | Gère ses biens via l'API `/api/owner/*` ou l'app Flutter ; voit ses notifications. |
| Admin (`role=admin`) | Modère biens et identités via `/api/admin/*` et `/django-admin/`. |

Un compte créé par déclaration web a `role=owner` et un mot de passe choisi par le
déclarant. Il peut donc se connecter ensuite dans l'application. Aucun visiteur ne
peut se déclarer admin : le rôle est fixé côté serveur.

## 4. Parcours détaillés

### 4.1 Déclaration publique

1. Le propriétaire ouvre « Déclarer mon bien » depuis la vitrine.
2. Formulaire : identité (nom, prénom, e-mail, téléphone, mot de passe), bien (type,
   titre, adresse, quartier, ville, loyer, charges, caution, nombre de pièces,
   description), photo de l'entrée, pièce d'identité, consentement.
3. Contrôles serveur : mot de passe selon les règles Django, e-mail unique et
   normalisé, fichiers image/pdf ≤ 10 Mo, champ piège `website` vide, consentement
   coché, limite de 5 déclarations par heure et par adresse IP.
4. Écritures atomiques : `User(role=owner)` + `IdentityVerification(pending)` +
   `Property(source=web, status=pending)` + notifications aux admins.
5. Réponse : accusé de réception avec numéro de dossier. Aucune donnée n'est publiée
   à ce stade.

### 4.2 Modération admin

1. Connexion sur `/admin.html` avec e-mail/mot de passe admin → `POST /api/auth/login/`.
   Le jeton d'accès est conservé en `sessionStorage` (jamais en `localStorage`, jamais
   dans une URL).
2. Tableau de bord : biens en attente, biens publiés, identités en attente, déclarations
   web récentes.
3. File « Déclarations » : chaque dossier montre le bien, le propriétaire et l'état de
   sa pièce d'identité. Le document s'ouvre via un endpoint JWT, avec type imposé et
   CSP `sandbox`.
4. Décisions :
   - identité : `approve` / `reject(motif)` via les services existants ;
   - bien : `approve` (exige une identité validée pour une déclaration web) /
     `reject(motif)` / `suspend(motif)` / `unsuspend`.
5. Toute décision passe par les services métier existants : notifications et règles
   de statut restent identiques à l'admin Django et à l'app Flutter.

### 4.3 Publication côté client

`GET /api/properties/` ne renvoie que `status=published`. Dès qu'un admin valide un
bien, la vitrine l'affiche au prochain chargement. Le badge « visite en préparation »
est affiché tant qu'aucun panorama n'est prêt — aucune visite 360° n'est simulée.

## 5. Modèle de données

Ajout d'un seul champ :

```python
Property.source = CharField(max_length=8, choices=[("app","Application"),("web","Déclaration web")], default="app")
```

Il permet de distinguer une déclaration web (sans pièces, sous modération) d'une annonce
construite dans l'application, et d'assouplir volontairement la règle « au moins une
pièce photo » pour le web. La règle « identité validée avant publication » reste, elle,
appliquée au moment de l'approbation admin.

Aucune table supplémentaire : `IdentityVerification` et `Notification` existent déjà.

## 6. Sécurité

- Admin API : `IsPlatformAdmin` sur toutes les vues ; jeton SimpleJWT ; le statut du
  compte est vérifié à chaque requête (authentication existante).
- Documents privés : jamais servis depuis `MEDIA_URL` ; endpoint dédié, extension
  autorisée uniquement, `X-Content-Type-Options: nosniff`, CSP sandbox.
- Déclaration publique : honeypot, throttle IP, validation serveur de tous les champs,
  mot de passe haché par Django, e-mail normalisé, rejet des doublons.
- Front : échappement HTML de toute donnée API, aucun secret dans le JavaScript,
  CORS limité aux origines connues, HTTPS forcé hors debug.
- Le mot de passe admin est généré par Render (`generateValue`) et retiré du code :
  le développeur le lit dans le dashboard Render, jamais dans le dépôt ni dans le chat.

## 7. Hébergement

- Static Site existant : `essivivi-vitrine` (déjà en ligne).
- Web Service Django `essivivi-api`, plan gratuit, `gunicorn`, `collectstatic`.
- Postgres gratuit Render ; `DATABASE_URL` injectée par le blueprint (`fromDatabase`).
- `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL` renseignés explicitement.
- Commande idempotente `ensure_admin` au démarrage : crée le compte admin si
  `ESSIVIVI_ADMIN_EMAIL`/`ESSIVIVI_ADMIN_PASSWORD` existent, ne réinitialise jamais
  un mot de passe existant.

Risque connu : l'offre gratuite Render met le service en veille après inactivité,
le premier appel peut prendre quelques secondes. Le front affiche un état explicite
plutôt que de prétendre que l'API est cassée.

## 8. Vérification

- Backend : tests Django/DRF couvrant déclaration (création, honeypot, doublon,
  throttle), permissions admin (401/403), transitions de modération, endpoint document.
- Front : `node --check` sur les scripts, contrôle visuel et console navigateur sur
  `/declarer.html` et `/admin.html`, aucune donnée inventée.
- Production : recette HTTPS des endpoints publics et admin, puis vérification que
  le bien validé apparaît dans la liste publique.
