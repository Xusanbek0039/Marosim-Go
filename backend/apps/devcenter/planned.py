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
OWNER_ONLY = "USER roli + marosimda ACCEPTED ownership"
MEMBER = "USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi)"
STUDIO_MANAGE = "Studiya a'zoligi OWNER/MANAGER (UPLOADER — faqat yuklash)"

PLANNED_ENDPOINTS: tuple[PlannedEndpoint, ...] = (
    # ------------------------------------------------------------ Phase C
    PlannedEndpoint(
        "POST",
        f"/api/v1/ceremonies/{_ID}/owners/invite/",
        "Marosim egasini telefon / JSHSHIR orqali taklif qilish",
        ("STUDIO", "SUPER_ADMIN"),
        "C",
        STUDIO_MANAGE + "; egalar bor bo'lsa — ularning tasdig'i kerak",
    ),
    PlannedEndpoint(
        "GET", f"/api/v1/ceremonies/{_ID}/owners/", "Egalar va egalik takliflari holati", ("STUDIO", "SUPER_ADMIN"), "C"
    ),
    PlannedEndpoint("GET", f"/api/v1/me/invitations/{_ID}/", "Taklif tafsilotlari", ("USER",), "C"),
    PlannedEndpoint("GET", f"/api/v1/me/ceremonies/{_ID}/members/", "Egalar va ko'ruvchilar", (CEREMONY_OWNER,), "C"),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/invitations/",
        "VIEWER yoki OWNER taklifi yuborish",
        (CEREMONY_OWNER,),
        "C",
        OWNER_ONLY + "; OWNER taklifi boshqa egalar tasdig'idan o'tadi",
    ),
    PlannedEndpoint("GET", f"/api/v1/me/ceremonies/{_ID}/invitations/", "Takliflar tarixi", (CEREMONY_OWNER,), "C"),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/invitations/{{invitation_id}}/revoke/",
        "O'zi yuborgan taklifni bekor qilish",
        (CEREMONY_OWNER,),
        "C",
        "Faqat taklifni yuborgan ega",
    ),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/invitations/{{invitation_id}}/resend/",
        "Taklifni qayta yuborish (muddat yangilanadi)",
        (CEREMONY_OWNER,),
        "C",
        "Faqat taklifni yuborgan ega",
    ),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/viewers/{{access_id}}/revoke/",
        "O'zi bergan ko'rish huquqini bekor qilish",
        (CEREMONY_OWNER,),
        "C",
        "Faqat huquqni bergan ega; boshqa egalar emas",
    ),
    PlannedEndpoint(
        "POST", f"/api/v1/me/ceremonies/{_ID}/leave/", "Marosimdan chiqish", (CEREMONY_OWNER, CEREMONY_VIEWER), "C"
    ),
    PlannedEndpoint(
        "GET", f"/api/v1/me/ceremonies/{_ID}/owner-requests/", "Tasdiq kutayotgan yangi egalar", (CEREMONY_OWNER,), "C"
    ),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/owner-requests/{{request_id}}/approve/",
        "Yangi egani tasdiqlash",
        (CEREMONY_OWNER,),
        "C",
        "Faqat so'rov ochilganda ACCEPTED bo'lgan va hali ega bo'lgan egalar",
    ),
    PlannedEndpoint(
        "POST",
        f"/api/v1/me/ceremonies/{_ID}/owner-requests/{{request_id}}/reject/",
        "Yangi egani rad etish",
        (CEREMONY_OWNER,),
        "C",
        "Faqat so'rov ochilganda ACCEPTED bo'lgan va hali ega bo'lgan egalar",
    ),
    # ------------------------------------------------------------ Phase D
    PlannedEndpoint(
        "POST",
        f"/api/v1/ceremonies/{_ID}/media/uploads/",
        "Resumable media upload sessiyasi",
        ("STUDIO",),
        "D",
        "Studiya a'zoligi OWNER/MANAGER/UPLOADER",
    ),
    PlannedEndpoint("GET", f"/api/v1/ceremonies/{_ID}/media/", "Yuklangan fayllar va holati", ("STUDIO",), "D"),
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
