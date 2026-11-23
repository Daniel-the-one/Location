"""API de modération réservée au développeur/admin.

Toutes les décisions passent par les services métier existants : les règles de statut
et les notifications restent les mêmes que dans /django-admin/ et dans l'application.
"""
import os

from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services as account_services
from apps.accounts.models import IdentityVerification
from apps.accounts.permissions import IsPlatformAdmin
from apps.properties import services as property_services
from apps.properties.models import Property

from .serializers import (
    AdminIdentitySerializer,
    AdminPropertySerializer,
    OptionalReasonSerializer,
    ReasonSerializer,
)

S = Property.Status
V = IdentityVerification.Status
SAFE_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def properties_with_identities():
    """Une seule requête pour la liste + dernière pièce d'identité de chaque propriétaire."""
    return Property.objects.select_related("owner").prefetch_related(
        "rooms__panorama",
        Prefetch(
            "owner__identity_verifications",
            queryset=IdentityVerification.objects.order_by("-created_at"),
            to_attr="admin_identities",
        ),
    )


def service_error(exc: property_services.BusinessError) -> Response:
    return Response({"detail": exc.errors[0], "errors": exc.errors}, status=400)


def latest_identity(owner) -> IdentityVerification | None:
    identities = getattr(owner, "admin_identities", None)
    if identities is None:
        identities = list(owner.identity_verifications.all()[:1])
    return identities[0] if identities else None


class AdminOverviewView(APIView):
    """Compteurs et dernières déclarations pour l'écran d'accueil de la console."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        props = Property.objects
        identities = IdentityVerification.objects
        recent = properties_with_identities().filter(
            status=S.PENDING, source=Property.Source.WEB
        )[:5]
        return Response(
            {
                "properties": {
                    "pending": props.filter(status=S.PENDING).count(),
                    "published": props.filter(status=S.PUBLISHED).count(),
                    "suspended": props.filter(status=S.SUSPENDED).count(),
                    "rejected": props.filter(status=S.REJECTED).count(),
                    "total": props.count(),
                },
                "identities": {
                    "pending": identities.filter(status=V.PENDING).count(),
                    "approved": identities.filter(status=V.APPROVED).count(),
                    "rejected": identities.filter(status=V.REJECTED).count(),
                },
                "web_declarations": props.filter(source=Property.Source.WEB).count(),
                "recent": AdminPropertySerializer(
                    recent, many=True, context={"request": request}
                ).data,
            }
        )


class AdminPropertyViewSet(viewsets.ReadOnlyModelViewSet):
    """Biens en attente de décision ou déjà traités."""

    serializer_class = AdminPropertySerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        qs = properties_with_identities()
        wanted = self.request.query_params.get("status", "").strip()
        if wanted in S.values:
            qs = qs.filter(status=wanted)
        source = self.request.query_params.get("source", "").strip()
        if source in Property.Source.values:
            qs = qs.filter(source=source)
        return qs

    @extend_schema(request=None, responses=AdminPropertySerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        prop = self.get_object()
        if prop.source == Property.Source.WEB:
            identity = latest_identity(prop.owner)
            if not identity or identity.status != V.APPROVED:
                return Response(
                    {
                        "detail": (
                            "Validez d'abord la pièce d'identité du propriétaire "
                            "avant de publier cette déclaration."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        try:
            property_services.approve_property(prop)
        except property_services.BusinessError as exc:
            return service_error(exc)
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=ReasonSerializer, responses=AdminPropertySerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop = self.get_object()
        try:
            property_services.reject_property(prop, serializer.validated_data["reason"].strip())
        except property_services.BusinessError as exc:
            return service_error(exc)
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=OptionalReasonSerializer, responses=AdminPropertySerializer)
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        serializer = OptionalReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop = self.get_object()
        property_services.admin_suspend_property(
            prop, serializer.validated_data.get("reason", "").strip()
        )
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=None, responses=AdminPropertySerializer)
    @action(detail=True, methods=["post"], url_path="unsuspend")
    def unsuspend(self, request, pk=None):
        prop = self.get_object()
        try:
            property_services.admin_unsuspend_property(prop)
        except property_services.BusinessError as exc:
            return service_error(exc)
        return Response(self.get_serializer(self.get_object()).data)


class AdminIdentityViewSet(viewsets.ReadOnlyModelViewSet):
    """Pièces d'identité : décision et consultation dans un isolateur sûr."""

    serializer_class = AdminIdentitySerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        qs = IdentityVerification.objects.select_related("user")
        wanted = self.request.query_params.get("status", "").strip()
        if wanted in V.values:
            qs = qs.filter(status=wanted)
        return qs

    @extend_schema(request=None, responses=AdminIdentitySerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        verification = self.get_object()
        account_services.approve_identity(verification, request.user)
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=ReasonSerializer, responses=AdminIdentitySerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = self.get_object()
        account_services.reject_identity(
            verification, request.user, serializer.validated_data["reason"].strip()
        )
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(responses={200: None, 404: None})
    @action(detail=True, methods=["get"])
    def document(self, request, pk=None):
        """Le seul accès HTTP à un document privé : type imposé, jamais deviné."""
        verification = get_object_or_404(IdentityVerification, pk=pk)
        if not verification.document:
            raise Http404
        extension = os.path.splitext(verification.document.name)[1].lower()
        content_type = SAFE_TYPES.get(extension)
        if content_type is None:
            raise Http404
        response = FileResponse(verification.document.open("rb"), content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = (
            "sandbox; default-src 'none'; img-src 'self'; object-src 'self'"
        )
        return response
