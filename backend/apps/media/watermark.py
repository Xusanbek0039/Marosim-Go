"""The MarosimGo watermark: a small logo in the bottom-right corner of photos and videos.

User decisions 2026-11-08: everyone without a running subscription sees media *with* the logo; it
must be visible but must not get in the way. Videos get the logo burned in (a second, watermarked
copy in Drive — see ``watermark_jobs``); photos and previews are stamped on the fly.

Look: brand icon + wordmark whose dark letters are turned white, a soft shadow so it reads on light
and dark footage, ~75 % opacity, width ≈ 16 % of the shorter side, 3 % margin.
"""

import io
import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).with_name("assets")
OPACITY = 0.78
#: Logo width relative to the frame's *shorter* side (portrait phone videos stay balanced).
RELATIVE_WIDTH = 0.30
MIN_WIDTH, MAX_WIDTH = 90, 520
MARGIN = 0.03


class WatermarkError(Exception):
    pass


# ------------------------------------------------------------------- logo
@lru_cache(maxsize=1)
def _base_logo() -> Image.Image:
    """Icon + wordmark (dark letters → white), shadowed, full resolution, RGBA."""
    icon = Image.open(ASSETS / "logo_icon.png").convert("RGBA")
    word = Image.open(ASSETS / "wordmark.png").convert("RGBA")
    # Dark navy letters become white; the blue→cyan "Go" keeps its colours.
    px = word.load()
    for y in range(word.height):
        for x in range(word.width):
            r, g, b, a = px[x, y]
            if a and max(r, g, b) < 90:
                px[x, y] = (255, 255, 255, a)
    word = word.crop(word.getbbox())
    icon = icon.crop(icon.getbbox())
    h = word.height
    icon = icon.resize((round(icon.width * h * 1.25 / icon.height), round(h * 1.25)), Image.LANCZOS)
    gap = h // 4
    canvas = Image.new("RGBA", (icon.width + gap + word.width, icon.height), (0, 0, 0, 0))
    canvas.alpha_composite(icon, (0, 0))
    canvas.alpha_composite(word, (icon.width + gap, (icon.height - word.height) // 2))
    # soft shadow: blurred black silhouette under the logo
    pad = h // 3
    out = Image.new("RGBA", (canvas.width + 2 * pad, canvas.height + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(canvas.getchannel("A").point(lambda v: int(v * 0.85)))
    out.alpha_composite(shadow, (pad + h // 30, pad + h // 30))
    out = out.filter(ImageFilter.GaussianBlur(h // 12))
    out.alpha_composite(canvas, (pad, pad))
    return out


@lru_cache(maxsize=16)
def logo_for(frame_width: int, frame_height: int) -> Image.Image:
    base = _base_logo()
    width = max(MIN_WIDTH, min(MAX_WIDTH, round(min(frame_width, frame_height) * RELATIVE_WIDTH)))
    logo = base.resize((width, round(base.height * width / base.width)), Image.LANCZOS)
    logo.putalpha(logo.getchannel("A").point(lambda v: int(v * OPACITY)))
    return logo


def _position(frame: tuple[int, int], logo: Image.Image) -> tuple[int, int]:
    w, h = frame
    m = round(min(w, h) * MARGIN)
    return w - logo.width - m, h - logo.height - m


# ----------------------------------------------------------------- images
def stamp_image(content: bytes) -> tuple[bytes, str]:
    """Return ``content`` (any Pillow-readable image) as a JPEG with the logo."""
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception as exc:  # noqa: BLE001 — any undecodable preview is simply not served
        raise WatermarkError("unreadable_image") from exc
    img = img.convert("RGBA")
    logo = logo_for(img.width, img.height)
    img.alpha_composite(logo, _position(img.size, logo))
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue(), "image/jpeg"


# ------------------------------------------------------------------ video
# Speed (10 GB wedding videos): the copy with the logo is a *preview* — the original quality is a
# subscription perk — so it is scaled down to ``MEDIA_WATERMARK_MAX_HEIGHT`` (720p) while burning.
# That alone cuts the work 4-9x for 1080p/4K sources. On top of it: a GPU encoder (NVIDIA / Intel /
# AMD) when one works, GPU decoding (``-hwaccel auto``), and the source is read straight from Drive
# over HTTPS while encoding (no 10 GB download-then-encode). Any GPU problem falls back to the CPU.

#: (encoder, extra args, pixel format) — tried in this order, the first that works is used.
_ENCODERS = {
    "h264_nvenc": (["-preset", "p3", "-rc", "vbr", "-cq", "27", "-b:v", "0"], "nv12"),
    "h264_qsv": (["-preset", "faster", "-global_quality", "27"], "nv12"),
    "h264_amf": (["-quality", "speed", "-rc", "cqp", "-qp_i", "25", "-qp_p", "27"], "nv12"),
    "libx264": (["-preset", "veryfast", "-crf", "24"], "yuv420p"),
}
CPU = "libx264"


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


@lru_cache(maxsize=1)
def video_encoder() -> str:
    """The fastest H.264 encoder that actually works on this machine (checked once per process)."""
    wanted = (getattr(settings, "MEDIA_WATERMARK_ENCODER", "auto") or "auto").strip()
    if wanted != "auto":
        return wanted if wanted in _ENCODERS else CPU
    ffmpeg = ffmpeg_bin()
    for name in ("h264_nvenc", "h264_qsv", "h264_amf"):
        try:
            res = subprocess.run(  # noqa: S603 — fixed argv
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2",
                 "-c:v", name, *_ENCODERS[name][0], "-f", "null", "-"],
                capture_output=True, timeout=30, check=False,
            )  # fmt: skip
        except (OSError, subprocess.TimeoutExpired):
            continue
        if res.returncode == 0:
            logger.info("watermark: using GPU encoder %s", name)
            return name
    return CPU


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float  # seconds, 0 if unknown


def _probe(src: str, http_headers: str | None = None) -> VideoInfo:
    """Displayed width/height (phone videos carry a rotation; ffmpeg auto-rotates when decoding)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return VideoInfo(1920, 1080, 0.0)
    head = ["-headers", http_headers] if http_headers else []
    res = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [ffprobe, "-v", "error", *head, "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", src],
        capture_output=True, text=True, timeout=300, check=False,
    )  # fmt: skip
    try:
        data = json.loads(res.stdout)
        stream = data["streams"][0]
    except (ValueError, KeyError, IndexError):
        raise WatermarkError("not_a_video") from None
    w, h = int(stream["width"]), int(stream["height"])
    rotation = next((int(d.get("rotation", 0)) for d in stream.get("side_data_list", []) if "rotation" in d), 0)
    try:
        duration = float(data.get("format", {}).get("duration") or 0)
    except ValueError:
        duration = 0.0
    return VideoInfo(*((h, w) if abs(rotation) % 180 == 90 else (w, h)), duration)


def target_size(w: int, h: int, max_short: int) -> tuple[int, int]:
    """Scale so the shorter side is at most ``max_short``; both sides even (H.264 needs that)."""
    scale = min(1.0, max_short / min(w, h)) if max_short > 0 else 1.0
    return max(2, round(w * scale / 2) * 2), max(2, round(h * scale / 2) * 2)


def _run(cmd: list[str], duration: float, on_progress, workdir: Path) -> tuple[int, str]:
    """Run ffmpeg with ``-progress`` on stdout; report 0-99 %. Returns (returncode, stderr tail)."""
    err_path = workdir / "ffmpeg.log"
    deadline = time.monotonic() + 8 * 3600
    with open(err_path, "w+", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True)  # noqa: S603
        last = -1
        try:
            for line in proc.stdout:
                if time.monotonic() > deadline:
                    proc.kill()
                    break
                if on_progress and duration > 0 and line.startswith("out_time_us="):
                    try:
                        pct = min(99, int(int(line.split("=", 1)[1]) / 1e6 / duration * 100))
                    except ValueError:
                        continue
                    if pct > last:
                        last = pct
                        on_progress(pct)
            proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        err.seek(0)
        return proc.returncode, err.read()[-300:]


def burn_video(src, dst: Path, workdir: Path, *, http_headers: str | None = None, on_progress=None) -> None:
    """Re-encode ``src`` (local path or Drive URL) to an H.264/AAC MP4 preview with the logo burned in.

    ``+faststart`` puts the index first, so playback starts before the whole file arrives.
    """
    ffmpeg = ffmpeg_bin()
    if not ffmpeg:
        raise WatermarkError("ffmpeg_missing")
    src = str(src)
    info = _probe(src, http_headers)
    w, h = target_size(info.width, info.height, getattr(settings, "MEDIA_WATERMARK_MAX_HEIGHT", 720))
    logo = logo_for(w, h)
    logo_path = workdir / "logo.png"
    logo.save(logo_path)
    m = round(min(w, h) * MARGIN)
    head = ["-headers", http_headers, "-reconnect", "1", "-reconnect_delay_max", "30"] if http_headers else []

    encoder = video_encoder()
    # GPU decode + chosen encoder first; if anything about it fails, once more purely on the CPU.
    attempts = [(encoder, True), (CPU, False)]
    tail = ""
    for enc, hw in attempts:
        args, pix = _ENCODERS[enc]
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostats", "-y", "-progress", "pipe:1",
            *(["-hwaccel", "auto"] if hw else []),
            *head, "-i", src, "-i", str(logo_path),
            "-filter_complex",
            f"[0:v]scale={w}:{h}:flags=fast_bilinear[s];[s][1:v]overlay=W-w-{m}:H-h-{m}:format=auto,format={pix}[v]",
            "-map", "[v]", "-map", "0:a?",
            "-c:v", enc, *args,
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-movflags", "+faststart",
            str(dst),
        ]  # fmt: skip
        code, tail = _run(cmd, info.duration, on_progress, workdir)
        if code == 0 and dst.exists() and dst.stat().st_size > 0:
            return
        logger.warning("watermark: %s failed (%s), %s", enc, tail[-120:], "retrying on CPU" if enc != CPU else "giving up")
        dst.unlink(missing_ok=True)
    raise WatermarkError(f"ffmpeg_failed: {tail}")
