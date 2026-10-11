
from django.contrib import admin

from .models import ConsultationSession, SessionBilling


@admin.register(ConsultationSession)
class ConsultationSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "provider",
        "status",
        "price_per_minute",
        "billed_minutes",
        "total_amount",
    )
    list_filter = ("status",)
    search_fields = ("user__username", "provider__username")


@admin.register(SessionBilling)
class SessionBillingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "minute_number",
        "amount",
        "billed_at",
    )
    list_filter = ("billed_at",)
