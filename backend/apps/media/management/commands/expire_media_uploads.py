"""Close Drive upload sessions past their TTL (run from cron, e.g. hourly)."""

from django.core.management.base import BaseCommand

from apps.media.services import expire_stale


class Command(BaseCommand):
    help = "Expire abandoned media upload sessions."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{expire_stale()} upload session(s) expired."))
