from django.db import migrations


def forwards(apps, schema_editor):
    # From Phase C on, v1 participants are no longer written; copy any created after 0003.
    from apps.ceremonies.backfill import backfill

    backfill(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("ceremonies", "0003_backfill_ownership_from_participants"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
