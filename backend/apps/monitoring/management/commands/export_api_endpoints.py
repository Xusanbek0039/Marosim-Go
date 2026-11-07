"""Regenerate docs/API_ENDPOINTS.md from the live OpenAPI schema (same source as the panel catalog).

python manage.py export_api_endpoints
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.access import ROLE_ORDER
from apps.monitoring import catalog, contract


class Command(BaseCommand):
    help = "Write docs/API_ENDPOINTS.md from the generated OpenAPI schema."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=str(Path(settings.BASE_DIR).parent / "docs" / "API_ENDPOINTS.md"))

    def handle(self, *args, output, **options):
        catalog.reset_cache()
        endpoints = contract.annotate(catalog.build())
        lines = [
            "# API endpointlar",
            "",
            "> Avtomatik yaratilgan: `python manage.py export_api_endpoints` (OpenAPI'dan). Qo'lda tahrirlamang.",
            "> Rollar DRF permission class'laridan olinadi (`apps/accounts/access.py`) va",
            "> `tests/test_api_access_contract.py` da har bir rol bilan haqiqiy so'rov orqali tekshiriladi.",
            "> Batafsil: Swagger `/api/v1/docs/`, panel → API Monitoring → Endpointlar.",
            "",
            "| Metod | Yo'l | Tavsif | Rollar | Ruxsat kodi (ADMIN) | Auth | Ma'lumot doirasi | Holat |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for e in endpoints:
            lines.append(
                f"| {e['method']} | `{e['path']}` | {_cell(e['summary'])} | {', '.join(e['allowed_roles']) or '—'} "
                f"| {', '.join(f'`{c}`' for c in e['required_permissions']) or '—'} | {e['auth_type']} "
                f"| {_cell(e['ownership_scope'] or '—')} | {_status(e)} |"
            )

        lines += ["", "## Rollar bo'yicha", ""]
        for role in ROLE_ORDER:
            mine = [e for e in endpoints if role in e["allowed_roles"]]
            lines += [f"### {role} ({len(mine)})", ""]
            lines += [f"* `{e['method']} {e['path']}` — {_cell(e['summary'])}" for e in mine] or ["* —"]
            lines.append("")

        conditional = [e for e in endpoints if e["conditions"]]
        lines += ["## Qo'shimcha shartlar", ""]
        for e in conditional:
            lines.append(f"* `{e['method']} {e['path']}`")
            lines += [f"  * {_cell(c)}" for c in e["conditions"]]

        from apps.devcenter.planned import PLANNED_ENDPOINTS

        lines += [
            "",
            "## Rejalashtirilgan (PLANNED — hali ishlamaydi)",
            "",
            "> `apps/devcenter/planned.py`. Yuqoridagi jadval — faqat haqiqatda ishlaydigan endpointlar.",
            "> CEREMONY_OWNER / CEREMONY_VIEWER — global rol emas, marosimga xos huquq.",
            "",
            "| Bosqich | Metod | Yo'l | Tavsif | Kim | Shart |",
            "|---|---|---|---|---|---|",
        ]
        for p in PLANNED_ENDPOINTS:
            lines.append(
                f"| {p.phase} | {p.method} | `{p.path}` | {_cell(p.summary)} | {', '.join(p.roles)} "
                f"| {_cell(p.condition) or '—'} |"
            )
        Path(output).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"{len(endpoints)} endpoints -> {output}"))


def _cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _status(e: dict) -> str:
    flags = []
    if e["access_status"] != "DERIVED":
        flags.append("REVIEW REQUIRED")
    if e["documentation_status"] != "DOCUMENTED":
        flags.append("Documentation Missing")
    if e["contract_status"] != contract.MATCHES:
        flags.append(e["contract_status"])
    if e["deprecated"]:
        flags.append("Deprecated")
    return ", ".join(flags) or "OK"
