"""Déduit la liste des pièces et l'ordre de la visite à partir des réponses de l'assistant.

Ordre retenu : on entre par le salon, on passe par les chambres, puis les pièces d'eau
intérieures, les espaces ouverts (balcon, terrasse) et enfin ce qui est dehors (cour,
cuisine ou douche extérieures). Le propriétaire peut ensuite réordonner.
"""
from dataclasses import dataclass

from .models import Room

INTERIOR, EXTERIOR, NONE, WITH_BATHROOM = "interior", "exterior", "none", "with_bathroom"


@dataclass
class PlannedRoom:
    room_type: str
    name: str
    is_exterior: bool = False


def build_room_plan(answers: dict) -> list[PlannedRoom]:
    bedrooms = answers.get("bedrooms", 0)
    kitchen = answers.get("kitchen", NONE)
    bathroom = answers.get("bathroom", NONE)
    toilet = answers.get("toilet", NONE)
    T = Room.Type

    inside: list[PlannedRoom] = []
    outside: list[PlannedRoom] = []

    if answers.get("living_room"):
        inside.append(PlannedRoom(T.LIVING_ROOM, "Salon"))
    for i in range(1, bedrooms + 1):
        inside.append(PlannedRoom(T.BEDROOM, "Chambre" if bedrooms == 1 else f"Chambre {i}"))
    if not inside:
        # Studio ou chambre simple : une seule pièce de vie.
        inside.append(PlannedRoom(T.BEDROOM, "Pièce principale"))

    def place(room: PlannedRoom, where: str):
        if where == INTERIOR:
            inside.append(room)
        elif where == EXTERIOR:
            room.is_exterior = True
            room.name = f"{room.name} (extérieur)"
            outside.append(room)

    place(PlannedRoom(T.KITCHEN, "Cuisine"), kitchen)
    if toilet == WITH_BATHROOM:
        place(PlannedRoom(T.BATHROOM, "Douche et WC"), bathroom)
    else:
        place(PlannedRoom(T.BATHROOM, "Douche"), bathroom)
        place(PlannedRoom(T.TOILET, "WC"), toilet)

    for name in answers.get("others", []):
        inside.append(PlannedRoom(T.OTHER, name.strip()))
    if answers.get("balcony"):
        inside.append(PlannedRoom(T.BALCONY, "Balcon"))
    if answers.get("terrace"):
        inside.append(PlannedRoom(T.TERRACE, "Terrasse"))
    if answers.get("yard"):
        outside.insert(0, PlannedRoom(T.YARD, "Cour", is_exterior=True))

    return inside + outside


def main_rooms_count(plan: list[PlannedRoom]) -> int:
    """Nombre de pièces au sens de l'annonce : salon + chambres."""
    return sum(1 for r in plan if r.room_type in (Room.Type.LIVING_ROOM, Room.Type.BEDROOM))
