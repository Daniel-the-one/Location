from rest_framework import serializers

from apps.common.validators import validate_file_size, validate_image_extension

from .models import Panorama, Property, Room, RoomPhoto
from .room_plan import EXTERIOR, INTERIOR, NONE, WITH_BATHROOM
from .services import MAX_PHOTOS_PER_ROOM

IMAGE_VALIDATORS = [validate_image_extension, validate_file_size]


class RoomPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPhoto
        fields = ["id", "image", "order"]


class PanoramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Panorama
        fields = ["source", "status", "image_thumb", "image_medium", "image_high"]


class RoomSerializer(serializers.ModelSerializer):
    photos_count = serializers.IntegerField(source="photos.count", read_only=True)
    panorama = PanoramaSerializer(read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "room_type",
            "name",
            "is_exterior",
            "order",
            "panorama_status",
            "photos_count",
            "panorama",
        ]
        read_only_fields = ["id", "order", "panorama_status"]


class OwnerRoomSerializer(RoomSerializer):
    photos = RoomPhotoSerializer(many=True, read_only=True)

    class Meta(RoomSerializer.Meta):
        fields = RoomSerializer.Meta.fields + ["photos"]


PROPERTY_FIELDS = [
    "id",
    "property_type",
    "title",
    "description",
    "address",
    "neighborhood",
    "city",
    "latitude",
    "longitude",
    "rent",
    "charges",
    "deposit",
    "visit_fee",
    "rooms_count",
    "amenities",
    "rules",
    "available_from",
    "is_available",
    "entrance_photo",
]


class OwnerPropertySerializer(serializers.ModelSerializer):
    rooms = OwnerRoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = PROPERTY_FIELDS + [
            "status",
            "rejection_reason",
            "suspended_by_admin",
            "rooms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "entrance_photo",
            "status",
            "rejection_reason",
            "suspended_by_admin",
            "created_at",
            "updated_at",
        ]

    def validate_amenities(self, value):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("Liste de textes attendue.")
        return [v.strip() for v in value if v.strip()][:30]


class PublicOwnerSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    phone = serializers.SerializerMethodField()

    def get_phone(self, user) -> str | None:
        # Le numéro (appel, WhatsApp) n'est montré qu'aux personnes connectées.
        request = self.context.get("request")
        return user.phone if request and request.user.is_authenticated else None


class PropertyListSerializer(serializers.ModelSerializer):
    has_virtual_tour = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "property_type",
            "title",
            "neighborhood",
            "city",
            "latitude",
            "longitude",
            "rent",
            "rooms_count",
            "entrance_photo",
            "is_available",
            "has_virtual_tour",
        ]

    def get_has_virtual_tour(self, obj) -> bool:
        return any(r.panorama_status == Room.PanoramaStatus.READY for r in obj.rooms.all())


class PropertyDetailSerializer(serializers.ModelSerializer):
    owner = PublicOwnerSerializer(read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = PROPERTY_FIELDS + ["owner", "rooms", "created_at"]


class RoomPlanAnswersSerializer(serializers.Serializer):
    """Réponses aux questions de l'assistant de création."""

    bedrooms = serializers.IntegerField(min_value=0, max_value=10)
    living_room = serializers.BooleanField()
    kitchen = serializers.ChoiceField(choices=[INTERIOR, EXTERIOR, NONE])
    bathroom = serializers.ChoiceField(choices=[INTERIOR, EXTERIOR, NONE])
    toilet = serializers.ChoiceField(choices=[INTERIOR, EXTERIOR, WITH_BATHROOM, NONE])
    balcony = serializers.BooleanField(default=False)
    terrace = serializers.BooleanField(default=False)
    yard = serializers.BooleanField(default=False)
    others = serializers.ListField(
        child=serializers.CharField(max_length=60), max_length=5, default=list
    )

    def validate(self, attrs):
        if attrs["toilet"] == WITH_BATHROOM and attrs["bathroom"] == NONE:
            raise serializers.ValidationError({"toilet": "Il n'y a pas de douche à associer."})
        return attrs


class ReorderRoomsSerializer(serializers.Serializer):
    room_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class AddRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["room_type", "name", "is_exterior"]


class PhotoUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(validators=IMAGE_VALIDATORS),
        allow_empty=False,
        max_length=MAX_PHOTOS_PER_ROOM,
    )


class EntrancePhotoSerializer(serializers.Serializer):
    image = serializers.ImageField(validators=IMAGE_VALIDATORS)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
