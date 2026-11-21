from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html

from . import services
from .models import IdentityVerification, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "status", "date_joined"]
    list_filter = ["role", "status", "is_staff"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    actions = ["activate", "suspend", "block"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("first_name", "last_name", "phone", "photo", "language")}),
        ("Rôle et statut", {"fields": ("role", "status")}),
        ("Droits Django", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "role", "password1", "password2")}),
    )

    def _set_status(self, request, queryset, status):
        count = queryset.exclude(pk=request.user.pk).update(status=status)
        self.message_user(request, f"{count} compte(s) mis à jour.")

    @admin.action(description="Réactiver les comptes")
    def activate(self, request, queryset):
        self._set_status(request, queryset, User.Status.ACTIVE)

    @admin.action(description="Suspendre les comptes")
    def suspend(self, request, queryset):
        self._set_status(request, queryset, User.Status.SUSPENDED)

    @admin.action(description="Bloquer les comptes")
    def block(self, request, queryset):
        self._set_status(request, queryset, User.Status.BLOCKED)


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "document_link", "created_at", "reviewed_by"]
    list_filter = ["status"]
    readonly_fields = ["user", "document_link", "reviewed_by", "reviewed_at", "created_at"]
    exclude = ["document"]
    actions = ["approve", "reject"]

    @admin.display(description="Pièce")
    def document_link(self, obj):
        url = reverse("identity-document", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Voir la pièce</a>', url)

    @admin.action(description="Valider les pièces sélectionnées")
    def approve(self, request, queryset):
        for verification in queryset.select_related("user"):
            services.approve_identity(verification, request.user)
        self.message_user(request, "Pièce(s) validée(s), propriétaire(s) prévenu(s) par email.")

    @admin.action(description="Refuser (motif : document illisible ou non conforme)")
    def reject(self, request, queryset):
        for verification in queryset.select_related("user"):
            services.reject_identity(
                verification, request.user, "Document illisible ou non conforme."
            )
        self.message_user(request, "Pièce(s) refusée(s).", messages.WARNING)
