from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.bookings.selectors import get_resource_availability
from apps.bookings.serializers import ResourceAvailabilityQuerySerializer

from .filters import ResourceFilter
from .models import Resource, ResourceCategory
from .permissions import IsManagerOrAdminForWrite
from .serializers import ResourceCategorySerializer, ResourceSerializer


class ResourceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer
    permission_classes = [IsManagerOrAdminForWrite]
    ordering_fields = ("name", "created_at")
    ordering = ("name",)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()

        try:
            category.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "Category cannot be deleted because "
                        "it is used by existing resources."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [IsManagerOrAdminForWrite]

    filterset_class = ResourceFilter

    ordering_fields = ("name", "created_at", "capacity")

    ordering = ("name",)

    def get_queryset(self):
        queryset = Resource.objects.select_related("category")

        user = self.request.user

        if getattr(user, "role", None) in {UserRole.MANAGER, UserRole.ADMIN} or getattr(
            user, "is_superuser", False
        ):
            return queryset

        return queryset.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        resource = self.get_object()

        resource.is_active = False
        resource.save(update_fields=["is_active", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        resource = self.get_object()

        query_serializer = ResourceAvailabilityQuerySerializer(
            data=request.query_params
        )

        query_serializer.is_valid(raise_exception=True)

        target_date = query_serializer.validated_data["date"]

        availability = get_resource_availability(
            resource=resource, target_date=target_date
        )

        return Response(availability, status=status.HTTP_200_OK)
