from datetime import time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.resources.models import Resource, ResourceCategory

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com", password="StrongPassword123!", role=UserRole.USER
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


@pytest.mark.django_db
def test_resource_list_requires_authentication(api_client):
    url = reverse("resources:resource-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_user_can_list_resources(api_client, user, resource):
    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_user_does_not_see_inactive_resources(api_client, user, category):
    Resource.objects.create(
        name="Active Room",
        slug="active-room",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
        is_active=True,
    )

    Resource.objects.create(
        name="Inactive Room",
        slug="inactive-room",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
        is_active=False,
    )

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK

    names = [item["name"] for item in response.data["results"]]

    assert "Active Room" in names
    assert "Inactive Room" not in names


@pytest.mark.django_db
def test_manager_can_see_inactive_resources(api_client, manager, category):
    resource = Resource.objects.create(
        name="Inactive Room",
        slug="inactive-room",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
        is_active=False,
    )

    api_client.force_authenticate(user=manager)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == resource.id


@pytest.mark.django_db
def test_user_cannot_create_resource(api_client, user, category):
    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    payload = {
        "name": "Conference Room B",
        "slug": "conference-room-b",
        "category": category.id,
        "location": "Building B",
        "capacity": 10,
        "booking_min_duration": "00:30:00",
        "booking_max_duration": "04:00:00",
        "available_from": "08:00:00",
        "available_to": "20:00:00",
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert not Resource.objects.filter(slug="conference-room-b").exists()


@pytest.mark.django_db
def test_manager_can_create_resource(api_client, manager, category):
    api_client.force_authenticate(user=manager)

    url = reverse("resources:resource-list")

    payload = {
        "name": "Conference Room B",
        "slug": "conference-room-b",
        "category": category.id,
        "location": "Building B",
        "capacity": 10,
        "booking_min_duration": "00:30:00",
        "booking_max_duration": "04:00:00",
        "available_from": "08:00:00",
        "available_to": "20:00:00",
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED

    assert Resource.objects.filter(slug="conference-room-b").exists()


@pytest.mark.django_db
def test_user_cannot_update_resource(api_client, user, resource):
    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.patch(url, {"capacity": 50}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    resource.refresh_from_db()

    assert resource.capacity == 12


@pytest.mark.django_db
def test_admin_can_update_resource(api_client, admin, resource):
    api_client.force_authenticate(user=admin)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.patch(url, {"capacity": 20}, format="json")

    assert response.status_code == status.HTTP_200_OK

    resource.refresh_from_db()

    assert resource.capacity == 20


@pytest.mark.django_db
def test_user_cannot_delete_resource(api_client, user, resource):
    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN

    resource.refresh_from_db()

    assert resource.is_active is True


@pytest.mark.django_db
def test_manager_soft_deletes_resource(api_client, manager, resource):
    api_client.force_authenticate(user=manager)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert Resource.objects.filter(id=resource.id).exists()

    resource.refresh_from_db()

    assert resource.is_active is False


@pytest.mark.django_db
def test_user_cannot_retrieve_inactive_resource(api_client, user, resource):
    resource.is_active = False
    resource.save()

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-detail", args=[resource.id])

    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
