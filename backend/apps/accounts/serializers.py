from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import IdentityVerification, User


class UserSerializer(serializers.ModelSerializer):
    is_identity_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "photo",
            "role",
            "status",
            "language",
            "is_identity_verified",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "status", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    role = serializers.ChoiceField(choices=[User.Role.TENANT, User.Role.OWNER])

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role", "language"]
        extra_kwargs = {"first_name": {"required": True}, "last_name": {"required": True}}

    def validate_email(self, value):
        value = value.lower()
        # Le validateur d'unicité de DRF compare avant la mise en minuscules : on revérifie ici.
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value

    def validate(self, attrs):
        candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
        password_validation.validate_password(attrs["password"], candidate)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Connexion par email ; refuse les comptes suspendus ou bloqués."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].lower()
        data = super().validate(attrs)
        if self.user.status != User.Status.ACTIVE:
            raise serializers.ValidationError(
                {"detail": f"Compte {self.user.get_status_display().lower()}."},
                code="account_inactive",
            )
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            pk = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=pk)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Lien invalide."})
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Lien invalide ou expiré."})
        password_validation.validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs


class IdentityVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityVerification
        fields = ["id", "document", "status", "rejection_reason", "created_at", "reviewed_at"]
        read_only_fields = ["id", "status", "rejection_reason", "created_at", "reviewed_at"]
        # write_only via extra_kwargs pour garder les validateurs du modèle (type, taille).
        extra_kwargs = {"document": {"write_only": True}}
