from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


class ActiveStatusJWTAuthentication(JWTAuthentication):
    """Un jeton encore valide ne doit plus marcher une fois le compte suspendu ou bloqué."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("Ce compte est suspendu ou bloqué.", code="account_inactive")
        return user
