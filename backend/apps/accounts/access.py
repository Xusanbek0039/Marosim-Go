"""Access policy of an API operation, derived from the view's *real* DRF permission classes.

This is the single source of the role metadata published in OpenAPI (``x-allowed-roles``…),
the panel's API catalog and the committed access contract. It never grants anything itself —
enforcement stays in the permission classes; this module only *reads* them.

* Each permission class contributes a :class:`Grant` (who can pass it). Known classes are
  described here or by their own ``access_grant(view)`` method; ``&``/``|`` compositions are
  combined; anything else makes the policy ``REVIEW_REQUIRED`` instead of being guessed.
* ``PUBLIC`` means "no authentication needed". An authenticated endpoint is never PUBLIC.
* What permission classes cannot express — ownership / data scope, extra runtime conditions —
  is declared next to the code that enforces it, as ``access_notes`` on the view, and each
  declaration must be backed by a test (``tests/test_api_access_contract.py``).
"""

from dataclasses import dataclass, field

from rest_framework import permissions as drf

from .models import Role

PUBLIC = "PUBLIC"
#: Display / sort order of the classification (most open first).
ROLE_ORDER = (PUBLIC, Role.USER.value, Role.STUDIO.value, Role.ADMIN.value, Role.SUPER_ADMIN.value)
AUTHENTICATED_ROLES = frozenset(ROLE_ORDER[1:])

AUTH_NONE = "NONE"
AUTH_JWT = "JWT"  # Bearer (mobile) or httpOnly cookie + X-CSRFToken (web panel)
AUTH_UNKNOWN = "UNKNOWN"

DERIVED = "DERIVED"  # computed from known permission classes
REVIEW_REQUIRED = "REVIEW_REQUIRED"  # could not be derived automatically — a human must check


@dataclass(frozen=True)
class AccessNote:
    """Documentation of rules the permission classes do not express (enforced elsewhere)."""

    #: ``None`` inherits the ``"*"`` note; ``""`` explicitly means "no data scope".
    ownership: str | None = None
    conditions: tuple[str, ...] = ()


@dataclass
class Grant:
    roles: frozenset[str]
    #: role -> permission codes that role additionally needs (e.g. ADMIN -> users.view)
    requirements: dict[str, frozenset[str]] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)

    def __and__(self, other: "Grant") -> "Grant":
        roles = self.roles & other.roles
        requirements = {
            role: self.requirements.get(role, frozenset()) | other.requirements.get(role, frozenset())
            for role in roles
            if role in self.requirements or role in other.requirements
        }
        return Grant(roles, requirements, self.unknown + other.unknown)

    def __or__(self, other: "Grant") -> "Grant":
        requirements, unknown = {}, self.unknown + other.unknown
        for role in self.roles | other.roles:
            # A role passes the OR if it passes either side; it needs codes only if every side it can pass demands them.
            sides = {g.requirements.get(role, frozenset()) for g in (self, other) if role in g.roles}
            if all(sides):
                if len(sides) > 1:  # "codes A or codes B" is not expressible as one requirement
                    unknown.append(f"OR of different permission codes for {role}")
                requirements[role] = frozenset().union(*sides)
        return Grant(self.roles | other.roles, requirements, unknown)


EVERYONE = frozenset(ROLE_ORDER)


def _known_grant(permission, view) -> Grant | None:
    method = getattr(permission, "access_grant", None)
    if callable(method):
        return method(view)
    if isinstance(permission, drf.AND):
        return _grant(permission.op1, view) & _grant(permission.op2, view)
    if isinstance(permission, drf.OR):
        return _grant(permission.op1, view) | _grant(permission.op2, view)
    if type(permission) is drf.AllowAny:
        return Grant(EVERYONE)
    if type(permission) is drf.IsAuthenticated:
        return Grant(AUTHENTICATED_ROLES)
    return None


def _grant(permission, view) -> Grant:
    grant = _known_grant(permission, view)
    if grant is None:
        name = f"{type(permission).__module__}.{type(permission).__qualname__}"
        return Grant(EVERYONE, unknown=[name])  # neutral for AND; flagged below
    return grant


def _class_name(permission) -> str:
    if isinstance(permission, drf.AND | drf.OR):
        op = "&" if isinstance(permission, drf.AND) else "|"
        return f"({_class_name(permission.op1)} {op} {_class_name(permission.op2)})"
    return type(permission).__name__


def _overrides_object_permission(permission) -> bool:
    if isinstance(permission, drf.AND | drf.OR):
        return _overrides_object_permission(permission.op1) or _overrides_object_permission(permission.op2)
    impl = getattr(type(permission), "has_object_permission", None)
    return (
        impl is not None
        and impl is not drf.BasePermission.has_object_permission
        and not hasattr(permission, "access_grant")
    )


def notes_for(view, method: str) -> AccessNote:
    """``access_notes`` maps ``"*"``, an action name or a lowercase HTTP method to an :class:`AccessNote`."""
    notes = getattr(view, "access_notes", None) or {}
    base = notes.get("*", AccessNote())
    specific = notes.get(getattr(view, "action", None) or "") or notes.get(method.lower()) or AccessNote()
    return AccessNote(
        ownership=(base.ownership if specific.ownership is None else specific.ownership) or "",
        conditions=tuple(dict.fromkeys((*base.conditions, *specific.conditions))),
    )


@dataclass(frozen=True)
class AccessPolicy:
    allowed_roles: tuple[str, ...]
    auth_type: str
    required_permissions: tuple[str, ...]
    #: role -> human readable extra requirement (only for roles that need one)
    role_requirements: dict
    ownership_scope: str
    conditions: tuple[str, ...]
    permission_classes: tuple[str, ...]
    status: str
    review_reasons: tuple[str, ...]

    @property
    def is_public(self) -> bool:
        return PUBLIC in self.allowed_roles

    @property
    def label(self) -> str:
        if self.status == REVIEW_REQUIRED:
            return "Tekshirish talab qilinadi (REVIEW REQUIRED)"
        if self.is_public:
            return "Ochiq (public)"
        if set(self.allowed_roles) == AUTHENTICATED_ROLES:
            return "Har qanday tizimga kirgan foydalanuvchi"
        if self.allowed_roles == (Role.SUPER_ADMIN.value,):
            return "Faqat SUPER_ADMIN"
        if not self.allowed_roles:
            return "Hech kim (endpoint yopiq)"
        parts = [
            f"`{', '.join(sorted(self.role_requirements[r]))}` ruxsatli {r}" if r in self.role_requirements else r
            for r in reversed(self.allowed_roles)
        ]
        return " yoki ".join(parts)

    def as_dict(self) -> dict:
        return {
            "allowed_roles": list(self.allowed_roles),
            "auth_type": self.auth_type,
            "required_permissions": list(self.required_permissions),
            "role_requirements": {role: sorted(codes) for role, codes in self.role_requirements.items()},
            "ownership_scope": self.ownership_scope or None,
            "conditions": list(self.conditions),
            "permission_classes": list(self.permission_classes),
            "status": self.status,
            "review_reasons": list(self.review_reasons),
            "label": self.label,
        }


def resolve(view, method: str) -> AccessPolicy:
    perms = view.get_permissions() if hasattr(view, "get_permissions") else []
    grant = Grant(EVERYONE)
    for permission in perms:  # DRF requires every class to pass
        grant = grant & _grant(permission, view)

    reasons = [f"Noma'lum permission class: {name}" for name in grant.unknown]
    reasons += [
        f"{_class_name(p)} object-level tekshiruvga ega — `access_notes` da hujjatlashtiring"
        for p in perms
        if _overrides_object_permission(p)
    ]

    authenticators = view.get_authenticators() if hasattr(view, "get_authenticators") else []
    roles = set(grant.roles)
    if not authenticators:
        # No authentication runs: every caller is anonymous, so only a PUBLIC grant can pass.
        roles = {PUBLIC} if PUBLIC in roles else set()
    elif PUBLIC in roles:
        roles = {PUBLIC}
    if grant.unknown:
        roles = set()  # never guess — an unknown class may restrict anyone (or no one)
    elif not roles:
        reasons.append("Hech bir rol o'ta olmaydi")

    note = notes_for(view, method)
    if any(p for p in perms if _overrides_object_permission(p)) and note.ownership:
        reasons = [r for r in reasons if "object-level" not in r]

    requirements = {role: codes for role, codes in grant.requirements.items() if role in roles and codes}
    codes = sorted(set().union(*requirements.values())) if requirements else []
    ordered = tuple(r for r in ROLE_ORDER if r in roles)
    return AccessPolicy(
        allowed_roles=ordered,
        auth_type=AUTH_UNKNOWN if grant.unknown else AUTH_NONE if PUBLIC in roles else AUTH_JWT,
        required_permissions=tuple(codes),
        role_requirements=requirements,
        ownership_scope=note.ownership,
        conditions=note.conditions,
        permission_classes=tuple(_class_name(p) for p in perms),
        status=REVIEW_REQUIRED if reasons else DERIVED,
        review_reasons=tuple(reasons),
    )
