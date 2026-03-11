from rest_framework import serializers

from .models import Resource, ResourceCategory


class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory

        fields = ("id", "name", "slug", "description", "created_at", "updated_at")

        read_only_fields = ("id", "created_at", "updated_at")


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "category",
            "location",
            "capacity",
            "is_active",
            "booking_min_duration",
            "booking_max_duration",
            "available_from",
            "available_to",
            "created_at",
            "updated_at",
        )

        read_only_fields = ("id", "created_at", "updated_at")
