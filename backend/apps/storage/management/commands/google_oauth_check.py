"""Verify the Google OAuth setup without ever printing a secret.

python manage.py google_oauth_check
"""

import shutil
import subprocess  # noqa: S404 - fixed git argv, no shell
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.storage import client_config, services


class Command(BaseCommand):
    help = "Check Google OAuth client JSON, redirect URI, encryption key and git-ignore status (no secrets shown)."

    def handle(self, *args, **options):
        report = client_config.diagnose()
        path = Path(settings.GOOGLE_OAUTH_CLIENT_FILE)
        ok = self.style.SUCCESS("OK")
        self.stdout.write(f"Client JSON path : {path}")
        self.stdout.write(f"  exists         : {ok if path.exists() else self.style.ERROR('NO')}")
        self.stdout.write(f"  git-ignored    : {self._ignored(path)}")
        self.stdout.write(f"Source           : {report['source'] or '-'}")
        self.stdout.write(f"Project          : {report['project_id'] or '-'}")
        self.stdout.write(f"Client id        : {report['client_id_hint'] or '-'}  (secret never shown)")
        self.stdout.write(f"Redirect URI     : {report['redirect_uri']}")
        self.stdout.write(f"Scopes           : {' '.join(report['scopes'])}")
        conn = services.connection()
        self.stdout.write(f"Connection       : {conn.status} {conn.account_email or ''}")
        if report["issues"]:
            for issue in report["issues"]:
                self.stdout.write(self.style.ERROR(f"  [x] [{issue['code']}] {issue['message']}"))
            self.stdout.write(self.style.WARNING("Not ready. See docs/GOOGLE_DRIVE_SETUP.md"))
        else:
            self.stdout.write(self.style.SUCCESS("Ready: open the panel > Google Drive > Connect."))

    def _ignored(self, path: Path) -> str:
        try:
            git = shutil.which("git")
            if git is None:
                return "unknown (git not available)"
            argv = [git, "check-ignore", "-q", str(path)]
            result = subprocess.run(argv, cwd=settings.BASE_DIR, capture_output=True, timeout=10)  # noqa: S603
        except (OSError, subprocess.SubprocessError):
            return "unknown (git not available)"
        return self.style.SUCCESS("yes") if result.returncode == 0 else self.style.ERROR("NO — never commit this file!")
