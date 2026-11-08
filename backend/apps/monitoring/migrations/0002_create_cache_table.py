"""Creates the shared database cache table (CACHES -> DatabaseCache) as part of ``migrate``.

Production uses ``dbcache://marosimgo_cache`` unless CACHE_URL points at Redis, so a plain
``python manage.py migrate`` on cPanel is enough — no separate ``createcachetable`` step to forget.
For other cache backends the command is a no-op.
"""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [("monitoring", "0001_initial")]

    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
