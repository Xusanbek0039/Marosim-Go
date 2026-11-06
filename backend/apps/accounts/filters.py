import django_filters

from . import pinfl as pinfl_utils
from .models import Role, User


class ManagedUserFilter(django_filters.FilterSet):
    role = django_filters.ChoiceFilter(choices=[(Role.USER, Role.USER.label), (Role.STUDIO, Role.STUDIO.label)])
    is_active = django_filters.BooleanFilter()
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    pinfl = django_filters.CharFilter(method="filter_pinfl", label="JSHSHIR (aniq moslik)")

    class Meta:
        model = User
        fields = ["role", "is_active", "created_after", "created_before", "pinfl"]

    def filter_pinfl(self, queryset, name, value):
        normalized = pinfl_utils.normalize(value)
        if not pinfl_utils.PINFL_RE.fullmatch(normalized):
            return queryset.none()
        return queryset.filter(pinfl_hash=pinfl_utils.hash_of(normalized))


class AdminFilter(ManagedUserFilter):
    class Meta(ManagedUserFilter.Meta):
        fields = ["is_active", "created_after", "created_before", "pinfl"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters.pop("role", None)
