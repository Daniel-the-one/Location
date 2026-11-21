from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.common.storage import private_storage
from apps.common.validators import (
    validate_document_extension,
    validate_file_size,
    validate_image_extension,
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("L'email est obligatoire.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=User.Role.ADMIN)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Un compte est locataire OU propriétaire (ou administrateur), jamais les deux."""

    class Role(models.TextChoices):
        TENANT = "tenant", "Locataire"
        OWNER = "owner", "Propriétaire"
        ADMIN = "admin", "Administrateur"

    class Status(models.TextChoices):
        ACTIVE = "active", "Actif"
        SUSPENDED = "suspended", "Suspendu"
        BLOCKED = "blocked", "Bloqué"

    class Language(models.TextChoices):
        FR = "fr", "Français"
        EN = "en", "English"

    username = None
    email = models.EmailField("email", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TENANT)
    phone = models.CharField("téléphone", max_length=20, blank=True)
    photo = models.ImageField(
        upload_to="avatars/",
        blank=True,
        validators=[validate_image_extension, validate_file_size],
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.FR)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"

    def __str__(self):
        return self.email

    @property
    def is_tenant(self):
        return self.role == self.Role.TENANT

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_identity_verified(self):
        return self.identity_verifications.filter(
            status=IdentityVerification.Status.APPROVED
        ).exists()


class IdentityVerification(models.Model):
    """Pièce d'identité d'un propriétaire, visible seulement par l'administrateur."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Validée"
        REJECTED = "rejected", "Refusée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identity_verifications"
    )
    document = models.FileField(
        upload_to="identity/",
        storage=private_storage,
        validators=[validate_document_extension, validate_file_size],
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.CharField(max_length=255, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_identities",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "vérification d'identité"

    def __str__(self):
        return f"{self.user} — {self.get_status_display()}"
