"""Contrôles communs sur les fichiers téléversés (type et taille)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS + ["pdf"]

validate_image_extension = FileExtensionValidator(IMAGE_EXTENSIONS)
validate_document_extension = FileExtensionValidator(DOCUMENT_EXTENSIONS)


def validate_file_size(file):
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Fichier trop lourd (maximum {settings.MAX_UPLOAD_SIZE_MB} Mo).")
