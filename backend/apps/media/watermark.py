"""The MarosimGo watermark: a small logo in the bottom-right corner of photos and videos.

User decisions 2026-11-08: everyone without a running subscription sees media *with* the logo; it
must be visible but must not get in the way. Videos get the logo burned in (a second, watermarked
copy in Drive — see ``watermark_jobs``); photos and previews are stamped on the fly.

Look: brand icon + wordmark whose dark letters are turned white, a soft shadow so it reads on light
and dark footage, ~75 % opacity, width ≈ 16 % of the shorter side, 3 % margin.
"""

import io
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter

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
def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def _probe(src: Path) -> tuple[int, int]:
    """Displayed width/height (phone videos carry a rotation; ffmpeg auto-rotates when decoding)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 1920, 1080
    res = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation", "-of", "json", str(src)],
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    try:
        stream = json.loads(res.stdout)["streams"][0]
    except (ValueError, KeyError, IndexError):
        raise WatermarkError("not_a_video") from None
    w, h = int(stream["width"]), int(stream["height"])
    rotation = next((int(d.get("rotation", 0)) for d in stream.get("side_data_list", []) if "rotation" in d), 0)
    return (h, w) if abs(rotation) % 180 == 90 else (w, h)


def burn_video(src: Path, dst: Path, workdir: Path) -> None:
    """Re-encode ``src`` to an H.264/AAC MP4 with the logo burned in (``+faststart`` for streaming)."""
    ffmpeg = ffmpeg_bin()
    if not ffmpeg:
        raise WatermarkError("ffmpeg_missing")
    w, h = _probe(src)
    logo = logo_for(w, h)
    logo_path = workdir / "logo.png"
    logo.save(logo_path)
    m = round(min(w, h) * MARGIN)
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-i", str(logo_path),
        "-filter_complex", f"[0:v][1:v]overlay=W-w-{m}:H-h-{m}:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(dst),
    ]  # fmt: skip
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=6 * 3600, check=False)  # noqa: S603
    if res.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        raise WatermarkError(f"ffmpeg_failed: {res.stderr[-300:]}")
