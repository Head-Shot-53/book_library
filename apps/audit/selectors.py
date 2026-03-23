from django.db.models import QuerySet

from .models import BookingHistory


def get_booking_history(*, booking) -> QuerySet[BookingHistory]:
    return (
        BookingHistory.objects.filter(booking=booking)
        .select_related("changed_by")
        .order_by("-created_at", "-id")
    )
