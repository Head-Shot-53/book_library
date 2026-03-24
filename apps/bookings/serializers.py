from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.resources.models import Resource

from .models import Booking

User = get_user_model()


class BookingReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking

        fields = (
            "id",
            "user",
            "resource",
            "start_at",
            "end_at",
            "status",
            "title",
            "notes",
            "created_at",
            "updated_at",
            "cancelled_at",
        )

        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False
    )

    resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all())

    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()

    title = serializers.CharField(max_length=200)

    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BookingUpdateSerializer(serializers.Serializer):
    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(), required=False
    )

    start_at = serializers.DateTimeField(required=False)

    end_at = serializers.DateTimeField(required=False)

    title = serializers.CharField(
        max_length=200,
        required=False,
    )

    notes = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        forbidden_fields = {
            "user",
            "status",
            "cancelled_at",
            "created_at",
            "updated_at",
        }

        submitted_forbidden_fields = forbidden_fields.intersection(data.keys())

        if submitted_forbidden_fields:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be modified."
                    for field in submitted_forbidden_fields
                }
            )

        return super().to_internal_value(data)


class ResourceAvailabilityQuerySerializer(serializers.Serializer):
    date = serializers.DateField()


class BookingErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()
