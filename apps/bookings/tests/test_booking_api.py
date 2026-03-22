from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import BookingHistory, BookingHistoryAction
from apps.bookings.models import Booking, BookingStatus
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
    return Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Team meeting",
    )


@pytest.mark.django_db
def test_booking_list_requires_authentication(api_client):
    url = reverse("bookings:booking-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_user_sees_only_own_bookings(api_client, user, other_user, resource):
    own_booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Own booking",
    )

    Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(12),
        end_at=future_datetime(13),
        title="Other booking",
    )

    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == own_booking.id


@pytest.mark.django_db
def test_manager_sees_all_bookings(api_client, manager, user, other_user, resource):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Booking A",
    )

    Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(12),
        end_at=future_datetime(13),
        title="Booking B",
    )

    api_client.force_authenticate(user=manager)

    response = api_client.get(reverse("bookings:booking-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_user_can_create_own_booking(api_client, user, resource):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "resource": resource.id,
            "start_at": future_datetime(10).isoformat(),
            "end_at": future_datetime(11).isoformat(),
            "title": "Team meeting",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    booking = Booking.objects.get()

    assert booking.user == user
    assert booking.resource == resource
    assert booking.status == BookingStatus.CONFIRMED


@pytest.mark.django_db
def test_user_cannot_create_booking_for_another_user(
    api_client, user, other_user, resource
):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "user": other_user.id,
            "resource": resource.id,
            "start_at": future_datetime(10).isoformat(),
            "end_at": future_datetime(11).isoformat(),
            "title": "Forbidden booking",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Booking.objects.count() == 0


@pytest.mark.django_db
def test_manager_can_create_booking_for_user(api_client, manager, user, resource):
    api_client.force_authenticate(user=manager)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "user": user.id,
            "resource": resource.id,
            "start_at": future_datetime(10).isoformat(),
            "end_at": future_datetime(11).isoformat(),
            "title": "Manager-created booking",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    booking = Booking.objects.get()

    assert booking.user == user


@pytest.mark.django_db
def test_create_booking_returns_409_for_overlap(api_client, user, booking, resource):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "resource": resource.id,
            "start_at": future_datetime(10, 30).isoformat(),
            "end_at": future_datetime(11, 30).isoformat(),
            "title": "Conflicting booking",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "booking_conflict"

    assert Booking.objects.count() == 1


@pytest.mark.django_db
def test_create_booking_returns_400_for_invalid_duration(api_client, user, resource):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "resource": resource.id,
            "start_at": future_datetime(10).isoformat(),
            "end_at": future_datetime(10, 15).isoformat(),
            "title": "Too short",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "duration_too_short"


@pytest.mark.django_db
def test_user_can_retrieve_own_booking(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-detail", args=[booking.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == booking.id


@pytest.mark.django_db
def test_user_cannot_retrieve_another_users_booking(
    api_client, user, other_user, resource
):
    foreign_booking = Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Private booking",
    )

    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-detail", args=[foreign_booking.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_can_update_own_booking(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-detail", args=[booking.id])

    response = api_client.patch(url, {"title": "Updated meeting"}, format="json")

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.title == "Updated meeting"


@pytest.mark.django_db
def test_user_cannot_update_another_users_booking(
    api_client, user, other_user, resource
):
    foreign_booking = Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Private booking",
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "bookings:booking-detail",
            args=[foreign_booking.id],
        ),
        {"title": "Hacked"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    foreign_booking.refresh_from_db()

    assert foreign_booking.title == "Private booking"


@pytest.mark.django_db
def test_status_cannot_be_changed_directly(api_client, user, booking):
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "bookings:booking-detail",
            args=[booking.id],
        ),
        {"status": BookingStatus.COMPLETED},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == BookingStatus.CONFIRMED


@pytest.mark.django_db
def test_user_can_cancel_own_booking(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-cancel", args=[booking.id])

    response = api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == BookingStatus.CANCELLED

    booking.refresh_from_db()

    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at is not None


@pytest.mark.django_db
def test_user_cannot_cancel_another_users_booking(
    api_client, user, other_user, resource
):
    foreign_booking = Booking.objects.create(
        user=other_user,
        resource=resource,
        start_at=future_datetime(10),
        end_at=future_datetime(11),
        title="Private booking",
    )

    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-cancel", args=[foreign_booking.id])

    response = api_client.post(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    foreign_booking.refresh_from_db()

    assert foreign_booking.status == BookingStatus.CONFIRMED


@pytest.mark.django_db
def test_cancelled_booking_cannot_be_cancelled_again(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-cancel", args=[booking.id])

    first_response = api_client.post(url)

    assert first_response.status_code == status.HTTP_200_OK

    second_response = api_client.post(url)

    assert second_response.status_code == status.HTTP_400_BAD_REQUEST

    assert second_response.data["code"] == "booking_cannot_be_cancelled"


@pytest.mark.django_db
def test_booking_cannot_be_deleted_via_api(api_client, user, booking):
    api_client.force_authenticate(user=user)

    url = reverse("bookings:booking-detail", args=[booking.id])

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    assert Booking.objects.filter(pk=booking.id).exists()


@pytest.mark.django_db
def test_booking_does_not_support_put(api_client, user, booking):
    api_client.force_authenticate(user=user)

    response = api_client.put(
        reverse("bookings:booking-detail", args=[booking.id]), {}, format="json"
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_update_returns_409_for_booking_conflict(api_client, user, booking, resource):
    Booking.objects.create(
        user=user,
        resource=resource,
        start_at=future_datetime(12),
        end_at=future_datetime(13),
        title="Second booking",
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("bookings:booking-detail", args=[booking.id]),
        {
            "start_at": future_datetime(12, 30).isoformat(),
            "end_at": future_datetime(13, 30).isoformat(),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "booking_conflict"

    booking.refresh_from_db()

    assert booking.start_at == future_datetime(10)
    assert booking.end_at == future_datetime(11)


@pytest.mark.django_db
def test_manager_can_update_any_booking(api_client, manager, booking):
    api_client.force_authenticate(user=manager)

    response = api_client.patch(
        reverse("bookings:booking-detail", args=[booking.id]),
        {"title": "Updated by manager"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.title == "Updated by manager"


@pytest.mark.django_db
def test_manager_can_cancel_any_booking(api_client, manager, booking):
    api_client.force_authenticate(user=manager)

    response = api_client.post(reverse("bookings:booking-cancel", args=[booking.id]))

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.django_db
def test_manager_is_recorded_as_booking_creator(api_client, manager, user, resource):
    api_client.force_authenticate(user=manager)

    response = api_client.post(
        reverse("bookings:booking-list"),
        {
            "user": user.id,
            "resource": resource.id,
            "start_at": future_datetime(10).isoformat(),
            "end_at": future_datetime(11).isoformat(),
            "title": "Manager-created booking",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    history = BookingHistory.objects.get(action=BookingHistoryAction.CREATED)

    assert history.changed_by == manager
    assert history.booking.user == user
