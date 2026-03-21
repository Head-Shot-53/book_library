from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.bookings.models import Booking, BookingStatus
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


def future_datetime(hour: int, minute: int = 0, *, days: int = 1):
    target_date = timezone.localdate() + timedelta(days=days)

    naive_datetime = datetime.combine(target_date, time(hour, minute))

    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!"
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email="other@example.com", password="StrongPassword123!"
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        email="manager@example.com",
        password="StrongPassword123!",
        role=UserRole.MANAGER,
    )


@pytest.fixture
def category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.fixture
def resource(category):
    return Resource.objects.create(
        name="Room A",
        slug="room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8),
        available_to=time(20),
    )


@pytest.mark.django_db
def test_filter_bookings_by_status(api_client, user, resource):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Confirmed",
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(12),
        end_at=future_datetime(13),
        title="Cancelled",
        status=BookingStatus.CANCELLED,
        cancelled_at=timezone.now(),
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("bookings:booking-list"), {"status": BookingStatus.CONFIRMED}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["title"] == "Confirmed"


@pytest.mark.django_db
def test_filter_bookings_by_resource(api_client, user, category, resource):
    second_resource = Resource.objects.create(
        name="Room B",
        slug="room-b",
        category=category,
        location="Building B",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8),
        available_to=time(20),
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Room A booking",
    )

    Booking.objects.create(
        user=user,
        resource=second_resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Room B booking",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("bookings:booking-list"), {"resource": resource.id}
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["resource"] == resource.id


@pytest.mark.django_db
def test_manager_can_filter_bookings_by_user(
    api_client, manager, user, other_user, resource
):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="User booking",
    )

    Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(12),
        end_at=future_datetime(13),
        title="Other booking",
    )

    api_client.force_authenticate(user=manager)

    response = api_client.get(reverse("bookings:booking-list"), {"user": user.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["user"] == user.id


@pytest.mark.django_db
def test_user_filter_cannot_expose_foreign_bookings(
    api_client, user, other_user, resource
):
    Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Private booking",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-list"), {"user": other_user.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_filter_bookings_by_date_range(api_client, user, resource):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10, days=1),
        end_at=future_datetime(11, days=1),
        title="Day 1",
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10, days=3),
        end_at=future_datetime(11, days=3),
        title="Day 3",
    )

    api_client.force_authenticate(user=user)

    target_date = timezone.localdate() + timedelta(days=1)

    response = api_client.get(
        reverse("bookings:booking-list"),
        {"date_from": target_date.isoformat(), "date_to": target_date.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Day 1"


@pytest.mark.django_db
def test_bookings_can_be_ordered_by_start_at(api_client, user, resource):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(14),
        end_at=future_datetime(15),
        title="Later",
    )

    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Earlier",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("bookings:booking-list"), {"ordering": "start_at"}
    )

    titles = [booking["title"] for booking in response.data["results"]]

    assert titles == ["Earlier", "Later"]
