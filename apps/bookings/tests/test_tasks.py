from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.audit.models import BookingHistory, BookingHistoryAction
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.tasks import celery_health_check, complete_expired_bookings
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!"
    )


@pytest.fixture
def resource():
    category = ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")

    return Resource.objects.create(
        name="Room A",
        slug="room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from="08:00",
        available_to="20:00",
    )


def test_celery_health_check():
    result = celery_health_check.run()

    assert result == {"status": "ok"}


@pytest.mark.django_db
def test_expired_confirmed_booking_is_completed(user, resource):
    now = timezone.now()

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        title="Finished meeting",
        status=BookingStatus.CONFIRMED,
    )

    result = complete_expired_bookings.run()

    booking.refresh_from_db()

    history = BookingHistory.objects.get(
        booking=booking, action=BookingHistoryAction.COMPLETED
    )

    assert history.changed_by is None

    assert history.old_data["status"] == BookingStatus.CONFIRMED

    assert history.new_data["status"] == BookingStatus.COMPLETED

    assert booking.status == BookingStatus.COMPLETED

    assert result["processed"] == 1
    assert result["completed"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0


@pytest.mark.django_db
def test_future_booking_is_not_completed(user, resource):
    now = timezone.now()

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        title="Future meeting",
        status=BookingStatus.CONFIRMED,
    )

    result = complete_expired_bookings.run()

    booking.refresh_from_db()

    assert booking.status == BookingStatus.CONFIRMED

    assert result["processed"] == 0
    assert result["completed"] == 0


@pytest.mark.django_db
def test_cancelled_expired_booking_is_not_completed(user, resource):
    now = timezone.now()

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        title="Cancelled meeting",
        status=BookingStatus.CANCELLED,
        cancelled_at=now - timedelta(hours=1),
    )

    result = complete_expired_bookings.run()

    booking.refresh_from_db()

    assert booking.status == BookingStatus.CANCELLED

    assert result["processed"] == 0


@pytest.mark.django_db
def test_completed_booking_is_not_processed_again(user, resource):
    now = timezone.now()

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        title="Completed meeting",
        status=BookingStatus.COMPLETED,
    )

    result = complete_expired_bookings.run()

    assert result["processed"] == 0
    assert result["completed"] == 0

    assert not BookingHistory.objects.filter(
        booking=booking,
        action=BookingHistoryAction.COMPLETED,
    ).exists()


@pytest.mark.django_db
def test_multiple_expired_bookings_are_completed(user, resource):
    now = timezone.now()

    bookings = []

    for index in range(3):
        bookings.append(
            Booking.objects.create(
                user=user,
                resource=resource,
                start_at=(now - timedelta(hours=3 + index)),
                end_at=(now - timedelta(hours=2 + index)),
                title=f"Meeting {index}",
                status=BookingStatus.CONFIRMED,
            )
        )

    result = complete_expired_bookings.run()

    assert result == {"processed": 3, "completed": 3, "skipped": 0, "failed": 0}

    assert Booking.objects.filter(status=BookingStatus.COMPLETED).count() == 3


@pytest.mark.django_db
def test_completion_task_is_idempotent(user, resource):
    now = timezone.now()

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        title="Meeting",
        status=BookingStatus.CONFIRMED,
    )

    first_result = complete_expired_bookings.run()

    second_result = complete_expired_bookings.run()

    booking.refresh_from_db()

    assert booking.status == BookingStatus.COMPLETED

    assert first_result["completed"] == 1
    assert second_result["completed"] == 0

    assert (
        BookingHistory.objects.filter(
            booking=booking, action=BookingHistoryAction.COMPLETED
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_completion_respects_batch_size(
    user,
    resource,
):
    now = timezone.now()

    for index in range(5):
        Booking.objects.create(
            user=user,
            resource=resource,
            start_at=(
                now
                - timedelta(
                    hours=3 + index,
                )
            ),
            end_at=(
                now
                - timedelta(
                    hours=2 + index,
                )
            ),
            title=f"Booking {index}",
            status=BookingStatus.CONFIRMED,
        )

    result = complete_expired_bookings.run(batch_size=2)

    assert result["processed"] == 2
    assert result["completed"] == 2

    assert Booking.objects.filter(status=BookingStatus.CONFIRMED).count() == 3
