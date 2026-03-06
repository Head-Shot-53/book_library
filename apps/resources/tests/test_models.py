import pytest
from django.db import IntegrityError, transaction

from apps.resources.models import ResourceCategory


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
