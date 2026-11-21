from django.contrib import admin

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


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "property", "room_type", "order", "panorama_status"]
    list_filter = ["panorama_status", "room_type"]


admin.site.register([RoomPhoto, Panorama, Favorite, ViewHistory])
