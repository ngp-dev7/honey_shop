import io
from typing import NamedTuple

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

# Only these formats are ever opened. Pillow refuses everything else.
ALLOWED_FORMATS = ["JPEG", "PNG", "WEBP"]
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
OUTPUT_WIDTHS = (480, 960, 1600)
WEBP_QUALITY = 82


class ProcessedImage(NamedTuple):
    width: int
    height: int
    data: bytes


def _open(upload):
    """Open an upload, accepting only the allowed formats and sizes."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            _("The file is too large. The maximum size is %(mb)d MB."),
            code="too_large",
            params={"mb": MAX_UPLOAD_BYTES // (1024 * 1024)},
        )
    try:
        upload.seek(0)
        # Pillow gets a private copy, so it can never close the uploaded file.
        image = Image.open(io.BytesIO(upload.read()), formats=ALLOWED_FORMATS)
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
        SyntaxError,
    ):
        raise ValidationError(
            _("Upload a valid JPEG, PNG or WebP image."), code="invalid_image"
        ) from None
    # The size comes from the file header, before any pixel data is decoded.
    if image.width * image.height > MAX_PIXELS:
        image.close()
        raise ValidationError(
            _("The image has too many pixels. The maximum is %(mp)d megapixels."),
            code="too_many_pixels",
            params={"mp": MAX_PIXELS // 1_000_000},
        )
    return image


def validate_image(upload):
    """Django validator: accept only safe, readable images."""
    image = _open(upload)
    try:
        image.verify()
    except (OSError, ValueError, SyntaxError):
        raise ValidationError(
            _("Upload a valid JPEG, PNG or WebP image."), code="invalid_image"
        ) from None
    finally:
        image.close()
        upload.seek(0)


def process_image(upload):
    """Return resized WebP versions, smallest first.

    Phone rotation is applied and all metadata (EXIF, GPS) is dropped.
    Images are never enlarged.
    """
    try:
        with _open(upload) as opened:
            image = ImageOps.exif_transpose(opened)
            has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")

            results = []
            for width in sorted({min(w, image.width) for w in OUTPUT_WIDTHS}):
                height = max(1, round(image.height * width / image.width))
                if width == image.width:
                    resized = image
                else:
                    resized = image.resize(
                        (width, height),
                        Image.Resampling.LANCZOS,
                        reducing_gap=2.0,
                    )
                buffer = io.BytesIO()
                resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
                results.append(ProcessedImage(width, height, buffer.getvalue()))
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError(
            _("Upload a valid JPEG, PNG or WebP image."), code="invalid_image"
        ) from None
    finally:
        upload.seek(0)
    return results
