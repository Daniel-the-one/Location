from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class ActiveStatusJWTScheme(SimpleJWTScheme):
    """Déclare notre authentification JWT dans Swagger (bouton « Authorize »)."""

    target_class = "apps.accounts.authentication.ActiveStatusJWTAuthentication"
    name = "jwtAuth"
