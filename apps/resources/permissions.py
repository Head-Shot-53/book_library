from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import UserRole


class IsManagerOrAdminForWrite(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return (
            request.user.role in {UserRole.MANAGER, UserRole.ADMIN}
            or request.user.is_superuser
        )
