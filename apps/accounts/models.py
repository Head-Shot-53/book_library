from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class UserRole(models.TextChoices):
    USER = "USER", "User"
    MANAGER = "MANAGER", "Manager"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.USER
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
