import django_filters

from .models import Booking, BookingStatus


class BookingFilter(django_filters.FilterSet):
    resource = django_filters.NumberFilter(field_name="resource_id")

    user = django_filters.NumberFilter(field_name="user_id")

    status = django_filters.ChoiceFilter(choices=BookingStatus.choices)

    date_from = django_filters.DateFilter(
        field_name="start_at", lookup_expr="date__gte"
    )

    date_to = django_filters.DateFilter(field_name="start_at", lookup_expr="date__lte")

    class Meta:
        model = Booking

        fields = ("resource", "user", "status", "date_from", "date_to")
