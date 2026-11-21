"""Redimensionnement des photos à l'arrivée : moins de stockage, assemblage plus léger."""
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1600


def resize_upload(uploaded, max_side: int = MAX_SIDE, quality: int = 85) -> ContentFile:
    """Remet l'image droite (EXIF), la réduit à `max_side` px et la réencode en JPEG."""
    try:
        uploaded.seek(0)
        image = Image.open(uploaded)
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Image illisible.") from exc
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
