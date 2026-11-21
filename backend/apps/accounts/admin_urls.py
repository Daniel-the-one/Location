"""Pages réservées à l'administrateur (session Django, pas JWT)."""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path

from .models import IdentityVerification


@staff_member_required
def identity_document(request, pk):
    """Affiche la pièce d'identité : seul accès possible à ce fichier privé."""
    verification = get_object_or_404(IdentityVerification, pk=pk)
    if not verification.document:
        raise Http404
    return FileResponse(verification.document.open("rb"), as_attachment=False)


urlpatterns = [
    path("identity/<int:pk>/document/", identity_document, name="identity-document"),
]
