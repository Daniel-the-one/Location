from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Comptes"

    def ready(self):
        from . import schema  # noqa: F401  (enregistre l'extension Swagger)
