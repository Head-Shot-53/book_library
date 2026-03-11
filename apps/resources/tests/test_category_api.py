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
def category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.mark.django_db
def test_user_can_list_categories(api_client, user, category):
    api_client.force_authenticate(user=user)

    url = reverse("categories:category-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["name"] == "Meeting Room"


@pytest.mark.django_db
def test_user_cannot_create_category(api_client, user):
    api_client.force_authenticate(user=user)

    url = reverse("categories:category-list")

    response = api_client.post(
        url, {"name": "Vehicle", "slug": "vehicle"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_manager_can_create_category(api_client, manager):
    api_client.force_authenticate(user=manager)

    url = reverse("categories:category-list")

    response = api_client.post(
        url,
        {"name": "Vehicle", "slug": "vehicle", "description": "Company vehicles."},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert ResourceCategory.objects.filter(slug="vehicle").exists()


@pytest.mark.django_db
def test_user_cannot_update_category(api_client, user, category):
    api_client.force_authenticate(user=user)

    url = reverse("categories:category-detail", args=[category.id])

    response = api_client.patch(url, {"name": "New Name"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_manager_can_update_category(api_client, manager, category):
    api_client.force_authenticate(user=manager)

    url = reverse("categories:category-detail", args=[category.id])

    response = api_client.patch(
        url, {"description": "Updated description."}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK

    category.refresh_from_db()

    assert category.description == "Updated description."


@pytest.mark.django_db
def test_manager_can_delete_unused_category(api_client, manager, category):
    api_client.force_authenticate(user=manager)

    url = reverse("categories:category-detail", args=[category.id])

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert not ResourceCategory.objects.filter(id=category.id).exists()


@pytest.mark.django_db
def test_cannot_delete_category_used_by_resource(api_client, manager, category):
    Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    api_client.force_authenticate(user=manager)

    url = reverse("categories:category-detail", args=[category.id])

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_409_CONFLICT

    assert ResourceCategory.objects.filter(id=category.id).exists()
