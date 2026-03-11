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
def meeting_category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.fixture
def vehicle_category():
    return ResourceCategory.objects.create(name="Vehicle", slug="vehicle")


@pytest.mark.django_db
def test_filter_resources_by_category(
    api_client, user, meeting_category, vehicle_category
):
    Resource.objects.create(
        name="Conference Room",
        slug="conference-room",
        category=meeting_category,
        location="Building A",
        capacity=10,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    Resource.objects.create(
        name="Company Car",
        slug="company-car",
        category=vehicle_category,
        location="Parking A",
        capacity=5,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=8),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url, {"category": "meeting-room"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["name"] == "Conference Room"


@pytest.mark.django_db
def test_filter_resources_by_location(api_client, user, meeting_category):
    Resource.objects.create(
        name="Room A",
        slug="room-a",
        category=meeting_category,
        location="Building A",
        capacity=10,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    Resource.objects.create(
        name="Room B",
        slug="room-b",
        category=meeting_category,
        location="Building B",
        capacity=10,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url, {"location": "Building A"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["name"] == "Room A"


@pytest.mark.django_db
def test_filter_resources_by_capacity(api_client, user, meeting_category):
    Resource.objects.create(
        name="Small Room",
        slug="small-room",
        category=meeting_category,
        location="Building A",
        capacity=4,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    Resource.objects.create(
        name="Large Room",
        slug="large-room",
        category=meeting_category,
        location="Building A",
        capacity=20,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url, {"capacity": 20})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Large Room"


@pytest.mark.django_db
def test_resources_can_be_ordered_by_name(api_client, user, meeting_category):
    for name, slug in (("Zulu Room", "zulu-room"), ("Alpha Room", "alpha-room")):
        Resource.objects.create(
            name=name,
            slug=slug,
            category=meeting_category,
            location="Building A",
            capacity=10,
            booking_min_duration=timedelta(minutes=30),
            booking_max_duration=timedelta(hours=4),
            available_from=time(8, 0),
            available_to=time(20, 0),
        )

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url, {"ordering": "name"})

    names = [resource["name"] for resource in response.data["results"]]

    assert names == ["Alpha Room", "Zulu Room"]


@pytest.mark.django_db
def test_resources_are_paginated(api_client, user, meeting_category):
    resources = [
        Resource(
            name=f"Room {number:02}",
            slug=f"room-{number:02}",
            category=meeting_category,
            location="Building A",
            capacity=10,
            booking_min_duration=timedelta(minutes=30),
            booking_max_duration=timedelta(hours=4),
            available_from=time(8, 0),
            available_to=time(20, 0),
        )
        for number in range(21)
    ]

    Resource.objects.bulk_create(resources)

    api_client.force_authenticate(user=user)

    url = reverse("resources:resource-list")

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 21
    assert len(response.data["results"]) == 20
    assert response.data["next"] is not None
