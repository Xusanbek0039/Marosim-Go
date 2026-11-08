"""The web panels, served by Django itself — one deploy for the API and every panel.

Production: the same Django app answers every hostname (all in ``DJANGO_ALLOWED_HOSTS``) and picks
the panel by the host's first DNS label (``settings.PANEL_SITES``):

* ``api.marosimgo.uz``        — the API only (mobile apps)
* ``superadmin.marosimgo.uz`` — Super Admin panel  (``backend/panel/``)
* ``admin.marosimgo.uz``      — Admin panel        (``backend/panel-admin/``)
* ``studio.marosimgo.uz``     — Studio cabinet     (``backend/panel-studio/``)

Every panel host also serves ``/api/v1/`` on its own origin, so the httpOnly auth cookies stay
first-party and no CORS is involved.

The panels are Next.js static exports. Every path that is not ``api/``, ``media/`` or ``static/``
is looked up in the host's build:

* ``/dashboard``          → ``dashboard.html``
* ``/dashboard.txt``, ``/_next/static/...`` → the file itself (RSC payloads, JS, CSS, images)
* ``/ceremonies/<uuid>``  → ``ceremonies/_.html`` — a dynamic segment is exported once under the
  placeholder ``_`` and the page reads the real value from the URL
* anything else           → ``404.html`` with status 404

``_next/static`` files have content hashes in their names, so they are cached for a year; HTML and
RSC payloads are revalidated on every load so a new deploy shows up immediately. All panel responses
carry the CSP the Next.js servers used to send.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.utils._os import safe_join
from django.views.decorators.http import require_safe

PLACEHOLDER = "_"
# Pages a bare "/" opens, per site (the Super Admin / Admin panels have no root page).
HOME = {"superadmin": "/dashboard", "admin": "/dashboard"}
# Extra browser connections a site needs: the studio uploads videos straight to Google Drive.
EXTRA_CONNECT = {"studio": " https://www.googleapis.com"}


def csp(site: str) -> str:
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Next.js bootstraps with inline scripts
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            f"connect-src 'self'{EXTRA_CONNECT.get(site, '')}",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
        ]
    )


IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"

mimetypes.add_type("text/plain", ".txt")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")


def site_for(request) -> str | None:
    """The panel this host serves, or None (API-only host)."""
    host = request.get_host().split(":")[0].lower()
    site = settings.PANEL_HOST_SITES.get(host) or host.split(".")[0]
    if site not in settings.PANEL_SITES:
        site = settings.PANEL_DEFAULT_SITE
    return site if site in settings.PANEL_SITES else None


def _safe(root: Path, rel: str) -> Path | None:
    try:
        return Path(safe_join(root, rel))
    except Exception:  # noqa: BLE001 — SuspiciousFileOperation / ValueError: path escapes the build
        return None


def _resolve_dirs(root: Path, parts: list[str]) -> list[str] | None:
    """Directory segments, each one literal if it exists, else the ``_`` placeholder directory."""
    resolved: list[str] = []
    for part in parts:
        if part in ("", ".", ".."):
            return None
        for candidate in (part, PLACEHOLDER):
            folder = _safe(root, "/".join([*resolved, candidate]))
            if folder is not None and folder.is_dir():
                resolved.append(candidate)
                break
        else:
            return None
    return resolved


def _find(root: Path, path: str) -> Path | None:
    """The build file for a URL path, or None. ``safe_join`` refuses anything outside the build."""
    path = path.strip("/")
    if not path:
        file = root / "index.html"
        return file if file.is_file() else None
    *dirs, name = path.split("/")
    folders = _resolve_dirs(root, dirs)
    if folders is None:
        return None
    stem, dot, ext = name.partition(".")
    names = [name, f"{name}.html", f"{name}/index.html"]
    # ``abc`` → ``_.html`` / ``_/index.html``; ``abc.txt`` → ``_.txt`` (the RSC payload of that page)
    names += [f"{PLACEHOLDER}{dot}{ext}"] if dot else [f"{PLACEHOLDER}.html", f"{PLACEHOLDER}/index.html"]
    for candidate in names:
        file = _safe(root, "/".join([*folders, candidate]))
        if file is not None and file.is_file():
            return file
    return None


def _respond(root: Path, site: str, file: Path, status: int = 200) -> FileResponse:
    content_type, encoding = mimetypes.guess_type(file.name)
    response = FileResponse(file.open("rb"), status=status, content_type=content_type or "application/octet-stream")
    if encoding:
        response.headers.pop("Content-Encoding", None)
    rel = file.relative_to(root).as_posix()
    response["Cache-Control"] = IMMUTABLE if rel.startswith("_next/static/") else REVALIDATE
    response["Content-Security-Policy"] = csp(site)
    response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@require_safe
def serve_panel(request, path: str = ""):
    site = site_for(request)
    if site is None:
        # api.marosimgo.uz: no panel here, just say what this host is.
        if path.strip("/") == "":
            return HttpResponse("MarosimGo API — /api/v1/", content_type="text/plain; charset=utf-8")
        raise Http404
    root = Path(settings.PANEL_SITES[site])
    if not (root / "index.html").is_file():
        return HttpResponse(
            f"MarosimGo API ishlayapti. '{site}' paneli hali build qilinmagan (backend/{root.name}/ bo'sh). "
            "Build buyruqlari: docs/DEPLOY.md.",
            content_type="text/plain; charset=utf-8",
            status=404,
        )
    if path.strip("/") == "" and site in HOME:
        return HttpResponseRedirect(HOME[site])
    file = _find(root, path)
    if file is not None:
        return _respond(root, site, file)
    not_found = _find(root, "404")
    if not_found is None:
        raise Http404
    return _respond(root, site, not_found, status=404)
