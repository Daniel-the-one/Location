"""Déclaration publique d'un bien par un propriétaire.

Un seul point d'entrée, sans compte préalable : le formulaire web crée le compte,
la pièce d'identité et le bien en attente. Rien n'est publié avant modération.
"""
from django.contrib.auth import password_validation
from django.core.cache import cache
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from apps.accounts.models import IdentityVerification, User
from apps.common.images import resize_upload
from apps.common.validators import (
    validate_document_extension,
    validate_file_size,
    validate_image_extension,
)
from apps.exchanges.notifications import notify

from .models import Property

ACKNOWLEDGEMENT = (
    "Déclaration reçue. Votre bien sera visible sur le site seulement après "
    "vérification de votre identité et validation de l'annonce par l'équipe Essivivi."
)
THROTTLE_RATE = 5
THROTTLE_WINDOW = 3600  # secondes


def client_ip(request) -> str:
    """Adresse utilisée pour la limite anti-spam (proxy Render inclus)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "inconnue")


class DeclarationThrottle(BaseThrottle):
    """Au plus cinq déclarations par heure et par adresse IP."""

    def allow_request(self, request, view):
        self.key = f"declaration:{client_ip(request)}"
        count = cache.get(self.key, 0)
        if count >= THROTTLE_RATE:
            return False
        cache.set(self.key, count + 1, THROTTLE_WINDOW)
        return True

    def wait(self):
        return THROTTLE_WINDOW


class DeclarationSerializer(serializers.Serializer):
    """Validation serveur complète : le front n'est jamais une source de vérité."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    property_type = serializers.ChoiceField(choices=Property.Type.choices)
    title = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=255)
    neighborhood = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    rent = serializers.IntegerField(min_value=1000, max_value=100_000_000)
    charges = serializers.IntegerField(min_value=0, max_value=100_000_000, required=False, default=0)
    deposit = serializers.IntegerField(min_value=0, max_value=100_000_000, required=False, default=0)
    rooms_count = serializers.IntegerField(min_value=1, max_value=30, required=False, default=1)
    description = serializers.CharField(required=False, allow_blank=True, default="", max_length=4000)

    entrance_photo = serializers.ImageField(
        validators=[validate_image_extension, validate_file_size]
    )
    identity_document = serializers.FileField(
        validators=[validate_document_extension, validate_file_size]
    )
    consent = serializers.BooleanField()
    # Champ piège : laissé vide par un humain, rempli par la plupart des robots.
    website = serializers.CharField(required=False, allow_blank=True, max_length=100, default="")

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Un compte existe déjà avec cet e-mail. Connectez-vous depuis l'application "
                "pour déclarer un autre bien."
            )
        return value

    def validate_phone(self, value):
        value = (value or "").strip()
        if value and not value.startswith("+"):
            value = "+228" + value.lstrip("0")
        if value and (len(value) < 8 or not value[1:].replace(" ", "").isdigit()):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return value

    def validate(self, attrs):
        if not attrs.get("consent"):
            raise serializers.ValidationError({"consent": "Le consentement est obligatoire."})
        candidate = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        password_validation.validate_password(attrs["password"], candidate)
        return attrs


@transaction.atomic
def create_web_declaration(data: dict) -> Property:
    """Crée le dossier complet de façon atomique et prévient les administrateurs."""
    owner = User.objects.create_user(
        email=data["email"],
        password=data["password"],
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        phone=data.get("phone", ""),
        role=User.Role.OWNER,
    )
    IdentityVerification.objects.create(
        user=owner, document=data["identity_document"], status=IdentityVerification.Status.PENDING
    )
    prop = Property.objects.create(
        owner=owner,
        source=Property.Source.WEB,
        status=Property.Status.PENDING,
        property_type=data["property_type"],
        title=data["title"].strip(),
        address=data["address"].strip(),
        neighborhood=data["neighborhood"].strip(),
        city=data["city"].strip(),
        rent=data["rent"],
        charges=data.get("charges", 0),
        deposit=data.get("deposit", 0),
        rooms_count=data.get("rooms_count", 1),
        description=data.get("description", "").strip(),
        entrance_photo=resize_upload(data["entrance_photo"]),
    )
    for admin in User.objects.filter(role=User.Role.ADMIN, status=User.Status.ACTIVE):
        notify(
            admin,
            "new_declaration",
            "Nouvelle déclaration de bien",
            f"{owner.get_full_name()} ({owner.email}) a déclaré « {prop.title} » à {prop.city}.",
            email=False,
        )
    return prop


class DeclarationView(APIView):
    """POST /api/declarations/ — entrée publique, sans authentification."""

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [DeclarationThrottle]

    @extend_schema(
        request=DeclarationSerializer,
        responses={201: {"type": "object", "properties": {"detail": {"type": "string"}}}},
        summary="Déclarer un bien (modération avant publication)",
    )
    def post(self, request):
        # Le robot remplit le champ caché : on répond comme si tout allait bien, sans rien créer.
        if str(request.data.get("website", "")).strip():
            return Response({"detail": ACKNOWLEDGEMENT}, status=status.HTTP_201_CREATED)

        serializer = DeclarationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop = create_web_declaration(serializer.validated_data)
        return Response(
            {
                "detail": ACKNOWLEDGEMENT,
                "dossier": f"ESS-{prop.pk:06d}",
                "status": Property.Status.PENDING,
            },
            status=status.HTTP_201_CREATED,
        )
