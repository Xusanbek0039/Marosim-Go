"""The Super Admin panel's static export is served by Django (superadmin.marosimgo.uz)."""

import pytest
from django.test import Client


@pytest.fixture
def build(tmp_path, settings):
    (tmp_path / "_next/static/chunks").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<html>root</html>")
    (tmp_path / "dashboard.html").write_text("<html>dashboard</html>")
    (tmp_path / "dashboard.txt").write_text("rsc")
    (tmp_path / "404.html").write_text("<html>not found</html>")
    (tmp_path / "_next/static/chunks/app.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("nope")
    settings.PANEL_BUILD_DIR = tmp_path
    settings.PANEL_HOSTS = ["superadmin.marosimgo.uz"]
    settings.ALLOWED_HOSTS = ["superadmin.marosimgo.uz", "api.marosimgo.uz"]
    return tmp_path


def panel():
    return Client(HTTP_HOST="superadmin.marosimgo.uz")


def test_pages_assets_and_cache_headers(build):
    res = panel().get("/dashboard")
    assert res.status_code == 200 and b"dashboard" in b"".join(res.streaming_content)
    assert res["Cache-Control"] == "no-cache" and "default-src 'self'" in res["Content-Security-Policy"]
    assert res["Content-Type"].startswith("text/html")
    js = panel().get("/_next/static/chunks/app.js")
    assert js.status_code == 200 and "immutable" in js["Cache-Control"]
    assert panel().get("/dashboard.txt", {"_rsc": "x"}).status_code == 200
    assert panel().get("/").url == "/dashboard"


def test_unknown_path_is_404_page_and_traversal_is_refused(build):
    res = panel().get("/nope")
    assert res.status_code == 404 and b"not found" in b"".join(res.streaming_content)
    assert panel().get("/../secret.txt").status_code == 404
    assert panel().get("/%2e%2e/secret.txt").status_code == 404


def test_api_host_has_no_panel_but_api_still_works(build):
    api = Client(HTTP_HOST="api.marosimgo.uz")
    assert api.get("/dashboard").status_code == 404
    assert api.get("/").status_code == 200
    assert api.get("/api/v1/health/live/").status_code == 200
    # the panel host reaches the API on its own origin too
    assert panel().get("/api/v1/health/live/").status_code == 200
    # unknown API paths stay API 404s, not the panel
    assert panel().get("/api/v1/does-not-exist/").status_code == 404


def test_panel_is_read_only(build):
    assert panel().post("/dashboard").status_code in (403, 405)
