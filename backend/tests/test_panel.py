"""The panels' static exports are served by Django, one build per subdomain."""

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
    studio = tmp_path.parent / "studio-build"
    (studio / "ceremonies/_").mkdir(parents=True, exist_ok=True)
    (studio / "index.html").write_text("<html>studio home</html>")
    (studio / "ceremonies/_.html").write_text("<html>ceremony detail</html>")
    (studio / "ceremonies/_.txt").write_text("ceremony rsc")
    (studio / "ceremonies/_/__next.page.txt").write_text("segment rsc")
    (studio / "404.html").write_text("<html>studio 404</html>")
    settings.PANEL_SITES = {"superadmin": tmp_path, "admin": tmp_path.parent / "missing", "studio": studio}
    settings.PANEL_HOST_SITES = {"panel.example.com": "superadmin"}
    settings.PANEL_DEFAULT_SITE = ""
    settings.ALLOWED_HOSTS = [
        "superadmin.marosimgo.uz",
        "api.marosimgo.uz",
        "studio.marosimgo.uz",
        "admin.marosimgo.uz",
        "panel.example.com",
        "localhost",
    ]
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


def body(res):
    return b"".join(res.streaming_content)


def test_each_subdomain_gets_its_own_panel(build):
    studio = Client(HTTP_HOST="studio.marosimgo.uz")
    home = studio.get("/")
    assert home.status_code == 200 and b"studio home" in body(home)
    assert "https://www.googleapis.com" in home["Content-Security-Policy"]
    assert "googleapis" not in panel().get("/dashboard")["Content-Security-Policy"]
    assert studio.get("/dashboard").status_code == 404  # the Super Admin page is not on the studio host
    assert studio.get("/api/v1/health/live/").status_code == 200
    explicit = Client(HTTP_HOST="panel.example.com").get("/dashboard")
    assert explicit.status_code == 200 and b"dashboard" in body(explicit)


def test_dynamic_segments_use_the_placeholder_export(build):
    studio = Client(HTTP_HOST="studio.marosimgo.uz")
    page = studio.get("/ceremonies/dfe97f48-7712-461f-bffa-a125b3aa50a9")
    assert page.status_code == 200 and b"ceremony detail" in body(page)
    assert b"ceremony rsc" in body(studio.get("/ceremonies/dfe97f48.txt"))
    assert b"segment rsc" in body(studio.get("/ceremonies/dfe97f48/__next.page.txt"))
    missing = studio.get("/ceremonies/x/y/z")
    assert missing.status_code == 404 and b"studio 404" in body(missing)
    assert studio.get("/ceremonies/../../secret.txt").status_code == 404


def test_flattened_segment_prefetch_urls_match_export_directories(build, settings):
    segment = build / "admins/__next.!KHBhbmVsKQ/admins/__PAGE__.txt"
    segment.parent.mkdir(parents=True)
    segment.write_text("admin page segment")
    root_segment = build / "__next.!KHBhbmVsKQ/__PAGE__.txt"
    root_segment.parent.mkdir(parents=True)
    root_segment.write_text("root segment")
    studio_root = settings.PANEL_SITES["studio"]
    dynamic = studio_root / "ceremonies/_/__next.!KGFwcCk/ceremonies/$d$id/__PAGE__.txt"
    dynamic.parent.mkdir(parents=True)
    dynamic.write_text("dynamic ceremony segment")

    response = panel().get("/admins/__next.!KHBhbmVsKQ.admins.__PAGE__.txt", {"_rsc": "prefetch"})
    assert response.status_code == 200
    assert body(response) == b"admin page segment"
    assert response["Cache-Control"] == "no-cache"
    assert response["Content-Type"].startswith("text/plain")
    assert body(panel().get("/__next.!KHBhbmVsKQ.__PAGE__.txt")) == b"root segment"
    studio = Client(HTTP_HOST="studio.marosimgo.uz")
    response = studio.get(
        "/ceremonies/dfe97f48-7712-461f-bffa-a125b3aa50a9/__next.!KGFwcCk.ceremonies.$d$id.__PAGE__.txt"
    )
    assert response.status_code == 200
    assert body(response) == b"dynamic ceremony segment"
    assert panel().get("/admins/__next.!KHBhbmVsKQ..admins.__PAGE__.txt").status_code == 404


def test_unbuilt_panel_and_unknown_host(build, settings):
    res = Client(HTTP_HOST="admin.marosimgo.uz").get("/dashboard")
    assert res.status_code == 404 and "build" in res.content.decode()
    assert Client(HTTP_HOST="localhost").get("/dashboard").status_code == 404  # API-only by default
    settings.PANEL_DEFAULT_SITE = "superadmin"  # development
    assert Client(HTTP_HOST="localhost").get("/dashboard").status_code == 200


def test_root_domain_serves_the_landing_page(settings):
    from django.conf import settings as conf

    settings.PANEL_SITES = {**settings.PANEL_SITES, "landing": conf.BASE_DIR / "landing"}
    settings.PANEL_HOST_SITES = {"marosimgo.uz": "landing", "www.marosimgo.uz": "landing"}
    settings.ALLOWED_HOSTS = ["marosimgo.uz", "www.marosimgo.uz"]
    for host in ("marosimgo.uz", "www.marosimgo.uz"):
        res = Client(HTTP_HOST=host).get("/")
        assert res.status_code == 200 and b"MarosimGo" in body(res)  # no redirect to /dashboard
    assert Client(HTTP_HOST="marosimgo.uz").get("/fonts/jakarta-latin.woff2").status_code == 200
    missing = Client(HTTP_HOST="marosimgo.uz").get("/nope")
    assert missing.status_code == 404 and b"Bosh sahifaga" in body(missing)


@pytest.mark.parametrize(
    ("host", "site", "folder"),
    [("userlogin.marosimgo.uz", "userlogin", "panel-user"), ("toyxona.marosimgo.uz", "toyxona", "panel-toyxona")],
)
def test_user_and_venue_cabinets_have_their_own_subdomains(settings, host, site, folder):
    from django.conf import settings as conf
    from django.test import RequestFactory

    from config.panel import site_for

    settings.ALLOWED_HOSTS = [host]
    assert site_for(RequestFactory(HTTP_HOST=host).get("/")) == site
    assert conf.PANEL_SITES[site].name == folder
