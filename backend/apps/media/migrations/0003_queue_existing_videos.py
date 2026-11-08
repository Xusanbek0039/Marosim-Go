"""Videos uploaded before the watermark existed: queue them for a burned-in logo copy."""

from django.db import migrations


def forwards(apps, schema_editor):
    Media = apps.get_model("media", "CeremonyMedia")
    Media.objects.filter(kind="VIDEO", status="READY", wm_status="NONE").update(wm_status="PENDING")


class Migration(migrations.Migration):
    dependencies = [("media", "0002_video_watermark")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
