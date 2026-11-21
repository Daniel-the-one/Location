"""Droits par rôle, réutilisés par toutes les apps."""
from rest_framework.permissions import BasePermission


class IsTenant(BasePermission):
    message = "Réservé aux locataires."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_tenant)


class IsOwner(BasePermission):
    message = "Réservé aux propriétaires."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_owner)


class IsVerifiedOwner(IsOwner):
    message = "Votre identité doit être validée par l'administrateur."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_identity_verified


class IsPlatformAdmin(BasePermission):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_platform_admin
        )
