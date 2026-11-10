"""Where portfolio files live and how much space a studio uses.

Every studio gets ``Studio.portfolio_quota_mb`` (default 1 GB) for its portfolio — photos, reels and
their posters together. Files go to Google Drive (``MarosimGo / Studio_<nom> / Portfolio``, the same
studio folder as its ceremonies) whenever the platform Drive is connected; without a connection
(development, tests) they stay in MEDIA_ROOT. ``STUDIO_PORTFOLIO_STORAGE`` = ``auto`` (default) /
``drive`` (Drive or fail) / ``local``.
"""

import logging
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import PortfolioStorage, Studio, StudioImage

logger = logging.getLogger("apps.studios")

MB = 1024 * 1024


def quota_bytes(studio: Studio) -> int:
    return studio.portfolio_quota_mb * MB


def _backfill_sizes(studio: Studio) -> None:
    """Rows saved before sizes were tracked: measure the local files once."""
    for item in studio.images.filter(storage=PortfolioStorage.LOCAL, size_bytes=0):
        size = 0
        for f in (item.image, item.video):
            if f:
                try:
                    size += f.size
                except (OSError, ValueError):
                    pass
        if size:
            StudioImage.objects.filter(pk=item.pk).update(size_bytes=size)


def used_bytes(studio: Studio) -> int:
    _backfill_sizes(studio)
    return studio.images.aggregate(n=Sum("size_bytes"))["n"] or 0


def usage(studio: Studio) -> dict:
    used, quota = used_bytes(studio), quota_bytes(studio)
    return {"used_bytes": used, "quota_bytes": quota, "free_bytes": max(0, quota - used), "storage": target()}


def ensure_room(studio: Studio, extra: int, field: str) -> None:
    used, quota = used_bytes(studio), quota_bytes(studio)
    if used + extra > quota:
        free = max(0, quota - used) / MB
        raise ValidationError(
            {field: [f"Portfolio joyi yetmaydi: {free:.0f} MB bo'sh qoldi ({studio.portfolio_quota_mb} MB dan)."]}
        )


# ------------------------------------------------------------------- target
def target() -> str:
    mode = getattr(settings, "STUDIO_PORTFOLIO_STORAGE", "auto")
    if mode == "local":
        return PortfolioStorage.LOCAL
    if mode == "drive":
        return PortfolioStorage.DRIVE
    from apps.storage.models import ConnectionStatus
    from apps.storage.services import connection

    try:
        return PortfolioStorage.DRIVE if connection().status == ConnectionStatus.CONNECTED else PortfolioStorage.LOCAL
    except Exception:  # noqa: BLE001 — no connection row yet
        return PortfolioStorage.LOCAL


def _unavailable(exc):
    from apps.media.services import StorageUnavailable

    logger.warning("portfolio storage error: %s", getattr(exc, "code", exc))
    return StorageUnavailable(f"{StorageUnavailable.default_detail} ({getattr(exc, 'code', 'error')})")


def _folder(studio: Studio):
    from apps.media.services import _drive_name
    from apps.storage import folders

    sid = studio.pk
    return folders.ensure_path(
        [(f"studio:{sid}", f"Studio_{_drive_name(studio.name)}"), (f"studio:{sid}/portfolio", "Portfolio")]
    )


def _local_path(content):
    """(path, cleanup) for an upload or ContentFile."""
    if hasattr(content, "temporary_file_path"):
        return content.temporary_file_path(), lambda: None
    fd, path = tempfile.mkstemp(suffix=Path(content.name or "").suffix)
    with os.fdopen(fd, "wb") as out:
        content.seek(0)
        for chunk in content.chunks():
            out.write(chunk)
    return path, lambda: os.unlink(path)


def upload_to_drive(studio: Studio, files: list[tuple[object, str]]) -> list[str]:
    """Upload ``[(content, mime)]`` into the studio's Portfolio folder; returns Drive file ids.

    On a failure the files already uploaded in this call are trashed again.
    """
    from apps.storage.google import GoogleError
    from apps.storage.services import StorageError, gateway

    ids: list[str] = []
    try:
        parent, creds = _folder(studio)
        for content, mime in files:
            path, cleanup = _local_path(content)
            try:
                meta = gateway().upload_file(
                    creds,
                    name=content.name,
                    parent_id=parent,
                    path=path,
                    mime_type=mime,
                    app_properties={"marosimgo": "portfolio", "studio": str(studio.pk)},
                )
            finally:
                cleanup()
            ids.append(meta["id"])
    except (StorageError, GoogleError) as exc:
        trash(ids)
        raise _unavailable(exc) from None
    return ids


def trash(file_ids) -> None:
    """Move Drive files to the trash (best effort — a failure only leaves an orphan in Drive)."""
    file_ids = [f for f in file_ids if f]
    if not file_ids:
        return
    from apps.storage.google import GoogleError
    from apps.storage.services import StorageError, access_credentials, gateway

    try:
        creds = access_credentials()
        for file_id in file_ids:
            gateway().trash_file(creds, file_id)
    except (StorageError, GoogleError) as exc:
        logger.warning("could not trash portfolio files %s: %s", file_ids, getattr(exc, "code", exc))


def open_stream(file_id: str, byte_range: str | None):
    from apps.storage.google import GoogleError
    from apps.storage.services import StorageError, access_credentials, gateway

    try:
        return gateway().open_media(access_credentials(), file_id, byte_range)
    except (StorageError, GoogleError) as exc:
        raise _unavailable(exc) from None
