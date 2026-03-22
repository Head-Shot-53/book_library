from django.conf import settings
from django.db import models

from apps.bookings.models import Booking


class BookingHistoryAction(models.TextChoices):
    CREATED = "CREATED", "Created"
    UPDATED = "UPDATED", "Updated"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


class BookingHistory(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, related_name="history"
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="booking_history_entries",
        null=True,
        blank=True,
    )

    action = models.CharField(max_length=20, choices=BookingHistoryAction.choices)

    old_data = models.JSONField(default=dict, blank=True)

    new_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

        indexes = [
            models.Index(
                fields=("booking", "-created_at"), name="bh_booking_created_idx"
            )
        ]

    def __str__(self):
        return f"Booking #{self.booking_id} - {self.action}"
