"""Role-based API contract: the published role metadata must match what the backend enforces.

1. Runtime matrix — every operation in the live OpenAPI schema is called as every caller
   (anonymous, USER, STUDIO, ADMIN without/with the required codes, SUPER_ADMIN) and the
   decision of DRF's permission layer is compared with ``x-allowed-roles``. New endpoints are
   picked up automatically.
2. Snapshot — the live metadata must equal ``contracts/api_access_contract.json``.
3. Documentation — every operation is documented and none needs manual access review.
4. Ownership — every declared ``ownership_scope`` is backed by a test listed in ``OWNERSHIP_TESTS``.
5. Resolver unit tests and "a new endpoint lands in the catalog with the right role".
"""

import re
import uuid

import pytest
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions as drf
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.accounts.access import PUBLIC, REVIEW_REQUIRED, ROLE_ORDER, AccessNote, resolve
from apps.accounts.models import Role
from apps.accounts.permissions import HasAdminPermission, IsSuperAdmin
from apps.monitoring import catalog, contract
from apps.storage import services as storage_services

from .conftest import bearer_client

ENDPOINTS = catalog.build()
CALLERS = ("ANONYMOUS", "USER", "STUDIO", "VENUE_OWNER", "ADMIN_NO_PERMS", "ADMIN_WITH_PERMS", "SUPER_ADMIN")


def expected_allowed(endpoint: dict, caller: str) -> bool:
    roles = endpoint["allowed_roles"]
    if PUBLIC in roles:
        return True
    if caller == "ANONYMOUS":
        return False
    if caller.startswith("ADMIN"):
        if "ADMIN" not in roles:
            return False
        return caller == "ADMIN_WITH_PERMS" or not endpoint["role_requirements"].get("ADMIN")
    return caller in roles


def concrete_url(template: str) -> str:
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), template)


class _NoNetworkGateway:
    def __getattr__(self, name):
        raise AssertionError(f"contract test must not call Google ({name})")


@pytest.fixture
def spy_permissions(monkeypatch):
    seen = {"checked": False, "denied": False}
    check, deny = APIView.check_permissions, APIView.permission_denied

    def check_permissions(self, request):
        seen["checked"] = True
        return check(self, request)

    def permission_denied(self, request, message=None, code=None):
        seen["denied"] = True
        return deny(self, request, message, code)

    monkeypatch.setattr(APIView, "check_permissions", check_permissions)
    monkeypatch.setattr(APIView, "permission_denied", permission_denied)
    return seen


@pytest.fixture
def no_google():
    storage_services.set_gateway(_NoNetworkGateway())
    yield
    storage_services.set_gateway(None)


def caller_client(caller: str, endpoint: dict, make_user) -> APIClient:
    if caller == "ANONYMOUS":
        client = APIClient()
    elif caller == "ADMIN_NO_PERMS":
        client = bearer_client(make_user(Role.ADMIN, admin_permissions=[]))
    elif caller == "ADMIN_WITH_PERMS":
        codes = endpoint["role_requirements"].get("ADMIN", [])
        client = bearer_client(make_user(Role.ADMIN, admin_permissions=list(codes)))
    else:
        client = bearer_client(make_user(Role(caller)))
    client.raise_request_exception = False  # this test is about the permission layer only
    return client


# ------------------------------------------------------------ 1. runtime
@pytest.mark.django_db
@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: f"{e['method']} {e['path']}")
def test_permission_layer_matches_documented_roles(endpoint, caller, make_user, spy_permissions, no_google):
    client = caller_client(caller, endpoint, make_user)
    response = client.generic(
        endpoint["method"], concrete_url(endpoint["path"]), data="{}", content_type="application/json"
    )
    allowed = expected_allowed(endpoint, caller)

    assert spy_permissions["checked"], f"permission layer never ran (status {response.status_code})"
    if allowed:
        assert not spy_permissions["denied"], (
            f"{caller} is documented as allowed but was denied ({response.status_code}) — "
            f"documented roles: {endpoint['allowed_roles']}"
        )
    else:
        assert spy_permissions["denied"], (
            f"{caller} is documented as denied but passed the permission layer ({response.status_code})"
        )
        assert response.status_code in (401, 403)


# ----------------------------------------------------------- 2. snapshot
def test_live_api_matches_reviewed_contract():
    changes = contract.diff(contract.load(), contract.current())
    assert not any(changes.values()), (
        "API access contract changed. Review the change, run `python manage.py api_contract --write`, "
        f"and add an API changelog entry.\n{changes}"
    )


# ------------------------------------------------- 3. metadata hygiene
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: f"{e['method']} {e['path']}")
def test_operation_metadata_is_consistent(endpoint):
    roles = endpoint["allowed_roles"]
    assert endpoint["access_status"] != REVIEW_REQUIRED, endpoint["review_reasons"]
    assert roles, "no role can call this operation"
    assert set(roles) <= set(ROLE_ORDER)
    assert list(roles) == [r for r in ROLE_ORDER if r in roles]
    if PUBLIC in roles:
        assert roles == [PUBLIC] and endpoint["auth_type"] == "NONE" and not endpoint["auth_required"]
    else:
        assert endpoint["auth_type"] == "JWT" and endpoint["auth_required"]
    assert set(endpoint["role_requirements"]) <= set(roles)
    assert endpoint["roles"] == roles  # legacy x-access agrees with the new extensions
    assert endpoint["api_version"] == "v1"


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: f"{e['method']} {e['path']}")
def test_operation_is_documented(endpoint):
    assert endpoint["documentation_status"] == "DOCUMENTED", endpoint["documentation_missing"]


def test_schema_exposes_role_extensions():
    op = catalog.get_schema()["paths"]["/api/v1/users/{id}/pinfl/"]["get"]
    assert op["x-allowed-roles"] == ["ADMIN", "SUPER_ADMIN"]
    assert op["x-required-permissions"] == ["users.view_pinfl"]
    assert op["x-auth-type"] == "JWT"
    assert op["x-ownership-scope"].startswith("Faqat USER, STUDIO va VENUE_OWNER")
    assert op["x-access-status"] == "DERIVED"
    assert any("PINFL_REVEAL" in c for c in op["x-access-conditions"])
    me = catalog.get_schema()["paths"]["/api/v1/auth/me/"]["get"]
    assert me["x-allowed-roles"] == ["USER", "STUDIO", "VENUE_OWNER", "ADMIN", "SUPER_ADMIN"]
    assert "403" not in me["responses"]  # any signed-in role passes


# ----------------------------------------------------------- 4. ownership
#: operation_id -> name of the test in this module that proves the declared data scope.
OWNERSHIP_TESTS = {
    **dict.fromkeys(
        [
            "users_list",
            "users_create",
            "users_retrieve",
            "users_partial_update",
            "users_destroy",
            "users_pinfl_retrieve",
            "users_verify_phone_create",
        ],
        "test_users_scope_is_client_accounts_only",
    ),
    **dict.fromkeys(
        [
            "admins_list",
            "admins_create",
            "admins_retrieve",
            "admins_partial_update",
            "admins_destroy",
            "admins_pinfl_retrieve",
            "admins_verify_phone_create",
        ],
        "test_admins_scope_is_admin_accounts_only",
    ),
    **dict.fromkeys(
        ["studios_list", "studios_create", "studios_retrieve", "studios_partial_update", "studios_destroy"],
        "test_studios_scope_excludes_deleted",
    ),
    **dict.fromkeys(["auth_me_retrieve", "auth_me_partial_update"], "test_me_is_own_account_only"),
    # ceremonies — tests live in tests/test_ceremonies.py (aliased below so they are not collected twice)
    **dict.fromkeys(
        [
            "ceremonies_list",
            "ceremonies_create",
            "ceremonies_retrieve",
            "ceremonies_partial_update",
            "ceremonies_participants_list",
            "ceremonies_participants_create",
            "ceremonies_participants_destroy",
            "studios_me_ceremonies_list",
        ],
        "ownership_ceremony_scope_is_own_studio",
    ),
    "studios_me_list": "ownership_studio_me_is_own_memberships",
    **dict.fromkeys(["me_ceremonies_list", "me_ceremonies_retrieve"], "ownership_user_ceremony_scope"),
    **dict.fromkeys(
        ["me_invitations_list", "me_invitations_accept_create", "me_invitations_decline_create"],
        "ownership_invitation_scope_is_own_phone",
    ),
    # ceremony ownership (Phase C) — tests live in tests/test_ceremony_invitations.py
    **dict.fromkeys(["ceremonies_owners_list", "ceremonies_owners_invite_create"], "ownership_studio_owner_scope"),
    **dict.fromkeys(
        [
            "me_ceremonies_members_retrieve",
            "me_ceremonies_invitations_list",
            "me_ceremonies_invitations_create",
            "me_ceremonies_owner_requests_list",
        ],
        "ownership_owner_actions_need_ownership",
    ),
    **dict.fromkeys(
        ["me_ceremonies_invitations_revoke_create", "me_ceremonies_invitations_resend_create"],
        "ownership_nested_ids_scoped_to_ceremony",
    ),
    "me_ceremonies_viewers_revoke_create": "ownership_owner_revokes_only_own_grants",
    **dict.fromkeys(
        ["me_ceremonies_owner_requests_approve_create", "me_ceremonies_owner_requests_reject_create"],
        "ownership_owner_request_votes",
    ),
    "me_ceremonies_leave_create": "ownership_leave_is_own_access",
    "me_invitations_retrieve": "ownership_invitation_detail_is_recipient_only",
    # media (Phase D) — tests live in tests/test_media_upload.py
    **dict.fromkeys(
        [
            "ceremonies_media_list",
            "ceremonies_media_uploads_create",
            "ceremonies_media_uploads_retrieve",
            "ceremonies_media_uploads_complete_create",
            "ceremonies_media_uploads_cancel_create",
        ],
        "ownership_media_scope_is_own_studio",
    ),
    # couple / guest media (Phase E) — tests live in tests/test_media_sharing.py
    **dict.fromkeys(
        [
            "me_ceremonies_media_list",
            "me_ceremonies_media_thumbnail_retrieve",
            "me_ceremonies_media_stream_retrieve",
            "me_ceremonies_media_download_retrieve",
        ],
        "ownership_member_media_scope",
    ),
    # venue panel + gallery — tests live in tests/test_admin_venues.py
    **dict.fromkeys(
        [
            "admin_venues_list",
            "admin_venues_create",
            "admin_venues_retrieve",
            "admin_venues_partial_update",
            "admin_venues_destroy",
            "admin_venues_halls_create",
            "admin_venues_halls_partial_update",
            "admin_venues_images_create",
            "admin_venues_images_destroy",
        ],
        "ownership_admin_venues_all",
    ),
    **dict.fromkeys(
        ["venue_owner_venues_images_list", "venue_owner_venues_images_create", "venue_owner_venues_images_destroy"],
        "ownership_venue_gallery_by_membership",
    ),
    # venues — tests live in tests/test_venues.py
    **dict.fromkeys(
        [
            "venue_owner_venues_list",
            "venue_owner_venues_retrieve",
            "venue_owner_venues_partial_update",
            "venue_owner_venues_halls_list",
            "venue_owner_venues_halls_create",
            "venue_owner_venues_halls_partial_update",
            "venue_owner_venues_members_list",
            "venue_owner_venues_members_create",
            "venue_owner_venues_members_partial_update",
        ],
        "ownership_venue_scope_is_own_membership",
    ),
    # hall sessions + bookings — tests live in tests/test_venue_bookings.py
    **dict.fromkeys(
        [
            "me_venue_bookings_list",
            "me_venue_bookings_retrieve",
            "me_venue_bookings_cancel_create",
            "venue_owner_venues_bookings_list",
            "venue_owner_venues_bookings_create",
            "venue_owner_venues_bookings_partial_update",
            "venue_owner_venues_bookings_confirm_create",
            "venue_owner_venues_bookings_reject_create",
            "venue_owner_venues_bookings_cancel_create",
            "venue_owner_venues_calendar_retrieve",
            "venue_owner_venues_halls_sessions_list",
            "venue_owner_venues_halls_sessions_create",
            "venue_owner_venues_halls_sessions_partial_update",
        ],
        "ownership_hall_booking_scope",
    ),
}

from . import test_ceremonies as _ceremony_tests  # noqa: E402

ownership_ceremony_scope_is_own_studio = _ceremony_tests.test_ceremony_scope_is_own_studio
ownership_studio_me_is_own_memberships = _ceremony_tests.test_studio_me_lists_own_memberships_only
ownership_user_ceremony_scope = _ceremony_tests.test_user_ceremony_scope_is_own_participation
ownership_invitation_scope_is_own_phone = _ceremony_tests.test_invitation_scope_is_own_phone

from . import test_ceremony_invitations as _ownership_tests  # noqa: E402

ownership_studio_owner_scope = _ownership_tests.test_cross_ceremony_and_cross_studio_denied
ownership_owner_actions_need_ownership = _ownership_tests.test_viewer_cannot_invite_promote_or_manage
ownership_nested_ids_scoped_to_ceremony = _ownership_tests.test_other_ceremony_ids_do_not_leak_through_nested_routes
ownership_owner_revokes_only_own_grants = _ownership_tests.test_owner_cannot_revoke_unrelated_access
ownership_owner_request_votes = _ownership_tests.test_multiple_owners_need_existing_owner_approval
ownership_leave_is_own_access = _ownership_tests.test_leaving_owner_takes_their_pending_invitations_and_votes_along
ownership_invitation_detail_is_recipient_only = _ownership_tests.test_wrong_user_cannot_see_or_accept_invitation

from . import test_media_upload as _media_tests  # noqa: E402

ownership_media_scope_is_own_studio = _media_tests.test_upload_scope_and_roles

from . import test_media_sharing as _sharing_tests  # noqa: E402

ownership_member_media_scope = _sharing_tests.test_strangers_studio_and_other_ceremonies_get_404

from . import test_venues as _venue_tests  # noqa: E402

ownership_venue_scope_is_own_membership = _venue_tests.test_venue_scope_is_own_membership

from . import test_admin_venues as _admin_venue_tests  # noqa: E402

ownership_admin_venues_all = _admin_venue_tests.test_admin_venue_rights_come_only_from_granted_codes
ownership_venue_gallery_by_membership = _admin_venue_tests.test_gallery_rights_follow_membership

from . import test_venue_bookings as _booking_tests  # noqa: E402

ownership_hall_booking_scope = _booking_tests.test_booking_scope_is_own


@pytest.mark.parametrize(
    "endpoint", [e for e in ENDPOINTS if e["ownership_scope"]], ids=lambda e: f"{e['method']} {e['path']}"
)
def test_every_ownership_scope_has_a_test(endpoint):
    name = OWNERSHIP_TESTS.get(endpoint["id"])
    assert name, f"{endpoint['id']} declares ownership_scope but no test is registered in OWNERSHIP_TESTS"
    assert callable(globals().get(name)), f"{name} does not exist"


@pytest.mark.django_db
def test_users_scope_is_client_accounts_only(super_admin, admin_user, plain_user, studio_user, client_for):
    client = client_for(super_admin)
    listed = {row["id"] for row in client.get("/api/v1/users/?page_size=100").data["results"]}
    assert {str(plain_user.pk), str(studio_user.pk)} <= listed
    assert not listed & {str(admin_user.pk), str(super_admin.pk)}
    for staff in (admin_user, super_admin):
        url = f"/api/v1/users/{staff.pk}/"
        assert client.get(url).status_code == 404
        assert client.patch(url, {"address": "x"}, format="json").status_code == 404
        assert client.delete(url).status_code == 404
        assert client.get(f"{url}pinfl/").status_code == 404
        assert client.post(f"{url}verify-phone/").status_code == 404
    res = client.post("/api/v1/users/", {"role": "ADMIN", "phone_number": "+998977777777"}, format="json")
    assert res.status_code == 400 and "role" in res.data["error"]["details"]


@pytest.mark.django_db
def test_admins_scope_is_admin_accounts_only(super_admin, admin_user, plain_user, client_for):
    client = client_for(super_admin)
    listed = {row["id"] for row in client.get("/api/v1/admins/?page_size=100").data["results"]}
    assert listed == {str(admin_user.pk)}
    for other in (plain_user, super_admin):
        url = f"/api/v1/admins/{other.pk}/"
        assert client.get(url).status_code == 404
        assert client.patch(url, {"address": "x"}, format="json").status_code == 404
        assert client.delete(url).status_code == 404
        assert client.get(f"{url}pinfl/").status_code == 404
        assert client.post(f"{url}verify-phone/").status_code == 404
    res = client.post(
        "/api/v1/admins/",
        {
            "role": "SUPER_ADMIN",
            "phone_number": "+998977777778",
            "first_name": "A",
            "last_name": "B",
            "password": "Xavfsiz-Parol-2026",
            "password_confirm": "Xavfsiz-Parol-2026",
        },
        format="json",
    )
    if res.status_code == 201:
        assert res.data["role"] == "ADMIN"
    else:
        assert res.status_code == 400


@pytest.mark.django_db
def test_studios_scope_excludes_deleted(super_admin, studio_user, make_studio, client_for):
    client = client_for(super_admin)
    live, gone = make_studio(studio_user, name="Live"), make_studio(studio_user, name="Gone")
    gone.soft_delete()
    listed = {row["id"] for row in client.get("/api/v1/studios/?page_size=100").data["results"]}
    assert str(live.pk) in listed and str(gone.pk) not in listed
    url = f"/api/v1/studios/{gone.pk}/"
    assert client.get(url).status_code == 404
    assert client.patch(url, {"address": "x"}, format="json").status_code == 404
    assert client.delete(url).status_code == 404
    res = client.post("/api/v1/studios/", {"name": "N", "address": "A", "responsible_user": str(uuid.uuid4())})
    assert res.status_code == 400  # cannot attach a studio to an arbitrary / unknown account


@pytest.mark.django_db
def test_me_is_own_account_only(plain_user, studio_user, client_for):
    client = client_for(plain_user)
    assert client.get("/api/v1/auth/me/").data["id"] == str(plain_user.pk)
    res = client.patch(
        "/api/v1/auth/me/", {"address": "Yangi", "id": str(studio_user.pk), "role": "ADMIN"}, format="json"
    )
    assert res.status_code == 200 and res.data["id"] == str(plain_user.pk)
    plain_user.refresh_from_db()
    studio_user.refresh_from_db()
    assert plain_user.address == "Yangi" and plain_user.role == Role.USER
    assert studio_user.address != "Yangi"


# ------------------------------------------------- 5. resolver behaviour
def _view(*perms, authentication=None, notes=None, **attrs):
    cls = type("ProbeView", (APIView,), {"permission_classes": list(perms), "access_notes": notes, **attrs})
    if authentication is not None:
        cls.authentication_classes = authentication
    return cls()


class SecretHeader(drf.BasePermission):
    def has_permission(self, request, view):
        return request.headers.get("X-Secret") == "1"


class OwnObject(drf.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


def test_resolver_combinations():
    assert resolve(_view(drf.AllowAny, authentication=[]), "GET").allowed_roles == (PUBLIC,)
    assert resolve(_view(drf.AllowAny), "GET").auth_type == "NONE"
    assert resolve(_view(drf.IsAuthenticated), "GET").allowed_roles == ROLE_ORDER[1:]
    assert resolve(_view(drf.IsAuthenticated, IsSuperAdmin), "GET").allowed_roles == ("SUPER_ADMIN",)
    assert resolve(_view(drf.IsAuthenticated & IsSuperAdmin), "GET").allowed_roles == ("SUPER_ADMIN",)
    assert resolve(_view(drf.AllowAny | IsSuperAdmin), "GET").allowed_roles == (PUBLIC,)

    admin = resolve(_view(HasAdminPermission, required_permission="users.view"), "GET")
    assert admin.allowed_roles == ("ADMIN", "SUPER_ADMIN")
    assert admin.role_requirements == {"ADMIN": frozenset({"users.view"})}
    assert admin.required_permissions == ("users.view",)
    assert resolve(_view(HasAdminPermission), "GET").allowed_roles == ("SUPER_ADMIN",)  # no code: SA only

    either = resolve(_view(IsSuperAdmin | HasAdminPermission, required_permission="users.view"), "GET")
    assert either.allowed_roles == ("ADMIN", "SUPER_ADMIN")
    assert either.role_requirements == {"ADMIN": frozenset({"users.view"})}


def test_resolver_never_guesses():
    unknown = resolve(_view(SecretHeader), "GET")
    assert unknown.status == REVIEW_REQUIRED and unknown.allowed_roles == () and unknown.auth_type == "UNKNOWN"
    assert "SecretHeader" in unknown.review_reasons[0]

    # Allowing anyone but running no authentication cannot be "authenticated"; requiring auth without
    # any authenticator is unreachable — both are flagged rather than published as something else.
    unreachable = resolve(_view(drf.IsAuthenticated, authentication=[]), "GET")
    assert unreachable.status == REVIEW_REQUIRED and unreachable.allowed_roles == ()

    object_level = resolve(_view(OwnObject), "GET")
    assert object_level.status == REVIEW_REQUIRED
    documented = resolve(_view(OwnObject, notes={"*": AccessNote(ownership="Faqat egasi")}), "GET")
    assert documented.status == "DERIVED" and documented.ownership_scope == "Faqat egasi"


def test_access_notes_per_action_and_method():
    notes = {
        "*": AccessNote(ownership="Hammasi", conditions=("umumiy",)),
        "patch": AccessNote(conditions=("faqat patch",)),
        "permissions": AccessNote(ownership=""),
    }
    view = _view(drf.IsAuthenticated, notes=notes)
    assert resolve(view, "GET").ownership_scope == "Hammasi"
    assert resolve(view, "PATCH").conditions == ("umumiy", "faqat patch")
    view.action = "permissions"
    assert resolve(view, "GET").ownership_scope == ""


# --------------------------------- 6. new endpoints land in the catalog
Probe = inline_serializer("ContractProbe", fields={"ok": serializers.BooleanField()})


class NewSuperAdminView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(summary="Yangi endpoint", responses=Probe)
    def get(self, request):
        return Response({"ok": True})


class UndocumentedView(APIView):
    def get(self, request):
        return Response({})


class UnknownPermissionView(APIView):
    permission_classes = [SecretHeader]

    @extend_schema(summary="Noma'lum ruxsat", responses=Probe)
    def get(self, request):
        return Response({"ok": True})


def test_new_endpoint_is_catalogued_with_its_role():
    patterns = [
        path("api/v1/probe/new/", NewSuperAdminView.as_view()),
        path("api/v1/probe/undocumented/", UndocumentedView.as_view()),
        path("api/v1/probe/unknown/", UnknownPermissionView.as_view()),
    ]
    schema = SchemaGenerator(patterns=patterns).get_schema(request=None, public=True)
    by_path = {e["path"]: e for e in catalog.build(schema)}

    new = by_path["/api/v1/probe/new/"]
    assert new["allowed_roles"] == ["SUPER_ADMIN"] and new["documentation_status"] == "DOCUMENTED"
    assert new["access_status"] == "DERIVED"

    undocumented = by_path["/api/v1/probe/undocumented/"]
    assert undocumented["documentation_status"] == "MISSING"
    assert undocumented["allowed_roles"] == ["USER", "STUDIO", "VENUE_OWNER", "ADMIN", "SUPER_ADMIN"]  # DRF default

    unknown = by_path["/api/v1/probe/unknown/"]
    assert unknown["access_status"] == REVIEW_REQUIRED and unknown["allowed_roles"] == []

    live = contract.current(schema)
    assert contract.status_of(live["GET /api/v1/probe/new/"], contract.load(), "GET /api/v1/probe/new/") == (
        contract.NOT_IN_CONTRACT
    )
    assert contract.diff(contract.load(), live)["added"]  # → the snapshot test would fail in CI


@pytest.mark.django_db
def test_catalog_api_reports_contract_status(super_admin, client_for):
    data = client_for(super_admin).get("/api/v1/monitoring/endpoints/").data
    assert {e["contract_status"] for e in data["results"]} == {contract.MATCHES}
    me = next(e for e in data["results"] if e["path"] == "/api/v1/auth/me/" and e["method"] == "GET")
    assert me["allowed_roles"] == ["USER", "STUDIO", "VENUE_OWNER", "ADMIN", "SUPER_ADMIN"]
    assert me["ownership_scope"] and me["documentation_status"] == "DOCUMENTED"
    # "documented" and "matches contract" are not "healthy": traffic status is reported separately.
    assert me["status"] in {"idle", "healthy", "degraded", "failing"}
