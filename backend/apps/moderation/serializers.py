"""Représentations lisibles par la console admin, sans exposer de fichier privé."""
from rest_framework import serializers

from apps.accounts.models import IdentityVerification
from apps.properties.models import Property
from apps.properties.serializers import RoomSerializer


class AdminPropertySerializer(serializers.ModelSerializer):
    dossier = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_phone = serializers.CharField(source="owner.phone", read_only=True)
    identity_status = serializers.SerializerMethodField()
    identity_id = serializers.SerializerMethodField()
    entrance_photo_url = serializers.SerializerMethodField()
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "dossier",
            "source",
            "status",
            "property_type",
            "title",
            "description",
            "address",
            "neighborhood",
            "city",
            "rent",
            "charges",
            "deposit",
            "rooms_count",
            "owner_email",
            "owner_name",
            "owner_phone",
            "identity_status",
            "identity_id",
            "entrance_photo_url",
            "rejection_reason",
            "suspended_by_admin",
            "is_available",
            "rooms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_dossier(self, obj) -> str:
        return f"ESS-{obj.pk:06d}"

    def get_owner_name(self, obj) -> str:
        return (obj.owner.get_full_name() or obj.owner.email).strip()

    def _identity(self, obj):
        identities = getattr(obj.owner, "admin_identities", None)
        if identities is None:
            identities = list(obj.owner.identity_verifications.all()[:1])
        return identities[0] if identities else None

    def get_identity_status(self, obj):
        identity = self._identity(obj)
        return identity.status if identity else None

    def get_identity_id(self, obj):
        identity = self._identity(obj)
        return identity.pk if identity else None

    def get_entrance_photo_url(self, obj):
        request = self.context.get("request")
        if not obj.entrance_photo or not request:
            return None
        return request.build_absolute_uri(obj.entrance_photo.url)


class AdminIdentitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = IdentityVerification
        fields = [
            "id",
            "user_email",
            "user_name",
            "user_phone",
            "status",
            "document_url",
            "rejection_reason",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj) -> str:
        return (obj.user.get_full_name() or obj.user.email).strip()

    def get_document_url(self, obj):
        request = self.context.get("request")
        if not obj.document or not request:
            return None
        return request.build_absolute_uri(f"/api/admin/identities/{obj.pk}/document/")


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, min_length=5)


class OptionalReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
