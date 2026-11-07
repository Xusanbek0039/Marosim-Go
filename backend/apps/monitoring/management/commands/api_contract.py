"""Check or regenerate the reviewed API access contract.

python manage.py api_contract          # exit 1 and print the diff if the live API differs
python manage.py api_contract --write  # accept the live API as the new contract (review the git diff!)
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.monitoring import catalog, contract


class Command(BaseCommand):
    help = "Compare the live OpenAPI role metadata with contracts/api_access_contract.json."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Overwrite the contract with the live API.")
        parser.add_argument("--note", default="", help="Changelog note for this change (with --write).")

    def handle(self, *args, write, note, **options):
        catalog.reset_cache()
        live = contract.current()
        review = [name for name, entry in live.items() if entry["access_status"] != "DERIVED"]
        if write:
            history = contract.load_changelog()
            # The first entry is the baseline: every operation that exists counts as "added".
            changes = contract.diff(contract.load() if history else {}, live)
            if any(changes.values()) or not history:
                entry = contract.changelog_entry(
                    changes, revision=len(history) + 1, date=timezone.localdate().isoformat(), note=note
                )
                contract.append_changelog(entry)
                for name in entry["breaking"]:
                    self.stdout.write(self.style.WARNING(f"BREAKING (consider a new API version): {name}"))
            contract.dump(live)
            self.stdout.write(self.style.SUCCESS(f"{len(live)} operations -> {contract.CONTRACT_PATH}"))
            for name in review:
                self.stdout.write(self.style.WARNING(f"REVIEW REQUIRED: {name}"))
            return
        changes = contract.diff(contract.load(), live)
        if any(changes.values()):
            self.stdout.write(json.dumps(changes, indent=2, ensure_ascii=False))
            raise CommandError("API contract differs. Review, then run `python manage.py api_contract --write`.")
        self.stdout.write(self.style.SUCCESS(f"API contract up to date ({len(live)} operations)."))
