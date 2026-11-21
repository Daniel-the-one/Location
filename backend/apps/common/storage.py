import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    """Stockage hors de MEDIA_ROOT : aucun fichier n'a d'URL publique.

    L'emplacement est relu à chaque accès pour suivre PRIVATE_MEDIA_ROOT (tests compris).
    """

    def __init__(self):
        super().__init__(base_url=None)

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Les fichiers privés n'ont pas d'URL publique.")


def private_storage():
    return PrivateFileSystemStorage()
