from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.resources.models import Resource

from .exceptions import BookingConflictError, BookingValidationError
from .models import Booking, BookingStatus


def validate_booking_creation(
    *, resource: Resource, start_at: datetime, end_at: datetime
) -> None:
    _validate_timezone_awareness(start_at=start_at, end_at=end_at)

    _validate_time_range(start_at=start_at, end_at=end_at)

    _validate_not_in_past(start_at=start_at)

    _validate_resource_is_active(resource=resource)

    _validate_duration(resource=resource, start_at=start_at, end_at=end_at)

    _validate_working_hours(resource=resource, start_at=start_at, end_at=end_at)


def _validate_timezone_awareness(*, start_at: datetime, end_at: datetime) -> None:
    if timezone.is_naive(start_at) or timezone.is_naive(end_at):
        raise BookingValidationError(
            "Booking datetimes must be timezone-aware.", code="timezone_aware_required"
        )


def _validate_time_range(*, start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise BookingValidationError(
            "Booking end time must be after start time.", code="invalid_time_range"
        )


def _validate_not_in_past(*, start_at: datetime) -> None:
    if start_at < timezone.now():
        raise BookingValidationError(
            "Booking cannot be created in the past.", code="booking_in_past"
        )


def _validate_resource_is_active(*, resource: Resource) -> None:
    if not resource.is_active:
        raise BookingValidationError(
            "Inactive resources cannot be booked.", code="resource_inactive"
        )


def _validate_duration(
    *, resource: Resource, start_at: datetime, end_at: datetime
) -> None:
    duration = end_at - start_at

    if duration < resource.booking_min_duration:
        raise BookingValidationError(
            "Booking duration is shorter than the minimum allowed duration.",
            code="duration_too_short",
        )

    if duration > resource.booking_max_duration:
        raise BookingValidationError(
            "Booking duration exceeds the maximum allowed duration.",
            code="duration_too_long",
        )


def _validate_working_hours(
    *, resource: Resource, start_at: datetime, end_at: datetime
) -> None:
    start_local = timezone.localtime(start_at)
    end_local = timezone.localtime(end_at)

    if start_local.date() != end_local.date():
        raise BookingValidationError(
            "Booking must start and end on the same day.", code="cross_day_booking"
        )

    if (
        start_local.time() < resource.available_from
        or end_local.time() > resource.available_to
    ):
        raise BookingValidationError(
            "Booking must be within resource working hours.",
            code="outside_working_hours",
        )


@transaction.atomic
def create_booking(
    *,
    user,
    resource: Resource,
    start_at: datetime,
    end_at: datetime,
    title: str,
    notes: str = "",
) -> Booking:
    validate_booking_creation(resource=resource, start_at=start_at, end_at=end_at)

    _validate_no_booking_conflict(resource=resource, start_at=start_at, end_at=end_at)

    return Booking.objects.create(
        user=user,
        resource=resource,
        start_at=start_at,
        end_at=end_at,
        title=title,
        notes=notes,
    )


def check_booking_conflict(
    *,
    resource: Resource,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: int | None = None,
) -> bool:
    queryset = Booking.objects.filter(
        resource=resource, start_at__lt=end_at, end_at__gt=start_at
    ).exclude(
        status=BookingStatus.CANCELLED,
    )

    if exclude_booking_id is not None:
        queryset = queryset.exclude(pk=exclude_booking_id)

    return queryset.exists()


def _validate_no_booking_conflict(
    *,
    resource: Resource,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: int | None = None,
) -> None:

    if check_booking_conflict(
        resource=resource,
        start_at=start_at,
        end_at=end_at,
        exclude_booking_id=exclude_booking_id,
    ):
        raise BookingConflictError()
