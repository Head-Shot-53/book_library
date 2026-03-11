import django_filters

from .models import Resource


class ResourceFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )

    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")

    capacity = django_filters.NumberFilter(field_name="capacity")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Resource

        fields = ("category", "location", "capacity", "is_active")
