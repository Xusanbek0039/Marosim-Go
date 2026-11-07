"""Endpoints that are designed but not implemented yet — kept apart from the live catalog.

Live endpoints come only from the OpenAPI schema. This list exists so the docs and the Developer
Center can show what is *coming* without ever presenting it as callable. When an endpoint ships,
delete it here: ``tests/test_devcenter.py`` fails while a planned entry matches a live operation.

Paths follow the existing routing (studio side under ``/ceremonies/``, user side under ``/me/``).
``roles`` may use the ceremony-scoped CEREMONY_OWNER / CEREMONY_VIEWER, which are not ``User.role``s.
"""

from dataclasses import dataclass

CEREMONY_OWNER = "CEREMONY_OWNER"
CEREMONY_VIEWER = "CEREMONY_VIEWER"


@dataclass(frozen=True)
class PlannedEndpoint:
    method: str
    path: str
    summary: str
    roles: tuple[str, ...]
    phase: str
    condition: str = ""


_ID = "{id}"
MEMBER = "USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi)"

PLANNED_ENDPOINTS: tuple[PlannedEndpoint, ...] = (
    # ------------------------------------------------------------ Phase E
    PlannedEndpoint(
        "GET", f"/api/v1/me/ceremonies/{_ID}/media/", "Media galereya", (CEREMONY_OWNER, CEREMONY_VIEWER), "E", MEMBER
    ),
    *(
        PlannedEndpoint(
            "GET",
            f"/api/v1/me/ceremonies/{_ID}/media/{{media_id}}/{kind}/",
            label,
            (CEREMONY_OWNER, CEREMONY_VIEWER),
            "E",
            MEMBER + "; Drive fayli hech qachon public qilinmaydi",
        )
        for kind, label in (
            ("thumbnail", "Kichik rasm"),
            ("preview", "Ko'rib chiqish"),
            ("stream", "Video oqimi (Range)"),
            ("download", "Asl faylni yuklab olish"),
        )
    ),
    # ------------------------------------------------------------ Phase F
    PlannedEndpoint("GET", "/api/v1/admin/ceremonies/", "Barcha marosimlar monitoringi", ("SUPER_ADMIN",), "F"),
    PlannedEndpoint(
        "GET",
        f"/api/v1/admin/ceremonies/{_ID}/",
        "Marosim: egalar, takliflar, ko'ruvchilar, media, tarix",
        ("SUPER_ADMIN",),
        "F",
        "Maxfiy maydonlar faqat audit qilinadigan alohida amal orqali",
    ),
)
