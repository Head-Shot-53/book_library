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


class AvailabilityResourceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class WorkingHoursSerializer(serializers.Serializer):
    available_from = serializers.TimeField()
    available_to = serializers.TimeField()


class AvailabilitySlotSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class ResourceAvailabilitySerializer(serializers.Serializer):
    resource = AvailabilityResourceSerializer()
    date = serializers.DateField()
    timezone = serializers.CharField()

    working_hours = WorkingHoursSerializer()

    busy_slots = AvailabilitySlotSerializer(many=True)

    available_slots = AvailabilitySlotSerializer(many=True)
