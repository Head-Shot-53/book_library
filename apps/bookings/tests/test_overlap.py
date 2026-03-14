from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.exceptions import BookingConflictError
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import check_booking_conflict, create_booking
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!"
    )


@pytest.fixture
def category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.fixture
def resource(category):
    return Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        capacity=12,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )


def future_datetime(hour: int, minute: int = 0):
    target_date = timezone.localdate() + timedelta(days=1)

    naive_datetime = datetime.combine(target_date, time(hour, minute))

    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@pytest.fixture
def existing_booking(user, resource):
    return Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Existing booking",
    )


@pytest.mark.django_db
def test_exact_overlap_is_rejected(user, resource, existing_booking):
    with pytest.raises(BookingConflictError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10),
            end_at=future_datetime(11),
            title="Conflicting booking",
        )

    assert exc_info.value.code == "booking_conflict"
    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_partial_overlap_on_right_is_rejected(user, resource, existing_booking):
    with pytest.raises(BookingConflictError):
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10, 30),
            end_at=future_datetime(11, 30),
            title="Conflicting booking",
        )

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_partial_overlap_on_left_is_rejected(user, resource, existing_booking):
    with pytest.raises(BookingConflictError):
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(9, 30),
            end_at=future_datetime(10, 30),
            title="Conflicting booking",
        )

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_booking_inside_existing_booking_is_rejected(user, resource, existing_booking):
    with pytest.raises(BookingConflictError):
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10, 15),
            end_at=future_datetime(10, 45),
            title="Conflicting booking",
        )

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_booking_around_existing_booking_is_rejected(user, resource, existing_booking):
    with pytest.raises(BookingConflictError):
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(9),
            end_at=future_datetime(12),
            title="Conflicting booking",
        )

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_booking_starting_when_existing_ends_is_allowed(
    user, resource, existing_booking
):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(11),
        end_at=future_datetime(12),
        title="Next booking",
    )

    assert booking.pk is not None
    assert Booking.objects.count() == 2


@pytest.mark.django_db
def test_booking_ending_when_existing_starts_is_allowed(
    user, resource, existing_booking
):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(9),
        end_at=future_datetime(10),
        title="Previous booking",
    )

    assert booking.pk is not None
    assert Booking.objects.count() == 2


@pytest.mark.django_db
def test_cancelled_booking_does_not_create_conflict(user, resource, existing_booking):
    existing_booking.status = BookingStatus.CANCELLED
    existing_booking.cancelled_at = timezone.now()

    existing_booking.save(update_fields=["status", "cancelled_at", "updated_at"])

    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Replacement booking",
    )

    assert booking.pk is not None
    assert Booking.objects.count() == 2


@pytest.mark.django_db
def test_same_time_on_different_resource_is_allowed(
    user, category, resource, existing_booking
):
    second_resource = Resource.objects.create(
        name="Conference Room B",
        slug="conference-room-b",
        category=category,
        location="Building A",
        capacity=8,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    booking = create_booking(
        user=user,
        resource=second_resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Another room meeting",
    )

    assert booking.pk is not None
    assert booking.resource == second_resource
    assert Booking.objects.count() == 2


@pytest.mark.django_db
def test_check_booking_conflict_returns_true_for_overlap(resource, existing_booking):
    has_conflict = check_booking_conflict(
        resource=resource,
        start_at=future_datetime(10, 30),
        end_at=future_datetime(11, 30),
    )

    assert has_conflict is True


@pytest.mark.django_db
def test_check_booking_conflict_returns_false_without_overlap(
    resource, existing_booking
):
    has_conflict = check_booking_conflict(
        resource=resource, start_at=future_datetime(11), end_at=future_datetime(12)
    )

    assert has_conflict is False


@pytest.mark.django_db
def test_check_booking_conflict_can_exclude_booking(resource, existing_booking):
    has_conflict = check_booking_conflict(
        resource=resource,
        start_at=existing_booking.start_at,
        end_at=existing_booking.end_at,
        exclude_booking_id=existing_booking.id,
    )

    assert has_conflict is False
