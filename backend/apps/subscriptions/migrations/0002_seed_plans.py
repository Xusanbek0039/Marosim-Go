"""Initial plans (user decision 2026-11-08). Prices / limits are edited later in the admin panel."""

import uuid
from decimal import Decimal

from django.db import migrations

PLANS = (
    ("M1", "1 oy", 1, Decimal("25000"), 10, 1),
    ("M3", "3 oy", 3, Decimal("60000"), 20, 2),
    ("Y1", "1 yil", 12, Decimal("100000"), 30, 3),
    ("Y5", "5 yil", 60, Decimal("300000"), 50, 4),
)


def seed(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "SubscriptionPlan")
    for code, name, months, price, viewers, position in PLANS:
        Plan.objects.get_or_create(
            code=code,
            defaults={
                "id": uuid.uuid4(),
                "name": name,
                "duration_months": months,
                "price": price,
                "max_viewers": viewers,
                "position": position,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
