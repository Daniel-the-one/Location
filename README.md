# Essivivi — Location de logements avec visite virtuelle

Projet de classe (rendu le 30 novembre 2026). Le locataire visite chaque pièce en panorama 360°
construit à partir des photos du propriétaire.

| Dossier | Contenu |
| --- | --- |
| `backend/` | Django 5.2 + Django REST Framework : API, interface administrateur, assemblage des panoramas |
| `app/` | Application Flutter unique pour le web (Vercel) et Android (APK) |
| `docs/` | UML, modèle de données, guides |

## Backend

Prérequis : Python 3.12, MySQL 8.0.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1          # créer d'abord avec : python -m venv .venv
pip install -r requirements.txt
Copy-Item .env.example .env           # puis renseigner DATABASE_URL
```

Créer la base dans MySQL :

```sql
CREATE DATABASE essivivi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Puis :

```powershell
python manage.py migrate
python manage.py createsuperuser      # compte administrateur
python manage.py runserver
```

- Documentation de l'API (Swagger) : http://127.0.0.1:8000/api/docs/
- Admin Django (temporaire, en attendant l'interface admin dédiée) : http://127.0.0.1:8000/django-admin/

Tests : `python manage.py test` (sans `DATABASE_URL`, ils tournent sur SQLite).

### Endpoints d'authentification

| Méthode | URL | Rôle |
| --- | --- | --- |
| POST | `/api/auth/register/` | Inscription locataire ou propriétaire, renvoie les jetons JWT |
| POST | `/api/auth/login/` | Connexion par email |
| POST | `/api/auth/refresh/` | Nouveau jeton d'accès |
| GET / PATCH | `/api/auth/me/` | Profil |
| POST | `/api/auth/password-reset/` puis `/confirm/` | Mot de passe oublié |
| GET / POST | `/api/auth/identity/` | Pièce d'identité du propriétaire (stockage privé) |

## Application Flutter

```powershell
cd app
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://127.0.0.1:8000/api
flutter test
```

Sur l'émulateur Android, utiliser `API_URL=http://10.0.2.2:8000/api`.
