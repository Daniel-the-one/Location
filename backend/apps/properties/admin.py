from django.contrib import admin, messages

from . import services
from .models import Favorite, Panorama, Property, Room, RoomPhoto, ViewHistory


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "city", "neighborhood", "rent", "status", "created_at"]
    list_filter = ["status", "property_type", "city"]
    search_fields = ["title", "address", "neighborhood", "owner__email"]
    inlines = [RoomInline]
    actions = ["approve", "reject", "suspend", "unsuspend"]

    def _apply(self, request, queryset, func, *args):
        done, errors = 0, []
        for prop in queryset.select_related("owner"):
            try:
                func(prop, *args)
                done += 1
            except services.BusinessError as exc:
                errors.append(f"{prop.title} : {exc}")
        if done:
            self.message_user(request, f"{done} annonce(s) mise(s) à jour.")
        for error in errors:
            self.message_user(request, error, messages.ERROR)

    @admin.action(description="Valider et publier")
    def approve(self, request, queryset):
        self._apply(request, queryset, services.approve_property)

    @admin.action(description="Refuser (motif : informations ou photos insuffisantes)")
    def reject(self, request, queryset):
        self._apply(
            request, queryset, services.reject_property, "Informations ou photos insuffisantes."
        )

    @admin.action(description="Suspendre (modération)")
    def suspend(self, request, queryset):
        self._apply(request, queryset, services.admin_suspend_property)

    @admin.action(description="Lever la suspension")
    def unsuspend(self, request, queryset):
        self._apply(request, queryset, services.admin_unsuspend_property)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "property", "room_type", "order", "panorama_status"]
    list_filter = ["panorama_status", "room_type"]


admin.site.register([RoomPhoto, Panorama, Favorite, ViewHistory])
