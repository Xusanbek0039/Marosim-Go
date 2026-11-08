"""Background production of the watermarked copy of each video.

No task queue in this project: a finished upload (or the first viewer who meets a pending video)
starts one daemon worker thread (``kick``). The worker drains the PENDING queue one video at a
time — ffmpeg is CPU-heavy, so never more than one per process. ``manage.py process_watermarks``
does the same synchronously (back-fill, retries, stuck jobs) and can run from cron.

Each job: claim the row (CAS PENDING → PROCESSING) → download the original from Drive into a temp
dir → burn the logo → upload the copy next to the original → READY. Errors leave the row FAILED
with a short code; it is retried up to ``MAX_ATTEMPTS`` times.
"""

import logging
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.storage.google import GoogleError
from apps.storage.services import StorageError, access_credentials, gateway

from . import watermark
from .models import CeremonyMedia, MediaKind, MediaStatus, WatermarkStatus

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
#: A PROCESSING row older than this is considered abandoned (server restarted mid-job).
STALE_AFTER = timedelta(hours=6)
WM_MIME = "video/mp4"

_lock = threading.Lock()
_running = False


def queue_for(media: CeremonyMedia) -> None:
    """Called when a video becomes READY."""
    if media.kind == MediaKind.VIDEO and media.wm_status == WatermarkStatus.NONE:
        CeremonyMedia.objects.filter(pk=media.pk, wm_status=WatermarkStatus.NONE).update(
            wm_status=WatermarkStatus.PENDING
        )
        media.wm_status = WatermarkStatus.PENDING
        transaction.on_commit(kick)


def _candidates():
    stale = timezone.now() - STALE_AFTER
    return CeremonyMedia.objects.filter(kind=MediaKind.VIDEO, status=MediaStatus.READY).filter(
        Q(wm_status=WatermarkStatus.PENDING)
        | Q(wm_status=WatermarkStatus.FAILED, wm_attempts__lt=MAX_ATTEMPTS)
        | Q(wm_status=WatermarkStatus.PROCESSING, wm_started_at__lt=stale)
    )


def _claim(media_id) -> CeremonyMedia | None:
    won = (
        _candidates()
        .filter(pk=media_id)
        .update(
            wm_status=WatermarkStatus.PROCESSING,
            wm_started_at=timezone.now(),
            wm_attempts=F("wm_attempts") + 1,
            wm_progress=0,
        )
    )
    return CeremonyMedia.objects.get(pk=media_id) if won else None


def _progress_writer(media_pk):
    """Store the percentage for the gallery (at most every 3 s, so the DB is not hammered)."""
    last = {"at": 0.0}

    def write(pct: int) -> None:
        now = time.monotonic()
        if now - last["at"] >= 3:
            last["at"] = now
            CeremonyMedia.objects.filter(pk=media_pk, wm_status=WatermarkStatus.PROCESSING).update(wm_progress=pct)

    return write


def _burn(media: CeremonyMedia, creds, work: Path, dst: Path, on_progress) -> None:
    """Read the original straight from Drive while encoding; if that fails, download it first."""
    media_request = getattr(gateway(), "media_request", None)
    if media_request and getattr(settings, "MEDIA_WATERMARK_STREAM_SOURCE", True):
        url, headers = media_request(creds, media.drive_file_id)
        try:
            watermark.burn_video(url, dst, work, http_headers=headers, on_progress=on_progress)
            return
        except watermark.WatermarkError as exc:
            if str(exc) in ("ffmpeg_missing", "not_a_video"):
                raise
            logger.warning("watermark: streaming from Drive failed for %s, downloading first", media.pk)
    src = work / "source"
    gateway().download_to_file(creds, media.drive_file_id, src)
    watermark.burn_video(src, dst, work, on_progress=on_progress)
    src.unlink(missing_ok=True)


def process(media_id) -> str:
    """Produce the copy for one video. Returns the final ``wm_status`` (or '' if not claimed)."""
    media = _claim(media_id)
    if media is None:
        return ""
    try:
        with tempfile.TemporaryDirectory(prefix="mg-wm-") as tmp:
            work = Path(tmp)
            dst = work / "watermarked.mp4"
            creds = access_credentials()
            _burn(media, creds, work, dst, _progress_writer(media.pk))
            created = gateway().upload_file(
                creds,
                name=f"MarosimGo_{media.pk.hex[:8]}_logo.mp4",
                parent_id=media.drive_folder_id,
                path=dst,
                mime_type=WM_MIME,
                app_properties={"mg_media_wm": str(media.pk)},
            )
            size = int(created.get("size") or dst.stat().st_size)
        CeremonyMedia.objects.filter(pk=media.pk).update(
            wm_status=WatermarkStatus.READY, wm_drive_file_id=created["id"], wm_size_bytes=size, wm_error="",
            wm_progress=100,
        )
        logger.info("watermark ready for media %s", media.pk)
        return WatermarkStatus.READY
    except (watermark.WatermarkError, StorageError, GoogleError, OSError, KeyError) as exc:
        code = getattr(exc, "code", "") or str(exc) or exc.__class__.__name__
        CeremonyMedia.objects.filter(pk=media.pk).update(wm_status=WatermarkStatus.FAILED, wm_error=code[:300])
        logger.warning("watermark failed for media %s: %s", media.pk, code[:120])
        return WatermarkStatus.FAILED


def drain(limit: int | None = None) -> int:
    """Process queued videos one by one; returns how many were attempted."""
    done = 0
    while limit is None or done < limit:
        media_id = _candidates().order_by("created_at").values_list("pk", flat=True).first()
        if media_id is None:
            break
        if process(media_id):
            done += 1
    return done


def _worker() -> None:
    global _running
    try:
        drain()
    except Exception:  # pragma: no cover — never let a thread die silently
        logger.exception("watermark worker crashed")
    finally:
        close_old_connections()
        with _lock:
            _running = False


def kick() -> None:
    """Start the in-process worker if enabled and not already running."""
    global _running
    if not getattr(settings, "MEDIA_WATERMARK_INLINE", True):
        return
    with _lock:
        if _running:
            return
        _running = True
    threading.Thread(target=_worker, name="mg-watermark", daemon=True).start()
