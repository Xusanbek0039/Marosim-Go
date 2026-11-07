"""Live check of what the ``drive.file`` scope really allows, against the connected Drive.

    python manage.py storage_selftest                 # in a new app-created test folder
    python manage.py storage_selftest --parent <ID>   # inside an existing (Picker-selected) folder

Creates ``MarosimGo_SELFTEST_<random>/`` with a ``Videos`` subfolder and a tiny text file,
reads them back, then deletes exactly those items. It never touches anything else.
"""

import secrets

from django.core.management.base import BaseCommand, CommandError

from apps.storage import services
from apps.storage.google import GoogleError


class Command(BaseCommand):
    help = "Create + verify + delete a test folder/file in the connected Google Drive (drive.file check)."

    def add_arguments(self, parser):
        parser.add_argument("--parent", default="", help="Existing folder id to test inside (e.g. picked root)")
        parser.add_argument("--keep", action="store_true", help="Do not delete the created test items")

    def handle(self, *args, parent="", keep=False, **options):
        try:
            creds = services.access_credentials()
        except services.StorageError as exc:
            raise CommandError(f"Not connected ({exc.code}). Connect Google Drive in the panel first.") from None

        gw = services.gateway()
        created: list[tuple[str, str]] = []
        try:
            if parent:
                meta = gw.get_file(creds, parent)
                self._ok(f"parent visible: {meta.get('name')} ({meta.get('mimeType')})")
                if meta.get("mimeType") != "application/vnd.google-apps.folder":
                    raise CommandError("--parent is not a folder.")
                self._ok(f"canAddChildren reported: {meta.get('capabilities', {}).get('canAddChildren')}")
            root = gw.create_folder(creds, f"MarosimGo_SELFTEST_{secrets.token_hex(4)}", parent or None)
            created.append(("folder", root["id"]))
            self._ok(f"created folder {root['name']}")
            sub = gw.create_folder(creds, "Videos", root["id"])
            created.append(("folder", sub["id"]))
            self._ok("created subfolder Videos")
            file = gw.create_text_file(creds, "hello.txt", sub["id"], b"MarosimGo drive.file self-test\n")
            created.append(("file", file["id"]))
            self._ok(f"uploaded hello.txt ({file.get('size')} bytes)")
            check = gw.get_file(creds, file["id"])
            if sub["id"] not in (check.get("parents") or []):
                raise CommandError("file parent mismatch")
            self._ok("read back metadata, parent verified")
        except GoogleError as exc:
            raise CommandError(f"Drive call failed: {exc.code} (HTTP {exc.status})") from None
        finally:
            if not keep:
                for kind, item_id in reversed(created):
                    try:
                        gw.delete_file(creds, item_id)
                    except GoogleError as exc:
                        self.stderr.write(f"cleanup failed for {kind} {item_id}: {exc.code}")
                if created:
                    self._ok(f"cleaned up {len(created)} test item(s)")
        self.stdout.write(self.style.SUCCESS("drive.file self-test passed."))

    def _ok(self, text: str) -> None:
        self.stdout.write(f"  [ok] {text}")
