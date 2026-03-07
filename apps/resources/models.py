from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

        constraints = [
            models.UniqueConstraint(
                Lower("name"), name="unique_resource_category_name_ci"
            )
        ]

        verbose_name = "resource category"
        verbose_name_plural = "resource categories"

    def __str__(self):
        return self.name


class Resource(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        ResourceCategory, on_delete=models.PROTECT, related_name="resources"
    )

    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    booking_min_duration = models.DurationField()
    booking_max_duration = models.DurationField()
    available_from = models.TimeField()
    available_to = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

        constraints = [
            models.CheckConstraint(
                condition=Q(capacity__gte=1), name="resource_capacity_gte_1"
            ),
            models.CheckConstraint(
                condition=Q(booking_max_duration__gte=F("booking_min_duration")),
                name="resource_max_duration_gte_min",
            ),
            models.CheckConstraint(
                condition=Q(available_to__gt=F("available_from")),
                name="resource_available_to_gt_from",
            ),
        ]

    def __str__(self):
        return self.name
