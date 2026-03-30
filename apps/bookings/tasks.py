import logging

from celery import shared_task
from django.utils import timezone

from .exceptions import BookingStateError
from .models import Booking
from .selectors import get_expired_confirmed_booking_ids
from .services import complete_booking

logger = logging.getLogger("booking_management.booking")


@shared_task(name="bookings.celery_health_check")
def celery_health_check() -> dict[str, str]:
    return {"status": "ok"}


@shared_task(bind=True, name="bookings.complete_expired_bookings")
def complete_expired_bookings(self, batch_size: int = 100) -> dict[str, int]:
    current_time = timezone.now()

    booking_ids = get_expired_confirmed_booking_ids(
        current_time=current_time, limit=batch_size
    )

    completed_count = 0
    skipped_count = 0
    failed_count = 0

    for booking_id in booking_ids:
        try:
            booking = Booking.objects.get(pk=booking_id)

            complete_booking(booking=booking, changed_by=None)

            completed_count += 1

        except Booking.DoesNotExist:
            skipped_count += 1

        except BookingStateError as exc:
            skipped_count += 1

            logger.info(
                "automatic_booking_completion_skipped",
                extra={
                    "task_id": self.request.id,
                    "booking_id": booking_id,
                    "error_code": exc.code,
                },
            )

        except Exception:
            failed_count += 1

            logger.exception(
                "automatic_booking_completion_failed",
                extra={"task_id": self.request.id, "booking_id": booking_id},
            )

    logger.info(
        "expired_bookings_processed",
        extra={
            "task_id": self.request.id,
            "processed_count": len(booking_ids),
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
        },
    )

    return {
        "processed": len(booking_ids),
        "completed": completed_count,
        "skipped": skipped_count,
        "failed": failed_count,
    }
