from django.contrib import admin

from .models import Resource, ResourceCategory


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "location",
        "capacity",
        "is_active",
    )

    list_filter = ("category", "is_active")
    search_fields = ("name", "slug", "location")
    ordering = ("name",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
