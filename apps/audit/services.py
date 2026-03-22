from .models import BookingHistory


def get_booking_snapshot(booking) -> dict:
    return {
        "user_id": booking.user_id,
        "resource_id": booking.resource_id,
        "start_at": booking.start_at.isoformat(),
        "end_at": booking.end_at.isoformat(),
        "status": booking.status,
        "title": booking.title,
        "notes": booking.notes,
        "cancelled_at": (
            booking.cancelled_at.isoformat() if booking.cancelled_at else None
        ),
    }


def record_booking_history(
    *,
    booking,
    action: str,
    changed_by=None,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> BookingHistory:
    return BookingHistory.objects.create(
        booking=booking,
        changed_by=changed_by,
        action=action,
        old_data=old_data or {},
        new_data=new_data or {},
    )
