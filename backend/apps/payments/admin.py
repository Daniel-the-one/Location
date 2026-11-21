from django.contrib import admin

from .models import Lease, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "payer", "kind", "amount", "method", "status", "created_at"]
    list_filter = ["status", "method", "kind"]
    search_fields = ["reference", "payer__email"]


admin.site.register(Lease)
