from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.bookings.models import Booking, BookingStatus
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!"
    )


@pytest.fixture
def resource():
    category = ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")

    return Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8),
        available_to=time(20),
    )


def datetime_for_date(target_date, hour, minute=0):
    naive_datetime = datetime.combine(target_date, time(hour, minute))

    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@pytest.mark.django_db
def test_availability_returns_full_working_day_when_free(api_client, user, resource):
    api_client.force_authenticate(user=user)

    target_date = timezone.localdate() + timedelta(days=1)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": target_date.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["busy_slots"] == []

    assert len(response.data["available_slots"]) == 1


@pytest.mark.django_db
def test_availability_splits_free_time_around_booking(api_client, user, resource):
    target_date = timezone.localdate() + timedelta(days=1)

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 10),
        end_at=datetime_for_date(target_date, 11),
        title="Meeting",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse(
            "resources:resource-availability",
            args=[resource.id],
        ),
        {"date": target_date.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK

    assert len(response.data["busy_slots"]) == 1
    assert len(response.data["available_slots"]) == 2


@pytest.mark.django_db
def test_cancelled_booking_does_not_block_availability(api_client, user, resource):
    target_date = timezone.localdate() + timedelta(days=1)

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 10),
        end_at=datetime_for_date(target_date, 11),
        title="Cancelled meeting",
        status=BookingStatus.CANCELLED,
        cancelled_at=timezone.now(),
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": target_date.isoformat()},
    )

    assert response.data["busy_slots"] == []
    assert len(response.data["available_slots"]) == 1


@pytest.mark.django_db
def test_adjacent_busy_slots_are_merged(api_client, user, resource):
    target_date = timezone.localdate() + timedelta(days=1)

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 10),
        end_at=datetime_for_date(target_date, 11),
        title="Meeting A",
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 11),
        end_at=datetime_for_date(target_date, 12),
        title="Meeting B",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": target_date.isoformat()},
    )

    assert len(response.data["busy_slots"]) == 1


@pytest.mark.django_db
def test_availability_hides_gap_shorter_than_min_duration(api_client, user, resource):
    target_date = timezone.localdate() + timedelta(days=1)

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 8),
        end_at=datetime_for_date(target_date, 10),
        title="Booking A",
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=datetime_for_date(target_date, 10, 20),
        end_at=datetime_for_date(target_date, 12),
        title="Booking B",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": target_date.isoformat()},
    )

    available_slots = response.data["available_slots"]

    assert len(available_slots) == 1

    assert available_slots[0]["start_at"].endswith("12:00:00+00:00")


@pytest.mark.django_db
def test_availability_requires_valid_date(api_client, user, resource):
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": "invalid-date"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_availability_requires_date(api_client, user, resource):
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id])
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_user_cannot_check_inactive_resource_availability(api_client, user, resource):
    resource.is_active = False
    resource.save(update_fields=["is_active", "updated_at"])

    api_client.force_authenticate(user=user)

    target_date = timezone.localdate() + timedelta(days=1)

    response = api_client.get(
        reverse("resources:resource-availability", args=[resource.id]),
        {"date": target_date.isoformat()},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
