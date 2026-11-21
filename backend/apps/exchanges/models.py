from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.storage import private_storage
from apps.common.validators import validate_document_extension, validate_file_size
from apps.properties.models import Property

USER = settings.AUTH_USER_MODEL


class Conversation(models.Model):
    """Fil de discussion entre un locataire et le propriétaire, à propos d'un bien."""

    tenant = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="tenant_conversations")
    owner = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="owner_conversations")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "property"], name="unique_conversation")
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class VisitAppointment(models.Model):
    """Demande de visite physique sur un créneau."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        DECLINED = "declined", "Refusée"
        CANCELLED = "cancelled", "Annulée"
        DONE = "done", "Effectuée"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="appointments")
    tenant = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="appointments")
    slot = models.DateTimeField("créneau")
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slot"]
        verbose_name = "rendez-vous de visite"


class RentalRequest(models.Model):
    """Demande de location avec dossier ; le propriétaire accepte ou refuse."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        REFUSED = "refused", "Refusée"
        CANCELLED = "cancelled", "Annulée"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rental_requests")
    tenant = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="rental_requests")
    dossier = models.FileField(
        upload_to="dossiers/",
        storage=private_storage,
        blank=True,
        validators=[validate_document_extension, validate_file_size],
    )
    message = models.TextField(blank=True)
    occupation = models.CharField("profession", max_length=120, blank=True)
    monthly_income = models.PositiveIntegerField("revenu mensuel (FCFA)", null=True, blank=True)
    move_in_date = models.DateField("date d'entrée souhaitée", null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    refusal_reason = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "demande de location"


class Notification(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "Dans l'application"
        EMAIL = "email", "Email"
        PUSH = "push", "Notification push"

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField("type", max_length=40)
    title = models.CharField(max_length=150)
    content = models.TextField()
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Report(models.Model):
    """Signalement d'une annonce ou d'un compte (exactement une cible)."""

    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        IN_REVIEW = "in_review", "En cours"
        RESOLVED = "resolved", "Traité"
        DISMISSED = "dismissed", "Classé sans suite"

    author = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="reports_made")
    target_property = models.ForeignKey(
        Property, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    target_user = models.ForeignKey(
        USER, on_delete=models.CASCADE, null=True, blank=True, related_name="reports_received"
    )
    reason = models.CharField("motif", max_length=120)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    handled_by = models.ForeignKey(
        USER, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports_handled"
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "signalement"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(target_property__isnull=False, target_user__isnull=True)
                    | Q(target_property__isnull=True, target_user__isnull=False)
                ),
                name="report_exactly_one_target",
            )
        ]
