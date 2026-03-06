from django.contrib import admin

from .models import ResourceCategory


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
