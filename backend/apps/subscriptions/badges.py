"""Read-only paid badges. Payment never implies identity or phone verification."""

from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import serializers

from .models import Subscription, SubscriptionStatus


class PaidBadgeSerializer(serializers.Serializer):
    is_verified = serializers.SerializerMethodField(
        help_text="Faol pulli obuna / biznes galichkasi (shaxs tasdig'i emas)"
    )

    def get_is_verified(self, obj) -> bool:
        model = obj._meta.model_name
        target = {"user": "user", "studio": "studio", "venue": "venue"}[model]
        key = f"_paid_badges_{target}"
        cache = self.context.setdefault(key, {})
        if obj.pk not in cache:
            parent_rows = getattr(self.parent, "instance", None)
            rows = parent_rows if isinstance(parent_rows, (list, tuple, QuerySet)) else [obj]
            ids = [row.pk for row in rows if type(row) is type(obj)]
            if obj.pk not in ids:
                ids.append(obj.pk)
            now = timezone.now()
            qs = Subscription.objects.filter(
                status=SubscriptionStatus.ACTIVE, starts_at__lte=now, ends_at__gt=now, **{f"{target}_id__in": ids}
            )
            if target == "user":
                qs = qs.filter(studio__isnull=True, venue__isnull=True)
            verified = set(qs.values_list(f"{target}_id", flat=True))
            cache.update({pk: pk in verified for pk in ids})
        return cache[obj.pk] and getattr(obj, "is_active", True) and not obj.is_deleted
