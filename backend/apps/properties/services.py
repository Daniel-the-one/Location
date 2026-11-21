"""Règles métier des annonces : soumission, validation, suspension.

Les vues API et l'interface administrateur passent toutes par ici.
"""
from django.db import transaction

from apps.exchanges.notifications import notify

from .models import Property, Room, RoomPhoto
from .room_plan import build_room_plan, main_rooms_count

S = Property.Status
MAX_PHOTOS_PER_ROOM = 16


class BusinessError(Exception):
    """Action refusée par une règle métier ; `errors` liste les raisons lisibles."""

    def __init__(self, errors):
        self.errors = errors if isinstance(errors, list) else [errors]
        super().__init__("; ".join(self.errors))


# --- Propriétaire ---------------------------------------------------------


@transaction.atomic
def apply_room_plan(prop: Property, answers: dict) -> list[Room]:
    if prop.status not in (S.DRAFT, S.REJECTED):
        raise BusinessError("La liste des pièces ne peut être regénérée que sur un brouillon.")
    plan = build_room_plan(answers)
    prop.rooms.all().delete()
    rooms = Room.objects.bulk_create(
        Room(property=prop, room_type=r.room_type, name=r.name, is_exterior=r.is_exterior, order=i)
        for i, r in enumerate(plan)
    )
    prop.rooms_count = main_rooms_count(plan)
    prop.save(update_fields=["rooms_count", "updated_at"])
    return rooms


@transaction.atomic
def reorder_rooms(prop: Property, room_ids: list[int]) -> None:
    current = set(prop.rooms.values_list("id", flat=True))
    if set(room_ids) != current or len(room_ids) != len(current):
        raise BusinessError("La liste doit contenir exactement toutes les pièces du bien.")
    for order, room_id in enumerate(room_ids):
        Room.objects.filter(pk=room_id).update(order=order)


def add_photos(room: Room, files) -> list[RoomPhoto]:
    existing = room.photos.count()
    if existing + len(files) > MAX_PHOTOS_PER_ROOM:
        raise BusinessError(f"{MAX_PHOTOS_PER_ROOM} photos au maximum par pièce.")
    photos = [
        RoomPhoto.objects.create(room=room, image=f, order=existing + i)
        for i, f in enumerate(files)
    ]
    room.panorama_status = Room.PanoramaStatus.PENDING
    room.save(update_fields=["panorama_status"])
    return photos


def submission_problems(prop: Property) -> list[str]:
    problems = []
    if not prop.owner.is_identity_verified:
        problems.append("Votre identité doit d'abord être validée par l'administrateur.")
    if not prop.entrance_photo:
        problems.append("Ajoutez la photo de la porte d'entrée.")
    rooms = list(prop.rooms.all())
    if not rooms:
        problems.append("Le bien doit avoir au moins une pièce.")
    missing = [r.name for r in rooms if not r.photos.exists() and not hasattr(r, "panorama")]
    if missing:
        problems.append("Pièces sans photos : " + ", ".join(missing) + ".")
    return problems


def submit_for_review(prop: Property) -> None:
    if prop.status not in (S.DRAFT, S.REJECTED):
        raise BusinessError("Seul un brouillon ou une annonce refusée peut être soumis.")
    problems = submission_problems(prop)
    if problems:
        raise BusinessError(problems)
    prop.status = S.PENDING
    prop.rejection_reason = ""
    prop.save(update_fields=["status", "rejection_reason", "updated_at"])


def owner_suspend(prop: Property) -> None:
    if prop.status != S.PUBLISHED:
        raise BusinessError("Seule une annonce publiée peut être suspendue.")
    prop.status = S.SUSPENDED
    prop.suspended_by_admin = False
    prop.save(update_fields=["status", "suspended_by_admin", "updated_at"])


def owner_reactivate(prop: Property) -> None:
    if prop.status != S.SUSPENDED:
        raise BusinessError("Cette annonce n'est pas suspendue.")
    if prop.suspended_by_admin:
        raise BusinessError("Cette annonce a été suspendue par l'administrateur.")
    prop.status = S.PUBLISHED
    prop.save(update_fields=["status", "updated_at"])


# --- Administrateur -------------------------------------------------------


def approve_property(prop: Property) -> None:
    if prop.status != S.PENDING:
        raise BusinessError("Seule une annonce en attente peut être validée.")
    prop.status = S.PUBLISHED
    prop.rejection_reason = ""
    prop.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(
        prop.owner,
        "property_approved",
        "Votre annonce est publiée",
        f"Bonne nouvelle : « {prop.title} » est maintenant visible par les locataires.",
    )


def reject_property(prop: Property, reason: str) -> None:
    if prop.status != S.PENDING:
        raise BusinessError("Seule une annonce en attente peut être refusée.")
    prop.status = S.REJECTED
    prop.rejection_reason = reason
    prop.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(
        prop.owner,
        "property_rejected",
        "Votre annonce a été refusée",
        f"« {prop.title} » n'a pas été validée. Motif : {reason}\n"
        "Corrigez l'annonce puis soumettez-la à nouveau.",
    )


def admin_suspend_property(prop: Property, reason: str = "") -> None:
    prop.status = S.SUSPENDED
    prop.suspended_by_admin = True
    prop.rejection_reason = reason
    prop.save(update_fields=["status", "suspended_by_admin", "rejection_reason", "updated_at"])
    notify(
        prop.owner,
        "property_suspended",
        "Votre annonce a été suspendue",
        f"« {prop.title} » a été suspendue par l'administrateur. {reason}".strip(),
    )


def admin_unsuspend_property(prop: Property) -> None:
    if prop.status != S.SUSPENDED:
        raise BusinessError("Cette annonce n'est pas suspendue.")
    prop.status = S.PUBLISHED
    prop.suspended_by_admin = False
    prop.save(update_fields=["status", "suspended_by_admin", "updated_at"])
