"""Mark overdue PENDING ceremony invitations EXPIRED (run from cron, e.g. hourly).

Expiry is also enforced on every read/accept; this only keeps stored statuses tidy.
"""

from django.core.management.base import BaseCommand

from apps.ceremonies.invitations import expire_stale


class Command(BaseCommand):
    help = "Expire overdue ceremony invitations."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{expire_stale()} invitation(s) expired."))
