"""API Developer Center (Phase 3): role sections, mobile guide, changelog."""

import pytest

from apps.accounts.access import PUBLIC, ROLE_ORDER
from apps.accounts.models import Role
from apps.devcenter.mobile import MOBILE_APPS
from apps.devcenter.planned import CEREMONY_OWNER, CEREMONY_VIEWER, PLANNED_ENDPOINTS
from apps.monitoring import catalog, contract

BASE = "/api/v1/devcenter"
URLS = [f"{BASE}/overview/", f"{BASE}/endpoints/", f"{BASE}/mobile/", f"{BASE}/changelog/"]


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS)
def test_devcenter_is_super_admin_only(url, make_user, client_for, anon):
    assert anon.get(url).status_code == 401
    for role in (Role.USER, Role.STUDIO):
        assert client_for(make_user(role)).get(url).status_code == 403
    every_code = ["dashboard.view", "users.view", "studios.view"]
    assert client_for(make_user(Role.ADMIN, admin_permissions=every_code)).get(url).status_code == 403
    assert client_for(make_user(Role.SUPER_ADMIN)).get(url).status_code == 200


@pytest.mark.django_db
def test_overview_counts_come_from_the_schema(super_admin, client_for):
    data = client_for(super_admin).get(f"{BASE}/overview/").data
    endpoints = catalog.build()
    assert data["totals"]["operations"] == len(endpoints)
    assert data["totals"]["documented"] + data["totals"]["documentation_missing"] == len(endpoints)
    by_role = {r["role"]: r["count"] for r in data["roles"]}
    assert list(by_role) == list(ROLE_ORDER)
    for role in ROLE_ORDER:
        assert by_role[role] == sum(role in e["allowed_roles"] for e in endpoints)
    assert data["versions"] == ["v1"]
    assert data["last_change"]["revision"] == len(contract.load_changelog())


@pytest.mark.django_db
@pytest.mark.parametrize("role", ROLE_ORDER)
def test_endpoints_grouped_by_role(role, super_admin, client_for):
    data = client_for(super_admin).get(f"{BASE}/endpoints/", {"role": role}).data
    expected = {e["id"] for e in catalog.build() if role in e["allowed_roles"]}
    assert {e["id"] for e in data["results"]} == expected and data["count"] == len(expected)
    assert all("traffic_24h" in e and "contract_status" in e for e in data["results"])


@pytest.mark.django_db
def test_shared_endpoint_appears_in_every_role_section(super_admin, client_for):
    client = client_for(super_admin)
    for role in ("USER", "STUDIO", "ADMIN", "SUPER_ADMIN"):
        ids = {e["id"] for e in client.get(f"{BASE}/endpoints/", {"role": role}).data["results"]}
        assert "auth_me_retrieve" in ids
    public = {e["id"] for e in client.get(f"{BASE}/endpoints/", {"role": PUBLIC}).data["results"]}
    assert "auth_me_retrieve" not in public and "auth_login_create" in public


@pytest.mark.django_db
def test_unknown_role_is_rejected(super_admin, client_for):
    res = client_for(super_admin).get(f"{BASE}/endpoints/", {"role": "ROOT"})
    assert res.status_code == 400 and "role" in res.data["error"]["details"]


# ------------------------------------------------------------------ mobile
def test_mobile_guide_only_references_real_operations_the_role_can_call():
    by_id = {e["id"]: e for e in catalog.build()}
    for app in MOBILE_APPS:
        for feature in app.features:
            assert bool(feature.operations) != bool(feature.planned), f"{feature.key}: operations XOR planned"
            for op in feature.operations:
                assert op in by_id, f"{app.key}.{feature.key}: {op} does not exist"
                roles = by_id[op]["allowed_roles"]
                assert PUBLIC in roles or app.role in roles, f"{app.role} cannot call {op} ({roles})"


@pytest.mark.django_db
def test_mobile_guide_separates_planned_from_available(super_admin, client_for):
    apps = {a["key"]: a for a in client_for(super_admin).get(f"{BASE}/mobile/").data["apps"]}
    assert set(apps) == {"user", "studio"}
    for app in apps.values():
        for feature in app["features"]:
            assert feature["status"] in {"AVAILABLE", "PLANNED"}
            if feature["status"] == "PLANNED":
                assert feature["operations"] == [] and feature["planned"]
            else:
                assert feature["operations"] and not feature["missing_operations"]
    user = {f["key"]: f for f in apps["user"]["features"]}
    assert user["login"]["status"] == "AVAILABLE" and user["photos"]["status"] == "PLANNED"
    studio = {f["key"]: f for f in apps["studio"]["features"]}
    assert studio["media_upload"]["status"] == "PLANNED"
    assert {o["id"] for o in studio["create_ceremony"]["operations"]} == {"ceremonies_create"}


# --------------------------------------------------------------- changelog
def test_changelog_replays_to_the_contract():
    entries = contract.load_changelog()
    assert entries, "run `python manage.py api_contract --write` to create the baseline"
    assert [e["revision"] for e in entries] == list(range(1, len(entries) + 1))
    assert contract.replay(entries) == set(contract.load())


def test_changelog_entry_flags_breaking_and_schema_changes():
    changes = {
        "added": ["GET /api/v1/new/"],
        "removed": ["GET /api/v1/old/"],
        "changed": {
            "GET /api/v1/a/": {"allowed_roles": {"from": ["USER"], "to": ["ADMIN"]}},
            "GET /api/v1/b/": {"schema_fingerprint": {"from": "1", "to": "2"}},
        },
    }
    entry = contract.changelog_entry(changes, revision=7, date="2026-11-07", note="test")
    assert entry["breaking"] == ["GET /api/v1/a/", "GET /api/v1/old/"]
    assert entry["schema_changed"] == ["GET /api/v1/b/"]
    assert entry["changed"] == {"GET /api/v1/a/": ["allowed_roles"], "GET /api/v1/b/": ["schema_fingerprint"]}


def test_append_changelog(tmp_path):
    path = tmp_path / "log.json"
    contract.append_changelog({"revision": 1, "added": ["A"], "removed": []}, path)
    contract.append_changelog({"revision": 2, "added": ["B"], "removed": ["A"]}, path)
    assert contract.replay(contract.load_changelog(path)) == {"B"}


@pytest.mark.django_db
def test_changelog_api_newest_first(super_admin, client_for):
    data = client_for(super_admin).get(f"{BASE}/changelog/").data
    revisions = [e["revision"] for e in data["results"]]
    assert revisions == sorted(revisions, reverse=True) and data["count"] == len(revisions)


def _route(path: str) -> str:
    import re

    return re.sub(r"\{[^}]+\}", "{}", path)


def test_planned_endpoints_are_not_live_and_use_known_roles():
    """A shipped endpoint must leave the planned list; planned and live never overlap."""
    live = {(e["method"], _route(e["path"])) for e in catalog.build()}
    known_roles = set(ROLE_ORDER) | {CEREMONY_OWNER, CEREMONY_VIEWER}
    seen = set()
    for p in PLANNED_ENDPOINTS:
        key = (p.method, _route(p.path))
        assert key not in live, f"{p.method} {p.path} is live — remove it from apps/devcenter/planned.py"
        assert key not in seen, f"duplicate planned entry {key}"
        seen.add(key)
        assert p.path.startswith("/api/v1/") and p.path.endswith("/")
        assert set(p.roles) <= known_roles and p.roles
