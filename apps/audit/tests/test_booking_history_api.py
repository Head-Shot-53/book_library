from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import BookingHistoryAction
from apps.bookings.models import Booking
from apps.bookings.services import (
    cancel_booking,
    complete_booking,
    create_booking,
    update_booking,
)
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


def future_datetime(hour: int, minute: int = 0):
    target_date = timezone.localdate() + timedelta(days=1)

    naive_datetime = datetime.combine(target_date, time(hour, minute))

    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!", role=UserRole.USER
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email="other@example.com", password="StrongPassword123!", role=UserRole.USER
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        email="manager@example.com",
        password="StrongPassword123!",
        role=UserRole.MANAGER,
    )


@pytest.fixture
def admin():
    return User.objects.create_user(
        email="admin@example.com", password="StrongPassword123!", role=UserRole.ADMIN
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


@pytest.fixture
def booking(user, resource):
    return create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Team meeting",
        changed_by=user,
    )


@pytest.mark.django_db
def test_booking_history_requires_authentication(api_client, booking):
    url = reverse("bookings:booking-history", args=[booking.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_user_can_view_own_booking_history(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-history", args=[booking.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK

    assert response.data["count"] == 1

    history = response.data["results"][0]

    assert history["action"] == BookingHistoryAction.CREATED

    assert history["changed_by"]["id"] == user.id
    assert history["changed_by"]["email"] == user.email


@pytest.mark.django_db
def test_user_cannot_view_another_users_booking_history(
    api_client, user, other_user, resource
):
    foreign_booking = create_booking(
        user=other_user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Private booking",
        changed_by=other_user,
    )

    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-history", args=[foreign_booking.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_manager_can_view_any_booking_history(api_client, manager, user, booking):
    api_client.force_authenticate(user=manager)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_admin_can_view_any_booking_history(api_client, admin, booking):
    api_client.force_authenticate(user=admin)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_history_endpoint_returns_update_event(api_client, user, booking):
    update_booking(booking=booking, title="Updated meeting", changed_by=user)

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2

    latest = response.data["results"][0]

    assert latest["action"] == BookingHistoryAction.UPDATED

    assert latest["old_data"]["title"] == "Team meeting"

    assert latest["new_data"]["title"] == "Updated meeting"


@pytest.mark.django_db
def test_history_is_returned_newest_first(api_client, user, booking):
    update_booking(booking=booking, title="Updated meeting", changed_by=user)

    cancel_booking(booking=booking, changed_by=user)

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    actions = [entry["action"] for entry in response.data["results"]]

    assert actions == [
        BookingHistoryAction.CANCELLED,
        BookingHistoryAction.UPDATED,
        BookingHistoryAction.CREATED,
    ]


@pytest.mark.django_db
def test_history_exposes_actual_manager_actor(api_client, manager, booking):
    update_booking(booking=booking, title="Changed by manager", changed_by=manager)

    api_client.force_authenticate(user=manager)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    update_event = response.data["results"][0]

    assert update_event["action"] == BookingHistoryAction.UPDATED

    assert update_event["changed_by"]["id"] == manager.id

    assert update_event["changed_by"]["email"] == manager.email


@pytest.mark.django_db
def test_system_history_event_has_null_actor(api_client, user, resource):
    end_at = timezone.now() - timedelta(minutes=30)

    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=end_at - timedelta(hours=1),
        end_at=end_at,
        title="Finished meeting",
    )

    complete_booking(booking=booking, changed_by=None)

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK

    history = response.data["results"][0]

    assert history["action"] == BookingHistoryAction.COMPLETED

    assert history["changed_by"] is None


@pytest.mark.django_db
def test_booking_history_cannot_be_created_via_api(api_client, user, booking):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-history", args=[booking.id]),
        {"action": BookingHistoryAction.CREATED},
        format="json",
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_booking_history_is_paginated(api_client, user, booking):
    for number in range(25):
        update_booking(booking=booking, title=f"Update {number}", changed_by=user)

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-history", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK

    assert response.data["count"] == 26
    assert len(response.data["results"]) == 20
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_history_returns_404_for_unknown_booking(api_client, user):
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-history", args=[999999]))

    assert response.status_code == status.HTTP_404_NOT_FOUND
