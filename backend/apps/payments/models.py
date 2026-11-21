import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.exchanges.models import RentalRequest, VisitAppointment


def new_reference():
    return uuid.uuid4().hex[:16].upper()


class Payment(models.Model):
    """Paiement en FCFA, lié à un rendez-vous (frais de visite) ou à une demande de location."""

    class Kind(models.TextChoices):
        VISIT = "visit", "Frais de réservation de visite"
        DEPOSIT = "deposit", "Caution"
        RENT = "rent", "Premier loyer"

    class Method(models.TextChoices):
        ON_SITE = "on_site", "Paiement sur place"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmé"
        FAILED = "failed", "Échoué"
        CANCELLED = "cancelled", "Annulé"

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments"
    )
    appointment = models.ForeignKey(
        VisitAppointment, on_delete=models.PROTECT, null=True, blank=True, related_name="payments"
    )
    rental_request = models.ForeignKey(
        RentalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="payments"
    )
    kind = models.CharField("type", max_length=10, choices=Kind.choices)
    amount = models.PositiveIntegerField("montant (FCFA)")
    method = models.CharField("mode", max_length=15, choices=Method.choices)
    provider = models.CharField("agrégateur", max_length=30, blank=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=32, unique=True, default=new_reference)
    # Commission de la plateforme : hors périmètre pour l'instant, champ laissé vide.
    commission = models.PositiveIntegerField("commission (FCFA)", null=True, blank=True)
    receipt = models.FileField("reçu PDF", upload_to="receipts/", blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_payments",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "paiement"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(appointment__isnull=False, rental_request__isnull=True)
                    | Q(appointment__isnull=True, rental_request__isnull=False)
                ),
                name="payment_exactly_one_subject",
            )
        ]

    def __str__(self):
        return f"{self.reference} — {self.amount} FCFA"


class Lease(models.Model):
    """Contrat de bail PDF généré après acceptation d'une demande de location."""

    rental_request = models.OneToOneField(
        RentalRequest, on_delete=models.PROTECT, related_name="lease"
    )
    pdf = models.FileField(upload_to="leases/")
    start_date = models.DateField("date d'effet", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "contrat de bail"
