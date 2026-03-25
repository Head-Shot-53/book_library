import json
import logging
from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.bookings.services import create_booking
from apps.resources.models import Resource, ResourceCategory
from config.logging import JsonFormatter

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
        available_from=time(8),
        available_to=time(20),
    )


@pytest.mark.django_db
def test_response_contains_request_id(api_client, user):
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("bookings:booking-list"))

    assert response.status_code == status.HTTP_200_OK

    request_id = response["X-Request-ID"]

    assert len(request_id) == 32


@pytest.mark.django_db
def test_booking_conflict_is_mapped_to_409(api_client, user, resource):
    create_booking(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Existing",
        changed_by=user,
    )

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "resource": resource.id,
            "start_at": (future_datetime(10, 30).isoformat()),
            "end_at": (future_datetime(11, 30).isoformat()),
            "title": "Conflict",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT

    assert response.data["code"] == "booking_conflict"


@pytest.mark.django_db
def test_domain_validation_is_mapped_to_400(api_client, user, resource):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "resource": resource.id,
            "start_at": (future_datetime(10).isoformat()),
            "end_at": (future_datetime(10, 15).isoformat()),
            "title": "Too short",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert response.data["code"] == "duration_too_short"


@pytest.mark.django_db
def test_unexpected_exception_returns_safe_500(api_client, user, resource):
    api_client.force_authenticate(user=user)

    internal_message = "SECRET INTERNAL DATABASE DETAILS"

    with patch(
        "apps.bookings.views.create_booking", side_effect=RuntimeError(internal_message)
    ):
        response = api_client.post(
            reverse("bookings:booking-list"),
            {
                "resource": resource.id,
                "start_at": (future_datetime(10).isoformat()),
                "end_at": (future_datetime(11).isoformat()),
                "title": "Meeting",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    assert response.data == {
        "detail": "Internal server error.",
        "code": "internal_error",
    }

    assert internal_message not in response.content.decode()


@pytest.mark.django_db
def test_permission_denied_response_is_safe(api_client, user, resource):
    other_user = User.objects.create_user(
        email="other@example.com", password="StrongPassword123!"
    )

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "user": other_user.id,
            "resource": resource.id,
            "start_at": (future_datetime(10).isoformat()),
            "end_at": (future_datetime(11).isoformat()),
            "title": "Forbidden",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_json_log_formatter():
    record = logging.LogRecord(
        name="booking_management.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="booking_created",
        args=(),
        exc_info=None,
    )

    record.booking_id = 42
    record.resource_id = 5

    formatter = JsonFormatter()

    output = formatter.format(record)

    data = json.loads(output)

    assert data["message"] == "booking_created"

    assert data["booking_id"] == 42
    assert data["resource_id"] == 5
    assert data["level"] == "INFO"
