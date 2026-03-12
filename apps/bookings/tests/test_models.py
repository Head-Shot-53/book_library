from datetime import time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
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


@pytest.fixture
def booking(user, resource):
    start_at = timezone.now() + timedelta(days=1)

    return Booking.objects.create(
        user=user,
        resource=resource,
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        title="Team meeting",
    )


@pytest.mark.django_db
def test_create_booking(booking, user, resource):
    assert booking.user == user
    assert booking.resource == resource
    assert booking.title == "Team meeting"
    assert booking.notes == ""

    assert booking.status == BookingStatus.CONFIRMED

    assert booking.cancelled_at is None
    assert booking.created_at is not None
    assert booking.updated_at is not None


@pytest.mark.django_db
def test_booking_string_representation(booking):
    assert "Conference Room A" in str(booking)


@pytest.mark.django_db
def test_booking_end_at_must_be_after_start_at(user, resource):
    start_at = timezone.now() + timedelta(days=1)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Booking.objects.create(
                user=user,
                resource=resource,
                start_at=start_at,
                end_at=start_at - timedelta(hours=1),
                title="Invalid booking",
            )


@pytest.mark.django_db
def test_booking_start_and_end_cannot_be_equal(user, resource):
    start_at = timezone.now() + timedelta(days=1)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Booking.objects.create(
                user=user,
                resource=resource,
                start_at=start_at,
                end_at=start_at,
                title="Invalid booking",
            )


@pytest.mark.django_db
def test_user_has_bookings_relation(user, booking):
    assert list(user.bookings.all()) == [booking]


@pytest.mark.django_db
def test_resource_has_bookings_relation(resource, booking):
    assert list(resource.bookings.all()) == [booking]


@pytest.mark.django_db
def test_cannot_delete_resource_with_booking(resource, booking):
    with pytest.raises(ProtectedError):
        resource.delete()


@pytest.mark.django_db
def test_cannot_delete_user_with_booking(user, booking):
    with pytest.raises(ProtectedError):
        user.delete()
