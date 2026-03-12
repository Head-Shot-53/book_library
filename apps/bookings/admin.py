from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "resource", "user", "start_at", "end_at", "status")
    list_filter = ("status", "resource")
    search_fields = ("title", "user__email", "resource__name")
    ordering = ("-start_at",)
    list_select_related = ("user", "resource")
    readonly_fields = ("created_at", "updated_at", "cancelled_at")
