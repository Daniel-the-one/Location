from django.utils import timezone

from apps.exchanges.notifications import notify

from .models import IdentityVerification

V = IdentityVerification.Status


def approve_identity(verification: IdentityVerification, admin) -> None:
    verification.status = V.APPROVED
    verification.rejection_reason = ""
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    verification.save()
    notify(
        verification.user,
        "identity_approved",
        "Votre identité est validée",
        "Votre pièce d'identité a été validée. Vous pouvez maintenant soumettre vos annonces.",
    )


def reject_identity(verification: IdentityVerification, admin, reason: str) -> None:
    verification.status = V.REJECTED
    verification.rejection_reason = reason
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    verification.save()
    notify(
        verification.user,
        "identity_rejected",
        "Votre pièce d'identité a été refusée",
        f"Motif : {reason}\nVous pouvez téléverser une nouvelle pièce depuis votre profil.",
    )
