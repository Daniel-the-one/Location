from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import IsOwner
from apps.common.images import resize_upload

from . import services
from .models import Property, Room, ViewHistory
from .serializers import (
    AddRoomSerializer,
    EntrancePhotoSerializer,
    OwnerPropertySerializer,
    OwnerRoomSerializer,
    PhotoUploadSerializer,
    PropertyDetailSerializer,
    PropertyListSerializer,
    ReorderRoomsSerializer,
    RoomPlanAnswersSerializer,
)

EDITABLE_PLAN = (Property.Status.DRAFT, Property.Status.REJECTED)


def business_error(exc: services.BusinessError) -> Response:
    return Response({"detail": exc.errors[0], "errors": exc.errors}, status=400)


# --- Public -----------------------------------------------------------------


@extend_schema(
    parameters=[
        OpenApiParameter("city", OpenApiTypes.STR),
        OpenApiParameter("neighborhood", OpenApiTypes.STR),
        OpenApiParameter("property_type", OpenApiTypes.STR),
        OpenApiParameter("min_rent", OpenApiTypes.INT),
        OpenApiParameter("max_rent", OpenApiTypes.INT),
        OpenApiParameter("min_rooms", OpenApiTypes.INT),
    ]
)
class PropertyViewSet(viewsets.ReadOnlyModelViewSet):
    """Annonces publiées, consultables sans compte."""

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        return PropertyListSerializer if self.action == "list" else PropertyDetailSerializer

    def get_queryset(self):
        qs = Property.objects.select_related("owner").prefetch_related("rooms__panorama")
        user = self.request.user
        if self.action == "retrieve" and user.is_authenticated:
            if user.is_platform_admin:
                return qs
            if user.is_owner:
                # Le propriétaire prévisualise aussi ses annonces non publiées.
                return qs.filter(Q(status=Property.Status.PUBLISHED) | Q(owner=user))
        qs = qs.filter(status=Property.Status.PUBLISHED)
        return self._filter(qs) if self.action == "list" else qs

    def _filter(self, qs):
        p = self.request.query_params
        if p.get("city"):
            qs = qs.filter(city__iexact=p["city"].strip())
        if p.get("neighborhood"):
            qs = qs.filter(neighborhood__icontains=p["neighborhood"].strip())
        if p.get("property_type"):
            qs = qs.filter(property_type=p["property_type"])
        for param, lookup in (("min_rent", "rent__gte"), ("max_rent", "rent__lte"),
                              ("min_rooms", "rooms_count__gte")):
            if p.get(param, "").isdigit():
                qs = qs.filter(**{lookup: int(p[param])})
        return qs

    def retrieve(self, request, *args, **kwargs):
        prop = self.get_object()
        if request.user.is_authenticated and request.user.is_tenant:
            ViewHistory.objects.create(user=request.user, property=prop)
        return Response(self.get_serializer(prop).data)


# --- Propriétaire -----------------------------------------------------------


class OwnerPropertyViewSet(viewsets.ModelViewSet):
    """Les biens du propriétaire connecté : création, assistant des pièces, soumission."""

    serializer_class = OwnerPropertySerializer
    permission_classes = [IsOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma Swagger
            return Property.objects.none()
        return Property.objects.filter(owner=self.request.user).prefetch_related(
            "rooms__photos", "rooms__panorama"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status=Property.Status.DRAFT)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Ce bien a des paiements enregistrés : suspendez-le plutôt."},
                status=status.HTTP_409_CONFLICT,
            )

    def _done(self, prop):
        prop.refresh_from_db()
        return Response(self.get_serializer(self.get_queryset().get(pk=prop.pk)).data)

    @extend_schema(request=RoomPlanAnswersSerializer, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"], url_path="room-plan")
    def room_plan(self, request, pk=None):
        """Construit la liste des pièces à partir des réponses de l'assistant."""
        prop = self.get_object()
        answers = RoomPlanAnswersSerializer(data=request.data)
        answers.is_valid(raise_exception=True)
        try:
            services.apply_room_plan(prop, answers.validated_data)
        except services.BusinessError as exc:
            return business_error(exc)
        return self._done(prop)

    @extend_schema(request=AddRoomSerializer, responses=OwnerRoomSerializer)
    @action(detail=True, methods=["post"])
    def rooms(self, request, pk=None):
        """Ajoute une pièce à la fin de la visite."""
        prop = self.get_object()
        if prop.status not in EDITABLE_PLAN:
            return Response({"detail": "Pièces modifiables seulement sur un brouillon."}, status=400)
        serializer = AddRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save(property=prop, order=prop.rooms.count())
        return Response(OwnerRoomSerializer(room, context={"request": request}).data, status=201)

    @extend_schema(request=ReorderRoomsSerializer, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"], url_path="reorder-rooms")
    def reorder_rooms(self, request, pk=None):
        prop = self.get_object()
        serializer = ReorderRoomsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.reorder_rooms(prop, serializer.validated_data["room_ids"])
        except services.BusinessError as exc:
            return business_error(exc)
        return self._done(prop)

    @extend_schema(request=EntrancePhotoSerializer, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"], url_path="entrance-photo",
            parser_classes=[MultiPartParser, FormParser])
    def entrance_photo(self, request, pk=None):
        prop = self.get_object()
        serializer = EntrancePhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop.entrance_photo = resize_upload(serializer.validated_data["image"])
        prop.save(update_fields=["entrance_photo", "updated_at"])
        return self._done(prop)

    @extend_schema(request=None, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Envoie l'annonce à l'administrateur pour validation."""
        return self._transition(services.submit_for_review)

    @extend_schema(request=None, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._transition(services.owner_suspend)

    @extend_schema(request=None, responses=OwnerPropertySerializer)
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        return self._transition(services.owner_reactivate)

    def _transition(self, func):
        prop = self.get_object()
        try:
            func(prop)
        except services.BusinessError as exc:
            return business_error(exc)
        return self._done(prop)


class OwnerRoomViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Une pièce d'un bien du propriétaire : renommer, supprimer, téléverser les photos."""

    serializer_class = OwnerRoomSerializer
    permission_classes = [IsOwner]
    http_method_names = ["patch", "post", "delete"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Room.objects.none()
        return Room.objects.filter(property__owner=self.request.user).select_related("property")

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        if room.property.status not in EDITABLE_PLAN:
            return Response({"detail": "Pièces modifiables seulement sur un brouillon."}, status=400)
        with transaction.atomic():
            prop = room.property
            room.delete()
            for order, r in enumerate(prop.rooms.order_by("order")):
                if r.order != order:
                    r.order = order
                    r.save(update_fields=["order"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=PhotoUploadSerializer, responses=OwnerRoomSerializer, methods=["POST"])
    @extend_schema(request=None, responses={204: None}, methods=["DELETE"])
    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        """POST : ajoute les photos de la pièce (réduites à 1 600 px). DELETE : les efface toutes."""
        room = self.get_object()
        if room.property.status == Property.Status.PENDING:
            return Response({"detail": "Annonce en cours de validation."}, status=400)
        if request.method == "DELETE":
            with transaction.atomic():
                room.photos.all().delete()
                if hasattr(room, "panorama"):
                    room.panorama.delete()
                room.panorama_status = Room.PanoramaStatus.NONE
                room.save(update_fields=["panorama_status"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = [resize_upload(f) for f in serializer.validated_data["images"]]
        try:
            services.add_photos(room, files)
        except services.BusinessError as exc:
            return business_error(exc)
        room = get_object_or_404(self.get_queryset().prefetch_related("photos"), pk=room.pk)
        return Response(OwnerRoomSerializer(room, context={"request": request}).data, status=201)
