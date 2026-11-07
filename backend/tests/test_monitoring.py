import json
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.monitoring import catalog
from apps.monitoring.middleware import route_template, safe_path
from apps.monitoring.models import ErrorCategory, RequestLog
from apps.monitoring.writer import prune

from .conftest import PASSWORD

OVERVIEW = "/api/v1/monitoring/overview/"
LOGS = "/api/v1/monitoring/logs/"
ENDPOINTS = "/api/v1/monitoring/endpoints/"
LIVE = "/api/v1/health/live/"
READY = "/api/v1/health/ready/"


@pytest.fixture(autouse=True)
def _fresh_catalog():
    catalog.reset_cache()
    yield


# --------------------------------------------------------------------- RBAC
@pytest.mark.django_db
@pytest.mark.parametrize("url", [OVERVIEW, LOGS, ENDPOINTS])
def test_monitoring_is_super_admin_only(url, make_user, client_for, anon):
    full_admin = make_user(Role.ADMIN, admin_permissions=["dashboard.view", "users.view", "users.view_pinfl"])
    assert anon.get(url).status_code == 401
    for role_user in (full_admin, make_user(Role.STUDIO), make_user(Role.USER)):
        assert client_for(role_user).get(url).status_code == 403


@pytest.mark.django_db
def test_super_admin_reads_monitoring(super_admin, client_for):
    client = client_for(super_admin)
    for url in (OVERVIEW, LOGS, ENDPOINTS):
        assert client.get(url).status_code == 200


# ---------------------------------------------------------------- recording
@pytest.mark.django_db
def test_requests_are_recorded_with_route_status_and_user(plain_user, client_for, anon):
    client_for(plain_user).get("/api/v1/auth/me/")
    anon.get("/api/v1/users/")
    anon.get("/api/v1/does-not-exist/")

    me = RequestLog.objects.get(path="/api/v1/auth/me/")
    assert me.method == "GET" and me.status_code == 200 and me.route == "/api/v1/auth/me/"
    assert me.user_id == plain_user.pk and me.error_category == ErrorCategory.NONE
    assert me.duration_ms >= 0 and me.request_id

    denied = RequestLog.objects.get(path="/api/v1/users/")
    assert (
        denied.status_code == 401 and denied.error_category == ErrorCategory.AUTHENTICATION and denied.user_id is None
    )

    missing = RequestLog.objects.get(path="/api/v1/does-not-exist/")
    assert missing.status_code == 404 and missing.route == ""


@pytest.mark.django_db
def test_request_id_header_matches_log(anon):
    res = anon.get(LIVE)
    assert res["X-Request-ID"]
    res = anon.get("/api/v1/auth/me/")
    assert str(RequestLog.objects.get(path="/api/v1/auth/me/").request_id) == res["X-Request-ID"]


@pytest.mark.django_db
def test_probes_and_monitoring_are_not_recorded(super_admin, client_for, anon):
    anon.get(LIVE)
    anon.get(READY)
    client_for(super_admin).get(OVERVIEW)
    assert not RequestLog.objects.exists()


@pytest.mark.django_db
def test_route_template_for_detail_routes(super_admin, plain_user, client_for):
    client_for(super_admin).get(f"/api/v1/users/{plain_user.pk}/")
    log = RequestLog.objects.get(path=f"/api/v1/users/{plain_user.pk}/")
    assert log.route == "/api/v1/users/{id}/"
    # ...which is exactly how the OpenAPI catalog spells the path
    assert any(e["path"] == log.route and e["method"] == "GET" for e in catalog.build())


def test_route_template_conversions():
    match = mock.Mock(route="api/v1/^users/(?P<pk>[^/.]+)/pinfl/$")
    assert route_template(match) == "/api/v1/users/{id}/pinfl/"
    assert route_template(mock.Mock(route="api/v1/things/<uuid:thing_id>/")) == "/api/v1/things/{thing_id}/"
    assert route_template(None) == ""


def test_safe_path_masks_identifiers_in_urls():
    assert safe_path("/api/v1/users/31201990123456/") == "/api/v1/users/[redacted]/"
    assert safe_path("/api/v1/x/+998901234567/") == "/api/v1/x/[redacted]/"
    for uuid_path in (
        "/api/v1/users/3fa85f64-5717-4562-b3fc-2c963f66afa6/",
        "/api/v1/users/086a0e33-cde3-45ac-91fc-177288345709/",  # all-digit last segment
    ):
        assert safe_path(uuid_path) == uuid_path


@pytest.mark.django_db
def test_sensitive_data_never_reaches_request_logs(make_user, anon):
    user = make_user(phone_number="+998901234567", pinfl="31201990123456")
    client = APIClient(HTTP_X_CLIENT="mobile")
    tokens = client.post(
        "/api/v1/auth/login/", {"phone_number": "+998901234567", "password": PASSWORD}, format="json"
    ).data
    client.post("/api/v1/auth/login/", {"phone_number": "+998901234567", "password": "Wrong-Secret-77"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}", HTTP_COOKIE="mg_access=cookie-secret")
    client.get("/api/v1/auth/me/?search=31201990123456&token=abc")
    client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    anon.get("/api/v1/users/31201990123456/")

    rows = list(RequestLog.objects.values())
    assert len(rows) == 5
    dump = json.dumps(rows, default=str)
    for secret in (
        PASSWORD,
        "Wrong-Secret-77",
        tokens["access"],
        tokens["refresh"],
        "cookie-secret",
        "31201990123456",
        "+998901234567",
        "998901234567",
        "search=",
        "Bearer",
        user.email,
    ):
        assert secret not in dump, secret
    assert set(rows[0]) == {
        "id",
        "created_at",
        "method",
        "path",
        "route",
        "status_code",
        "duration_ms",
        "request_id",
        "user_id",
        "error_category",
    }


@pytest.mark.django_db
def test_monitoring_failure_never_breaks_requests(plain_user, client_for):
    with mock.patch("apps.monitoring.writer.RequestLog.objects.bulk_create", side_effect=RuntimeError("db down")):
        assert client_for(plain_user).get("/api/v1/auth/me/").status_code == 200


# ------------------------------------------------------------------- stats
def _log(**extra):
    defaults = {
        "created_at": timezone.now(),
        "method": "GET",
        "path": "/api/v1/auth/me/",
        "route": "/api/v1/auth/me/",
        "status_code": 200,
        "duration_ms": 10.0,
        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    }
    return RequestLog(**{**defaults, **extra})


@pytest.mark.django_db
def test_overview_numbers_come_from_real_rows(super_admin, client_for):
    client = client_for(super_admin)
    empty = client.get(OVERVIEW).data["totals"]
    assert empty["total"] == 0 and empty["p95_ms"] is None and empty["avg_ms"] is None

    durations = list(range(1, 21))  # 1..20 ms
    rows = [_log(duration_ms=float(d)) for d in durations[:17]]
    rows += [_log(status_code=404, duration_ms=18.0), _log(status_code=429, duration_ms=19.0)]
    rows += [_log(status_code=500, duration_ms=20.0, route="/api/v1/users/")]
    rows.append(_log(created_at=timezone.now() - timedelta(days=3)))  # outside the 1h window
    RequestLog.objects.bulk_create(rows)

    data = client.get(OVERVIEW, {"window": "1h"}).data
    totals = data["totals"]
    assert totals["total"] == 20
    assert totals["success"] == 17 and totals["client_errors"] == 2 and totals["server_errors"] == 1
    assert totals["throttled"] == 1
    assert totals["avg_ms"] == 10.5
    assert totals["p95_ms"] == 19.0
    assert totals["rpm"] == round(20 / 60, 2)
    assert totals["active_endpoints"] == 2
    assert totals["documented_endpoints"] == len(catalog.build())
    assert sum(point["total"] for point in data["series"]) == 20
    assert data["top_endpoints"][0]["route"] == "/api/v1/auth/me/"

    assert client.get(OVERVIEW, {"window": "7d"}).data["totals"]["total"] == 21


@pytest.mark.django_db
def test_overview_reports_login_security_events(super_admin, plain_user, client_for):
    client = APIClient(HTTP_X_CLIENT="mobile")
    client.post("/api/v1/auth/login/", {"phone_number": plain_user.phone_number, "password": "x" * 12}, format="json")
    security = client_for(super_admin).get(OVERVIEW).data["security"]
    assert security["failed_logins"] == 1


@pytest.mark.django_db
def test_logs_filters(super_admin, client_for):
    RequestLog.objects.bulk_create(
        [_log(), _log(status_code=503, method="POST", path="/api/v1/studios/", route="/api/v1/studios/")]
    )
    client = client_for(super_admin)
    assert client.get(LOGS).data["count"] == 2
    res = client.get(LOGS, {"status_class": "5xx"})
    assert res.data["count"] == 1 and res.data["results"][0]["status_code"] == 503
    assert client.get(LOGS, {"method": "POST", "path": "studios"}).data["count"] == 1
    assert client.get(LOGS, {"status_class": "4xx"}).data["count"] == 0
    first = res.data["results"][0]
    assert {
        "timestamp",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "request_id",
        "user_id",
        "error_category",
    } <= set(first)


@pytest.mark.django_db
def test_retention_prunes_old_rows(settings):
    settings.MONITORING = {**settings.MONITORING, "RETENTION_DAYS": 7, "MAX_ROWS": 3}
    RequestLog.objects.bulk_create([_log(created_at=timezone.now() - timedelta(days=8))] + [_log() for _ in range(5)])
    assert prune() == 3  # 1 expired + 2 above the row cap
    assert RequestLog.objects.count() == 3


# ----------------------------------------------------------------- catalog
@pytest.mark.django_db
def test_endpoint_catalog_is_generated_from_openapi(super_admin, client_for):
    data = client_for(super_admin).get(ENDPOINTS).data
    by_key = {(e["method"], e["path"]): e for e in data["results"]}
    assert data["count"] == len(data["results"]) > 20

    register = by_key[("POST", "/api/v1/auth/register/")]
    assert register["auth_required"] is False
    assert register["request_example"] == {
        "phone_number": "+998901234567",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
    }
    assert 400 in {r["status"] for r in register["responses"]}

    admins = by_key[("GET", "/api/v1/admins/")]
    assert admins["roles"] == ["SUPER_ADMIN"] and admins["auth_required"] is True

    pinfl = by_key[("GET", "/api/v1/users/{id}/pinfl/")]
    assert pinfl["permission"] == "users.view_pinfl"

    monitoring = by_key[("GET", "/api/v1/monitoring/overview/")]
    assert monitoring["roles"] == ["SUPER_ADMIN"]
    assert ("GET", "/api/v1/health/ready/") in by_key


@pytest.mark.django_db
def test_catalog_examples_never_contain_real_secrets(super_admin, client_for):
    data = client_for(super_admin).get(ENDPOINTS).data
    login = next(e for e in data["results"] if e["path"] == "/api/v1/auth/login/")
    response = login["response_example"]
    assert response["access"] == "<ACCESS_TOKEN>" and response["refresh"] == "<REFRESH_TOKEN>"
    dump = json.dumps(data)
    assert "eyJ" not in dump  # no JWT anywhere


@pytest.mark.django_db
def test_catalog_includes_live_traffic(super_admin, client_for):
    RequestLog.objects.bulk_create([_log(), _log(status_code=500)])
    data = client_for(super_admin).get(ENDPOINTS).data
    me = next(e for e in data["results"] if e["path"] == "/api/v1/auth/me/" and e["method"] == "GET")
    assert me["traffic_24h"]["count"] == 2 and me["traffic_24h"]["server_errors"] == 1
    assert me["status"] == "failing"


@pytest.mark.django_db
def test_schema_documents_access_and_errors(super_admin, client_for):
    schema = catalog.get_schema()
    op = schema["paths"]["/api/v1/users/{id}/"]["patch"]
    assert op["x-access"]["permission"] == "users.update"
    assert {"400", "401", "403", "404", "429"} <= set(op["responses"])
    assert "Ruxsat" in op["description"]
    assert "ErrorEnvelope" in schema["components"]["schemas"]


# ------------------------------------------------------------------ health
def test_liveness(anon):
    res = anon.get(LIVE)
    assert res.status_code == 200 and res.data == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_ok(anon):
    res = anon.get(READY)
    assert res.status_code == 200
    assert res.data == {"status": "ok", "checks": {"database": "ok", "cache": "ok"}}


@pytest.mark.django_db
def test_readiness_reports_unavailable_without_leaking_details(anon):
    with mock.patch("apps.monitoring.health.check_database", return_value=False):
        res = anon.get(READY)
    assert res.status_code == 503
    assert res.data == {"status": "unavailable", "checks": {"database": "fail", "cache": "ok"}}


@pytest.mark.django_db
def test_readiness_degraded_when_cache_fails(anon):
    with mock.patch("apps.monitoring.health.check_cache", return_value=False):
        res = anon.get(READY)
    assert res.status_code == 200 and res.data["status"] == "degraded"


@pytest.mark.django_db
def test_readiness_survives_real_database_error(anon):
    with mock.patch("apps.monitoring.health.connections") as conns:
        conns.__getitem__.return_value.cursor.side_effect = RuntimeError("password=hunter2 host=db.internal")
        res = anon.get(READY)
    assert res.status_code == 503
    assert "hunter2" not in json.dumps(res.data) and "db.internal" not in json.dumps(res.data)


def test_health_is_not_throttled(anon, settings):
    for _ in range(80):  # anon rate in production defaults is 60/min
        assert anon.get(LIVE).status_code == 200
