from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import BookingHistory

User = get_user_model()


class AuditActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = ("id", "email", "first_name", "last_name")

        read_only_fields = fields


class BookingHistorySerializer(serializers.ModelSerializer):
    changed_by = AuditActorSerializer(read_only=True)

    class Meta:
        model = BookingHistory

        fields = ("id", "action", "changed_by", "old_data", "new_data", "created_at")

        read_only_fields = fields
