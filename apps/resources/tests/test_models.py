from datetime import time, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.resources.models import Resource, ResourceCategory


@pytest.fixture
def category():
    return ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")


@pytest.mark.django_db
def test_create_resource_category():
    category = ResourceCategory.objects.create(
        name="Meeting Room",
        slug="meeting-room",
        description="Rooms intended for meetings.",
    )

    assert category.name == "Meeting Room"
    assert category.slug == "meeting-room"
    assert category.description == "Rooms intended for meetings."
    assert category.created_at is not None
    assert category.updated_at is not None


@pytest.mark.django_db
def test_resource_category_string_representation():
    category = ResourceCategory.objects.create(name="Vehicle", slug="vehicle")

    assert str(category) == "Vehicle"


@pytest.mark.django_db
def test_resource_category_slug_must_be_unique():
    ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ResourceCategory.objects.create(name="Conference Room", slug="meeting-room")


@pytest.mark.django_db
def test_resource_category_name_is_case_insensitive_unique():
    ResourceCategory.objects.create(name="Meeting Room", slug="meeting-room")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ResourceCategory.objects.create(
                name="meeting room", slug="another-meeting-room"
            )


@pytest.mark.django_db
def test_resource_categories_are_ordered_by_name():
    ResourceCategory.objects.create(name="Vehicle", slug="vehicle")

    ResourceCategory.objects.create(name="Classroom", slug="classroom")

    ResourceCategory.objects.create(name="Equipment", slug="equipment")

    categories = list(ResourceCategory.objects.values_list("name", flat=True))

    assert categories == ["Classroom", "Equipment", "Vehicle"]


@pytest.mark.django_db
def test_create_resource(category):
    resource = Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A, Floor 2",
        capacity=12,
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    assert resource.name == "Conference Room A"
    assert resource.slug == "conference-room-a"
    assert resource.category == category
    assert resource.location == "Building A, Floor 2"
    assert resource.capacity == 12
    assert resource.is_active is True

    assert resource.booking_min_duration == timedelta(minutes=30)
    assert resource.booking_max_duration == timedelta(hours=4)

    assert resource.available_from == time(8, 0)
    assert resource.available_to == time(20, 0)

    assert resource.created_at is not None
    assert resource.updated_at is not None


@pytest.mark.django_db
def test_resource_string_representation(category):
    resource = Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    assert str(resource) == "Conference Room A"


@pytest.mark.django_db
def test_resource_default_capacity_is_one(category):
    resource = Resource.objects.create(
        name="Projector",
        slug="projector",
        category=category,
        location="Storage Room",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    assert resource.capacity == 1


@pytest.mark.django_db
def test_resource_is_active_by_default(category):
    resource = Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    assert resource.is_active is True


@pytest.mark.django_db
def test_resource_slug_must_be_unique(category):
    Resource.objects.create(
        name="Conference Room A",
        slug="conference-room",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Resource.objects.create(
                name="Conference Room B",
                slug="conference-room",
                category=category,
                location="Building B",
                booking_min_duration=timedelta(minutes=30),
                booking_max_duration=timedelta(hours=4),
                available_from=time(8, 0),
                available_to=time(20, 0),
            )


@pytest.mark.django_db
def test_resource_max_duration_cannot_be_less_than_min(category):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Resource.objects.create(
                name="Conference Room",
                slug="conference-room",
                category=category,
                location="Building A",
                booking_min_duration=timedelta(hours=4),
                booking_max_duration=timedelta(minutes=30),
                available_from=time(8, 0),
                available_to=time(20, 0),
            )


@pytest.mark.django_db
def test_resource_available_to_must_be_after_available_from(category):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Resource.objects.create(
                name="Conference Room",
                slug="conference-room",
                category=category,
                location="Building A",
                booking_min_duration=timedelta(minutes=30),
                booking_max_duration=timedelta(hours=4),
                available_from=time(20, 0),
                available_to=time(8, 0),
            )


@pytest.mark.django_db
def test_category_resources_relation(category):
    resource = Resource.objects.create(
        name="Conference Room A",
        slug="conference-room-a",
        category=category,
        location="Building A",
        booking_min_duration=timedelta(minutes=30),
        booking_max_duration=timedelta(hours=4),
        available_from=time(8, 0),
        available_to=time(20, 0),
    )

    assert list(category.resources.all()) == [resource]


@pytest.mark.django_db
def test_cannot_delete_category_used_by_resource(category):
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

    with pytest.raises(ProtectedError):
        category.delete()
