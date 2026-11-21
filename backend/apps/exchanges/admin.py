from django.contrib import admin

from .models import Conversation, Message, Notification, RentalRequest, Report, VisitAppointment


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["reason", "author", "target_property", "target_user", "status", "created_at"]
    list_filter = ["status"]


@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = ["property", "tenant", "status", "created_at"]
    list_filter = ["status"]


admin.site.register([Conversation, Message, Notification, VisitAppointment])
