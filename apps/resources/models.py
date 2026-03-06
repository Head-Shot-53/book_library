from django.db import models
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
