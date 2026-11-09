"""Business badge starter tariffs mirror existing rates; staff can edit or disable them."""
import uuid

from django.db import migrations


def seed(apps, schema_editor):
    plan_model = apps.get_model("subscriptions", "SubscriptionPlan")
    for audience, label in (("STUDIO", "Studiya"), ("VENUE", "To'yxona")):
        for suffix, months, price in (("M1", 1, "25000.00"), ("Y1", 12, "100000.00")):
            plan_model.objects.get_or_create(
                code=f"{audience}_{suffix}",
                defaults={"id": uuid.uuid4(), "name": f"{label} galichkasi — {months} oy",
                          "audience": audience, "duration_months": months, "price": price,
                          "max_viewers": 1, "position": 10 if months == 1 else 11},
            )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0003_remove_subscription_subscriptions_one_pending_per_user_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
