"""Vertical portfolio videos ("reels"): validation and poster frame.

A reel must be portrait (height ≥ 1.5 × width, e.g. 9:16), 1–90 s long and at most
``STUDIO_REEL_MAX_MB``. ffprobe / ffmpeg are used when installed (they already are for the
watermark worker); without them the client-sent poster frame is the only shape check.
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.files import File
from rest_framework.exceptions import ValidationError

from apps.core.uploads import process_image

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
MIN_PORTRAIT_RATIO = 1.5
MIN_SECONDS, MAX_SECONDS = 1, 90
POSTER_MAX_SIDE = 1280


def max_bytes() -> int:
    return getattr(settings, "STUDIO_REEL_MAX_MB", 100) * 1024 * 1024


@dataclass
class Probe:
    width: int
    height: int
    duration: float


def _error(message: str, field: str = "video"):
    return ValidationError({field: [message]})


@contextmanager
def _local_path(upload):
    """A filesystem path for the upload (large uploads already live in a temp file)."""
    if hasattr(upload, "temporary_file_path"):
        yield upload.temporary_file_path()
        return
    suffix = Path(upload.name or "").suffix.lower() or ".mp4"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as out:
            upload.seek(0)
            for chunk in upload.chunks():
                out.write(chunk)
        yield path
    finally:
        os.unlink(path)


def _probe(path: str) -> Probe | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    res = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", path],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    try:
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        w, h = int(stream["width"]), int(stream["height"])
    except (ValueError, KeyError, IndexError, TypeError):
        raise _error("Fayl yaroqli video emas.") from None
    rotation = next((int(d.get("rotation", 0)) for d in stream.get("side_data_list", []) if "rotation" in d), 0)
    if abs(rotation) % 180 == 90:
        w, h = h, w
    try:
        duration = float(data.get("format", {}).get("duration") or 0)
    except ValueError:
        duration = 0.0
    return Probe(w, h, duration)


def _poster_from_video(path: str, at: float):
    from apps.media.watermark import ffmpeg_bin  # media → studios never imports back

    ffmpeg = ffmpeg_bin()
    if not ffmpeg:
        return None
    out = Path(tempfile.gettempdir()) / f"reel-{uuid.uuid4().hex}.jpg"
    try:
        subprocess.run(  # noqa: S603 — fixed argv, no shell
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.2f}", "-i", path,
             "-frames:v", "1", "-q:v", "3", str(out)],
            capture_output=True, timeout=60, check=False,
        )  # fmt: skip
        if not out.exists() or not out.stat().st_size:
            return None
        with out.open("rb") as fh:
            return process_image(File(fh, name=out.name), max_side=POSTER_MAX_SIDE)
    finally:
        out.unlink(missing_ok=True)


def _check_portrait(w: int, h: int, field: str = "video") -> None:
    if w <= 0 or h < w * MIN_PORTRAIT_RATIO:
        raise _error("Video vertikal (Reels, 9:16) formatda bo'lishi kerak.", field)


def prepare(video, poster=None) -> dict:
    """Validate a reel upload; return ``{"video", "image", "duration"}`` ready for ``StudioImage``."""
    ext = Path(video.name or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise _error("Faqat MP4, MOV yoki WEBM video qabul qilinadi.")
    if video.size > max_bytes():
        raise _error(f"Video hajmi {max_bytes() // (1024 * 1024)} MB dan oshmasligi kerak.")

    with _local_path(video) as path:
        info = _probe(path)
        if info is not None:
            _check_portrait(info.width, info.height)
            if info.duration and not (MIN_SECONDS <= info.duration <= MAX_SECONDS):
                raise _error(f"Video {MIN_SECONDS}–{MAX_SECONDS} soniya bo'lishi kerak.")
        image = None
        if poster is not None:
            try:
                image = process_image(poster, max_side=POSTER_MAX_SIDE)
            except ValidationError as exc:
                detail = exc.detail if isinstance(exc.detail, list) else [exc.detail]
                raise ValidationError({"poster": detail}) from None
        if image is None:
            image = _poster_from_video(path, min(1.0, (info.duration if info else 2) / 2))
    if image is None:
        raise _error("Video muqovasi (poster) yuborilishi kerak.", "poster")
    if info is None:
        from PIL import Image

        image.seek(0)
        with Image.open(image) as frame:
            _check_portrait(frame.width, frame.height, "poster")
        image.seek(0)
    video.name = f"{uuid.uuid4().hex}{ext}"
    return {"video": video, "image": image, "duration": round(info.duration, 2) if info else 0}
