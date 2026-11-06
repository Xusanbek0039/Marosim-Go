"""Safe image upload handling.

Every uploaded image is fully decoded by Pillow, checked for size/format/pixel count
(decompression-bomb protection), stripped of metadata (EXIF/GPS) and re-encoded as WEBP
under a random file name. The original bytes are never stored.
"""

import io
import uuid
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def process_image(upload) -> ContentFile:
    cfg = settings.IMAGE_UPLOAD
    if upload.size > cfg["MAX_BYTES"]:
        raise ValidationError(f"Rasm hajmi {cfg['MAX_BYTES'] // (1024 * 1024)} MB dan oshmasligi kerak.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            upload.seek(0)
            probe = Image.open(upload)
            if probe.format not in cfg["ALLOWED_FORMATS"]:
                raise ValidationError("Faqat JPG, PNG yoki WEBP formatdagi rasm qabul qilinadi.")
            if probe.width * probe.height > cfg["MAX_PIXELS"]:
                raise ValidationError("Rasm o'lchami juda katta.")
            probe.verify()

            upload.seek(0)
            image = Image.open(upload)
            image.load()
    except ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, SyntaxError):
        raise ValidationError("Fayl yaroqli rasm emas.") from None

    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
    image.thumbnail((cfg["MAX_SIDE"], cfg["MAX_SIDE"]))

    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=85, method=4)
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.webp")
