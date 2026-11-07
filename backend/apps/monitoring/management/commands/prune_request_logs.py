from django.core.management.base import BaseCommand

from apps.monitoring.writer import cfg, prune


class Command(BaseCommand):
    help = "Delete request metrics older than MONITORING['RETENTION_DAYS'] (and above MAX_ROWS)."

    def handle(self, *args, **options):
        deleted = prune()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} request log rows (retention {cfg()['RETENTION_DAYS']} days).")
        )
