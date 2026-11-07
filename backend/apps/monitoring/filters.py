import django_filters

from .models import ErrorCategory, RequestLog

STATUS_CLASSES = {"2xx": (200, 300), "3xx": (300, 400), "4xx": (400, 500), "5xx": (500, 600)}


class RequestLogFilter(django_filters.FilterSet):
    method = django_filters.ChoiceFilter(
        choices=[(m, m) for m in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")]
    )
    status_class = django_filters.ChoiceFilter(
        choices=[(k, k) for k in STATUS_CLASSES], method="filter_status_class", label="Status sinfi"
    )
    status_code = django_filters.NumberFilter()
    route = django_filters.CharFilter()
    path = django_filters.CharFilter(lookup_expr="icontains")
    error_category = django_filters.ChoiceFilter(choices=[c for c in ErrorCategory.choices if c[0]])
    request_id = django_filters.UUIDFilter()
    user_id = django_filters.UUIDFilter()
    since = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    until = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    min_duration = django_filters.NumberFilter(field_name="duration_ms", lookup_expr="gte")

    class Meta:
        model = RequestLog
        fields = [
            "method",
            "status_class",
            "status_code",
            "route",
            "path",
            "error_category",
            "request_id",
            "user_id",
            "since",
            "until",
            "min_duration",
        ]

    def filter_status_class(self, queryset, name, value):
        low, high = STATUS_CLASSES[value]
        return queryset.filter(status_code__gte=low, status_code__lt=high)
