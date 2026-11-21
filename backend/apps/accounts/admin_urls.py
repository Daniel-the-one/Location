"""Pages réservées à l'administrateur (session Django, pas JWT)."""
import os

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path

from .models import IdentityVerification

SAFE_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@staff_member_required
def identity_document(request, pk):
    """Affiche la pièce d'identité : seul accès possible à ce fichier privé.

    Le type est imposé d'après l'extension (jamais deviné du contenu) et la réponse est
    isolée (nosniff + CSP sandbox) pour qu'un fichier piégé ne puisse pas exécuter de script.
    """
    verification = get_object_or_404(IdentityVerification, pk=pk)
    if not verification.document:
        raise Http404
    ext = os.path.splitext(verification.document.name)[1].lower()
    content_type = SAFE_TYPES.get(ext)
    if content_type is None:
        raise Http404
    response = FileResponse(verification.document.open("rb"), content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src 'self'; object-src 'self'"
    return response


urlpatterns = [
    path("identity/<int:pk>/document/", identity_document, name="identity-document"),
]
