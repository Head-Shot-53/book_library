from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.exceptions import BookingValidationError
from apps.bookings.models import Booking
from apps.bookings.services import create_booking
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


def future_datetime(hour: int, minute: int = 0, *, days: int = 1):
    target_date = timezone.localdate() + timedelta(days=days)

    naive_datetime = datetime.combine(target_date, time(hour, minute))

    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@pytest.mark.django_db
def test_create_booking(user, resource):
    start_at = future_datetime(10)
    end_at = future_datetime(11)

    booking = create_booking(
        user=user,
        resource=resource,
        start_at=start_at,
        end_at=end_at,
        title="Team meeting",
        notes="Weekly planning.",
    )

    assert booking.user == user
    assert booking.resource == resource
    assert booking.start_at == start_at
    assert booking.end_at == end_at
    assert booking.title == "Team meeting"
    assert booking.notes == "Weekly planning."

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_create_booking_rejects_invalid_time_range(user, resource):
    start_at = future_datetime(11)
    end_at = future_datetime(10)

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=start_at,
            end_at=end_at,
            title="Invalid booking",
        )

    assert exc_info.value.code == "invalid_time_range"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_equal_start_and_end(user, resource):
    start_at = future_datetime(10)

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=start_at,
            end_at=start_at,
            title="Invalid booking",
        )

    assert exc_info.value.code == "invalid_time_range"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_past_start(user, resource):
    start_at = timezone.now() - timedelta(hours=2)
    end_at = timezone.now() - timedelta(hours=1)

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=start_at,
            end_at=end_at,
            title="Past booking",
        )

    assert exc_info.value.code == "booking_in_past"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_inactive_resource(user, resource):
    resource.is_active = False
    resource.save(update_fields=["is_active", "updated_at"])

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10),
            end_at=future_datetime(11),
            title="Team meeting",
        )

    assert exc_info.value.code == "resource_inactive"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_duration_below_minimum(user, resource):
    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10),
            end_at=future_datetime(10, 15),
            title="Short booking",
        )

    assert exc_info.value.code == "duration_too_short"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_allows_exact_minimum_duration(user, resource):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(10, 30),
        title="Minimum duration booking",
    )

    assert booking.pk is not None


@pytest.mark.django_db
def test_create_booking_rejects_duration_above_maximum(user, resource):
    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(10),
            end_at=future_datetime(15),
            title="Long booking",
        )

    assert exc_info.value.code == "duration_too_long"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_allows_exact_maximum_duration(user, resource):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(14),
        title="Maximum duration booking",
    )

    assert booking.pk is not None


@pytest.mark.django_db
def test_create_booking_rejects_start_before_working_hours(user, resource):
    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(7, 30),
            end_at=future_datetime(8, 30),
            title="Early booking",
        )

    assert exc_info.value.code == "outside_working_hours"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_end_after_working_hours(user, resource):
    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=future_datetime(19, 30),
            end_at=future_datetime(20, 30),
            title="Late booking",
        )

    assert exc_info.value.code == "outside_working_hours"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_allows_exact_opening_time(user, resource):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(8),
        end_at=future_datetime(9),
        title="Morning booking",
    )

    assert booking.pk is not None


@pytest.mark.django_db
def test_create_booking_allows_exact_closing_time(user, resource):
    booking = create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(19),
        end_at=future_datetime(20),
        title="Evening booking",
    )

    assert booking.pk is not None


@pytest.mark.django_db
def test_create_booking_rejects_naive_datetime(user, resource):
    start_at = datetime.combine(timezone.localdate() + timedelta(days=1), time(10))

    end_at = datetime.combine(timezone.localdate() + timedelta(days=1), time(11))

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=start_at,
            end_at=end_at,
            title="Naive datetime booking",
        )

    assert exc_info.value.code == "timezone_aware_required"
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_create_booking_rejects_cross_day_booking(user, resource):
    resource.booking_max_duration = timedelta(days=2)
    resource.available_from = time(0, 0)
    resource.available_to = time(23, 59, 59)

    resource.save(
        update_fields=[
            "booking_max_duration",
            "available_from",
            "available_to",
            "updated_at",
        ]
    )

    start_at = future_datetime(19)

    end_at = future_datetime(10, days=2)

    with pytest.raises(BookingValidationError) as exc_info:
        create_booking(
            user=user,
            resource=resource,
            start_at=start_at,
            end_at=end_at,
            title="Cross-day booking",
        )

    assert exc_info.value.code == "cross_day_booking"
    assert Booking.objects.count() == 0
