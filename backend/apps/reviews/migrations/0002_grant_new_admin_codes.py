"""Admins who already manage venues / studios get the new codes, so nothing they ran before stops
working and the venue calendar is controllable from the panel right away (user request 2026-11-09).
Super Admin can revoke them per admin as usual."""

from django.db import migrations

GRANTS = {
    "venues.update": ("venues.schedule", "reviews.view", "reviews.moderate"),
    "studios.update": ("reviews.view", "reviews.moderate"),
    "venues.view": ("reviews.view",),
    "studios.view": ("reviews.view",),
}


def grant(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(role="ADMIN"):
        codes = list(user.admin_permissions or [])
        extra = [c for have, adds in GRANTS.items() if have in codes for c in adds]
        new = codes + [c for c in dict.fromkeys(extra) if c not in codes]
        if new != codes:
            user.admin_permissions = new
            user.save(update_fields=["admin_permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0001_initial"),
        ("accounts", "0003_venue_owner_role"),
    ]

    operations = [migrations.RunPython(grant, migrations.RunPython.noop)]
