"""Door registry for managing all door objects in the game."""

from src.models.models import Door
from src.models.core_data import GameFlag


class DoorRegistry:
    """Manages all Door objects in the game.

    Provides methods to load doors from YAML, retrieve them by ID or synonym,
    and find doors that connect to specific locations.
    """

    def __init__(self):
        """Initialize an empty door registry."""
        self._doors: dict[str, Door] = {}

    def load_from_list(self, data: list[dict]) -> None:
        """Load doors from parsed doors.yaml list.

        Args:
            data: List of door dictionaries from YAML file
        """
        flag_map = {f.name: f for f in GameFlag}
        for d in data:
            connects = tuple(d["connects"][:2])
            door = Door(
                id=d["id"],
                name=d["name"],
                base_description=d["base_description"],
                synonyms=d.get("synonyms", []),
                flags={flag_map[f] for f in d.get("flags", []) if f in flag_map},
                connects=connects,
                key_id=d.get("key_id"),
                unlock_condition=d.get("unlock_condition"),
            )
            self._doors[door.id] = door

    def get(self, door_id: str) -> Door | None:
        """Get a door by its ID.

        Args:
            door_id: The unique door identifier

        Returns:
            Door object or None if not found
        """
        return self._doors.get(door_id)

    def doors_for_location(self, location_id: str) -> list[Door]:
        """Return all doors that connect to a given location.

        Args:
            location_id: The location identifier to search for

        Returns:
            List of Door objects that connect to this location
        """
        return [d for d in self._doors.values() if location_id in d.connects]

    def find_by_synonym(self, query: str) -> Door | None:
        """Find a door by name or synonym.

        Args:
            query: The search term (case-insensitive)

        Returns:
            Door object or None if not found
        """
        q = query.lower().strip()
        for door in self._doors.values():
            if q == door.name.lower():
                return door
            if q in [s.lower() for s in door.synonyms]:
                return door
        return None
