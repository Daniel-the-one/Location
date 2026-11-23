from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.validators import validate_file_size, validate_image_extension

IMAGE_VALIDATORS = [validate_image_extension, validate_file_size]


class Property(models.Model):
    """Un bien mis en location. Montants en francs CFA (XOF), entiers."""

    class Type(models.TextChoices):
        STUDIO = "studio", "Studio"
        ROOM = "room", "Chambre"
        APARTMENT = "apartment", "Appartement"
        HOUSE = "house", "Maison"
        VILLA = "villa", "Villa"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PENDING = "pending", "En attente de validation"
        PUBLISHED = "published", "Publié"
        REJECTED = "rejected", "Refusé"
        SUSPENDED = "suspended", "Suspendu"

    class Source(models.TextChoices):
        APP = "app", "Application"
        WEB = "web", "Déclaration web"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="properties"
    )
    property_type = models.CharField("type", max_length=12, choices=Type.choices)
    # Origine du dossier : une déclaration web n'a pas encore de pièces ni de panorama.
    source = models.CharField(
        "origine", max_length=8, choices=Source.choices, default=Source.APP
    )
    title = models.CharField("titre", max_length=150)
    description = models.TextField(blank=True)
    address = models.CharField("adresse", max_length=255)
    neighborhood = models.CharField("quartier", max_length=100)
    city = models.CharField("ville", max_length=100, db_index=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    rent = models.PositiveIntegerField("loyer mensuel (FCFA)", db_index=True)
    charges = models.PositiveIntegerField("charges (FCFA)", default=0)
    deposit = models.PositiveIntegerField("caution (FCFA)", default=0)
    visit_fee = models.PositiveIntegerField("frais de réservation de visite (FCFA)", default=0)
    rooms_count = models.PositiveSmallIntegerField("nombre de pièces", default=1)
    amenities = models.JSONField("équipements", default=list, blank=True)
    rules = models.TextField("règles", blank=True)
    available_from = models.DateField("disponible à partir du", null=True, blank=True)
    is_available = models.BooleanField("disponible", default=True)
    entrance_photo = models.ImageField(
        "photo de la porte d'entrée", upload_to="entrances/", blank=True, validators=IMAGE_VALIDATORS
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    rejection_reason = models.CharField(max_length=255, blank=True)
    # Une suspension décidée par l'admin ne peut pas être levée par le propriétaire.
    suspended_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "bien"
        indexes = [models.Index(fields=["status", "city", "neighborhood"])]

    def __str__(self):
        return self.title


class Room(models.Model):
    """Une pièce du bien ; `order` fixe sa place dans la visite virtuelle."""

    class Type(models.TextChoices):
        LIVING_ROOM = "living_room", "Salon"
        BEDROOM = "bedroom", "Chambre"
        KITCHEN = "kitchen", "Cuisine"
        BATHROOM = "bathroom", "Douche / salle de bain"
        TOILET = "toilet", "WC"
        BALCONY = "balcony", "Balcon"
        TERRACE = "terrace", "Terrasse"
        YARD = "yard", "Cour"
        OTHER = "other", "Autre"

    class PanoramaStatus(models.TextChoices):
        NONE = "none", "Aucune photo"
        PENDING = "pending", "Photos reçues"
        PROCESSING = "processing", "Assemblage en cours"
        READY = "ready", "Prêt"
        FAILED = "failed", "Échec"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rooms")
    room_type = models.CharField("type", max_length=12, choices=Type.choices)
    name = models.CharField("nom", max_length=80)
    is_exterior = models.BooleanField("à l'extérieur", default=False)
    order = models.PositiveSmallIntegerField("ordre dans la visite", default=0)
    panorama_status = models.CharField(
        max_length=10, choices=PanoramaStatus.choices, default=PanoramaStatus.NONE
    )

    class Meta:
        ordering = ["property", "order"]
        verbose_name = "pièce"

    def __str__(self):
        return f"{self.property} — {self.name}"


class RoomPhoto(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="room_photos/", validators=IMAGE_VALIDATORS)
    order = models.PositiveSmallIntegerField("ordre de prise", default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["room", "order"]
        verbose_name = "photo de pièce"


class Panorama(models.Model):
    """Panorama 360° d'une pièce, enregistré en trois tailles (chargement progressif)."""

    class Source(models.TextChoices):
        STITCHED = "stitched", "Assemblé par le serveur"
        UPLOADED = "uploaded", "Panorama du téléphone"
        SLIDESHOW = "slideshow", "Diaporama de secours"

    class Status(models.TextChoices):
        PROCESSING = "processing", "Assemblage en cours"
        READY = "ready", "Prêt"
        FAILED = "failed", "Échec"

    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name="panorama")
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.STITCHED)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PROCESSING)
    image_thumb = models.ImageField(upload_to="panoramas/thumb/", blank=True)
    image_medium = models.ImageField(upload_to="panoramas/medium/", blank=True)
    image_high = models.ImageField(upload_to="panoramas/high/", blank=True)
    error_message = models.TextField(blank=True)
    validated_by_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "panorama"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "property"], name="unique_favorite")
        ]
        verbose_name = "favori"


class ViewHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="view_history"
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        verbose_name = "consultation"
        verbose_name_plural = "historique de consultation"
