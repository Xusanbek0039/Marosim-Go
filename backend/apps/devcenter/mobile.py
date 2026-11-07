"""What a mobile developer needs, per app, mapped onto *real* operation ids.

This only groups operations — their paths, schemas and roles still come from the live OpenAPI
schema. A feature without operations is ``PLANNED`` and is reported separately from working
endpoints. ``tests/test_devcenter.py`` fails if a listed operation id does not exist or the
app's role cannot call it.
"""

from dataclasses import dataclass

from apps.accounts.models import Role


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    operations: tuple[str, ...] = ()
    #: For PLANNED features: what is still missing.
    planned: str = ""


@dataclass(frozen=True)
class MobileApp:
    key: str
    label: str
    role: str
    features: tuple[Feature, ...]


AUTH = ("auth_login_create", "auth_refresh_create", "auth_logout_create")

USER_APP = MobileApp(
    key="user",
    label="User Mobile API",
    role=Role.USER.value,
    features=(
        Feature("registration", "Ro'yxatdan o'tish", ("auth_register_create",)),
        Feature("login", "Kirish / chiqish", AUTH[0::2]),
        Feature("token_refresh", "Token yangilash", ("auth_refresh_create",)),
        Feature("profile", "Profil", ("auth_me_retrieve", "auth_me_partial_update")),
        Feature("my_ceremonies", "Mening marosimlarim", ("me_ceremonies_list",)),
        Feature("ceremony_details", "Marosim tafsilotlari", ("me_ceremonies_retrieve",)),
        Feature(
            "invitations",
            "Takliflar",
            ("me_invitations_list", "me_invitations_accept_create", "me_invitations_decline_create"),
        ),
        Feature("photos", "Rasmlar", planned="Marosim rasmlari ro'yxati va yuklab olish API'si"),
        Feature("videos", "Videolar", planned="Marosim videolari ro'yxati va streaming/yuklab olish API'si"),
    ),
)

STUDIO_APP = MobileApp(
    key="studio",
    label="Studio Mobile API",
    role=Role.STUDIO.value,
    features=(
        Feature("login", "Kirish / token / chiqish", AUTH),
        Feature("studio_profile", "Studiya profili", ("studios_me_list", "auth_me_retrieve")),
        Feature("create_ceremony", "Marosim yaratish", ("ceremonies_create",)),
        Feature(
            "manage_ceremonies",
            "Marosimlarni boshqarish",
            ("ceremonies_list", "ceremonies_retrieve", "ceremonies_partial_update", "studios_me_ceremonies_list"),
        ),
        Feature(
            "assign_participants",
            "Kelin / kuyovni biriktirish",
            ("ceremonies_participants_list", "ceremonies_participants_create", "ceremonies_participants_destroy"),
        ),
        Feature(
            "media_upload",
            "Media yuklash",
            ("ceremonies_media_uploads_create", "ceremonies_media_uploads_complete_create"),
        ),
        Feature("upload_progress", "Yuklash jarayoni", ("ceremonies_media_uploads_retrieve", "ceremonies_media_list")),
        Feature(
            "upload_retry",
            "Yuklashni davom ettirish / bekor qilish",
            ("ceremonies_media_uploads_retrieve", "ceremonies_media_uploads_cancel_create"),
        ),
        Feature("media_management", "Media boshqaruvi", planned="Media o'chirish, tartiblash, muqova tanlash API'si"),
    ),
)

MOBILE_APPS = (USER_APP, STUDIO_APP)
