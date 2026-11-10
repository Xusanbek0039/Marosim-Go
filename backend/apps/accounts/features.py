"""Role capability switches, checked on the server on every business API request."""

from rest_framework.exceptions import PermissionDenied

from .models import PlatformPolicy, Role

FEATURE_LABELS = {
    "registration": "Ro'yxatdan o'tish",
    "ceremonies": "Marosimlar va takliflar",
    "sharing": "Media ulashish va ko'ruvchilar",
    "media": "Foto va video",
    "portfolio": "Studiya portfoliosi",
    "venues": "To'yxona va jadval boshqaruvi",
    "bookings": "To'yxonaga bron so'rovlari",
    "reviews": "Sharh va like qoldirish",
    "subscriptions": "Obuna / galichka sotib olish",
    "support": "Yordamga murojaat qilish",
}
ROLE_FEATURES = {
    "PUBLIC": ("registration",),
    Role.USER: ("ceremonies", "sharing", "media", "bookings", "reviews", "subscriptions", "support"),
    Role.STUDIO: ("ceremonies", "media", "portfolio", "subscriptions", "support"),
    Role.VENUE_OWNER: ("venues", "subscriptions", "support"),
}
FEATURE_CODES = {f"{role}.{feature}" for role, features in ROLE_FEATURES.items() for feature in features}


def feature_of(view):
    parts = type(view).__module__.split(".")
    if len(parts) < 2:
        return None
    module = parts[1]
    name = type(view).__name__
    if module == "accounts" and name == "RegisterView":
        return "registration"
    if module == "venues":
        return "bookings" if name == "MyVenueBookingViewSet" else "venues"
    if module == "studios":
        return "portfolio"
    if module == "ceremonies":
        action = getattr(view, "action", None)
        if action in {
            "members",
            "invitations",
            "invitation_revoke",
            "invitation_resend",
            "viewer_revoke",
            "owner_requests",
            "owner_request_approve",
            "owner_request_reject",
        }:
            return "sharing"
        return "ceremonies"
    return {"media": "media", "reviews": "reviews", "subscriptions": "subscriptions", "support": "support"}.get(module)


def ensure_feature(request, view):
    role = request.user.role if request.user and request.user.is_authenticated else "PUBLIC"
    # Staff tools remain available to restore a capability, moderate and resolve payments.
    if role in (Role.SUPER_ADMIN, Role.ADMIN):
        return True
    feature = feature_of(view)
    if feature == "subscriptions" and getattr(view, "action", None) != "create":
        return True  # existing purchases, payment instructions and cancellation remain available
    if not feature:
        return True
    code = f"{role}.{feature}"
    if code in PlatformPolicy.load().disabled_features:
        raise PermissionDenied("Bu imkoniyat platforma boshqaruvi tomonidan vaqtincha o'chirilgan.")
    if role != "PUBLIC" and code in (request.user.disabled_features or ()):
        raise PermissionDenied("Bu imkoniyat hisobingiz uchun administrator tomonidan o'chirilgan.")
    return True


def account_codes(user) -> tuple[str, ...]:
    """Feature codes that apply to ``user``'s role (empty for staff accounts)."""
    return tuple(f"{user.role}.{feature}" for feature in ROLE_FEATURES.get(user.role, ()))


def account_catalog(user):
    """Per-account switches: ``enabled`` (this account) and ``platform_enabled`` (the role-wide switch)."""
    disabled = set(PlatformPolicy.load().disabled_features)
    mine = set(user.disabled_features or ())
    return [
        {
            "code": code,
            "role": user.role,
            "label": FEATURE_LABELS[code.split(".", 1)[1]],
            "enabled": code not in mine,
            "platform_enabled": code not in disabled,
        }
        for code in account_codes(user)
    ]


def catalog():
    disabled = set(PlatformPolicy.load().disabled_features)
    return [
        {
            "code": f"{role}.{feature}",
            "role": role,
            "label": FEATURE_LABELS[feature],
            "enabled": f"{role}.{feature}" not in disabled,
        }
        for role, features in ROLE_FEATURES.items()
        for feature in features
    ]
