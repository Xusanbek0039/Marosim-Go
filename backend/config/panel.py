"""The Super Admin panel, served by Django itself (api.marosimgo.uz = API + panel, one deploy).

``frontend/`` is built as a static export (``npm run build:panel``) into ``backend/panel/``. Every
path that is not ``api/``, ``media/`` or ``static/`` is looked up there:

* ``/dashboard``          → ``dashboard.html``
* ``/dashboard.txt``, ``/_next/static/...`` → the file itself (RSC payloads, JS, CSS, images)
* anything else           → ``404.html`` with status 404

``_next/static`` files have content hashes in their names, so they are cached for a year; HTML and
RSC payloads are revalidated on every load so a new deploy shows up immediately. All panel responses
carry the same CSP the Next.js server used to send.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.utils._os import safe_join
from django.views.decorators.http import require_safe

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",  # Next.js bootstraps with inline scripts
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
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


def _root() -> Path:
    return Path(settings.PANEL_BUILD_DIR)


def _find(path: str) -> Path | None:
    """The build file for a URL path, or None. ``safe_join`` refuses anything outside the build."""
    root = _root()
    path = path.strip("/")
    candidates = [path, f"{path}.html", f"{path}/index.html"] if path else ["index.html"]
    for candidate in candidates:
        try:
            file = Path(safe_join(root, candidate))
        except Exception:  # noqa: BLE001 — SuspiciousFileOperation / ValueError: path escapes the build
            return None
        if file.is_file():
            return file
    return None


def _respond(file: Path, status: int = 200) -> FileResponse:
    content_type, encoding = mimetypes.guess_type(file.name)
    response = FileResponse(file.open("rb"), status=status, content_type=content_type or "application/octet-stream")
    if encoding:
        response.headers.pop("Content-Encoding", None)
    rel = file.relative_to(_root()).as_posix()
    response["Cache-Control"] = IMMUTABLE if rel.startswith("_next/static/") else REVALIDATE
    response["Content-Security-Policy"] = CSP
    response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@require_safe
def serve_panel(request, path: str = ""):
    if not (_root() / "index.html").is_file():
        return HttpResponse(
            "MarosimGo API ishlayapti. Super Admin panel hali build qilinmagan: "
            "frontend/ papkasida `npm run build:panel` ni ishga tushiring.",
            content_type="text/plain; charset=utf-8",
            status=404,
        )
    if path.strip("/") == "":
        return HttpResponseRedirect("/dashboard")
    file = _find(path)
    if file is not None:
        return _respond(file)
    not_found = _find("404")
    if not_found is None:
        raise Http404
    return _respond(not_found, status=404)
