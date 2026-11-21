from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import IdentityVerification, User
from .permissions import IsOwner
from .serializers import (
    IdentityVerificationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RegisterView(generics.CreateAPIView):
    """Inscription d'un locataire ou d'un propriétaire. Renvoie directement les jetons."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        body = {"user": UserSerializer(user, context={"request": request}).data, **tokens_for(user)}
        return Response(body, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(APIView):
    """Envoie un lien de réinitialisation. Répond pareil que l'email existe ou non."""

    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = User.objects.filter(email=email, status=User.Status.ACTIVE).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Réinitialisation de votre mot de passe",
                message=(
                    "Bonjour,\n\nPour choisir un nouveau mot de passe, ouvrez ce lien :\n"
                    f"{link}\n\nSi vous n'êtes pas à l'origine de cette demande, ignorez ce message."
                ),
                from_email=None,
                recipient_list=[user.email],
            )
        return Response({"detail": "Si ce compte existe, un email a été envoyé."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Mot de passe modifié."})


class IdentityVerificationView(generics.ListCreateAPIView):
    """Le propriétaire téléverse sa pièce d'identité et suit son statut."""

    serializer_class = IdentityVerificationSerializer
    permission_classes = [IsOwner]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = None

    def get_queryset(self):
        return IdentityVerification.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        blocking = self.get_queryset().filter(
            status__in=[IdentityVerification.Status.PENDING, IdentityVerification.Status.APPROVED]
        )
        if blocking.exists():
            return Response(
                {"detail": "Une pièce est déjà en attente ou validée."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
