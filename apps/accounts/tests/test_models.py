import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import UserRole

User = get_user_model()


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123!",
        first_name="John",
        last_name="Doe",
    )

    assert user.email == "user@example.com"
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.check_password("StrongPassword123!")


@pytest.mark.django_db
def test_create_user_without_email_raises_error():
    with pytest.raises(ValueError, match="Users must have an email address."):
        User.objects.create_user(email="", password="StrongPassword123!")


@pytest.mark.django_db
def test_create_superuser():
    user = User.objects.create_superuser(
        email="admin@example.com", password="StrongPassword123!"
    )

    assert user.email == "admin@example.com"
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
def test_user_string_representation():
    user = User.objects.create_user(
        email="user@example.com", password="StrongPassword123!"
    )

    assert str(user) == "user@example.com"
