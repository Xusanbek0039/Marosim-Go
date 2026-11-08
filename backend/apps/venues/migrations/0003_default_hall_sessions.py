"""Back-fill the default sessions (Nahor / Kunduzgi / Kechki) for halls created before sessions existed."""

import datetime
import uuid

from django.db import migrations

DEFAULTS = (("Nahor", "06:00", "10:00"), ("Kunduzgi", "12:00", "16:00"), ("Kechki", "18:00", "23:00"))


def forwards(apps, schema_editor):
    Hall = apps.get_model("venues", "VenueHall")
    Session = apps.get_model("venues", "HallSession")
    for hall in Hall.objects.filter(sessions__isnull=True):
        Session.objects.bulk_create(
            Session(
                id=uuid.uuid4(),
                hall=hall,
                name=name,
                starts_at=datetime.time.fromisoformat(start),
                ends_at=datetime.time.fromisoformat(end),
            )
            for name, start, end in DEFAULTS
        )


class Migration(migrations.Migration):
    dependencies = [("venues", "0002_hall_sessions_bookings")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
