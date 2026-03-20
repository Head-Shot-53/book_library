from django.db.models import QuerySet

from apps.accounts.models import UserRole

from .models import Booking


def can_manage_all_bookings(user) -> bool:
    return user.is_superuser or user.role in {UserRole.MANAGER, UserRole.ADMIN}


def get_bookings_for_user(*, user) -> QuerySet[Booking]:
    queryset = Booking.objects.select_related("user", "resource", "resource__category")

    if can_manage_all_bookings(user):
        return queryset

    return queryset.filter(user=user)
