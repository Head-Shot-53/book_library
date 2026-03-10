from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.accounts.models import UserRole

from .models import Resource
from .permissions import IsManagerOrAdminForWrite
from .serializers import ResourceSerializer


class ResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [IsManagerOrAdminForWrite]

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
        resource.save()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
