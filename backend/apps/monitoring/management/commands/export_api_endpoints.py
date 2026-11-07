"""Regenerate docs/API_ENDPOINTS.md from the live OpenAPI schema (same source as the panel catalog).

python manage.py export_api_endpoints
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.monitoring import catalog


class Command(BaseCommand):
    help = "Write docs/API_ENDPOINTS.md from the generated OpenAPI schema."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=str(Path(settings.BASE_DIR).parent / "docs" / "API_ENDPOINTS.md"))

    def handle(self, *args, output, **options):
        catalog.reset_cache()
        endpoints = catalog.build()
        lines = [
            "# API endpointlar",
            "",
            "> Avtomatik yaratilgan: `python manage.py export_api_endpoints` (OpenAPI'dan). Qo'lda tahrirlamang.",
            "> Batafsil: Swagger `/api/v1/docs/`, panel → API Monitoring → Endpointlar.",
            "",
            "| Metod | Yo'l | Tavsif | Kirish |",
            "|---|---|---|---|",
        ]
        for e in endpoints:
            access = e["access_label"] or ("Auth" if e["auth_required"] else "Ochiq")
            summary = (e["summary"] or "").replace("|", "\\|")
            lines.append(f"| {e['method']} | `{e['path']}` | {summary} | {access} |")
        Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"{len(endpoints)} endpoints -> {output}"))
