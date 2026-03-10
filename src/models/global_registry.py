# src/models/global_registry.py
from dataclasses import dataclass, field
from src.models.models import Item
from src.models.core_data import GameFlag


@dataclass
class _LocalGlobalEntry:
    item: Item
    visible_in: list[str]


class GlobalRegistry:
    """
    Manages global and local-global objects.
    global_objects: visible in ALL locations.
    local_globals: visible only in declared locations.
    """

    def __init__(self):
        self._globals: list[Item] = []
        self._local_globals: list[_LocalGlobalEntry] = []

    def load_from_dict(self, data: dict) -> None:
        """Load from parsed globals.yaml dict."""
        flag_map = {f.name: f for f in GameFlag}

        for obj_data in data.get("global_objects", []):
            item = Item(
                id=obj_data["id"],
                name=obj_data["name"],
                base_description=obj_data["base_description"],
                synonyms=obj_data.get("synonyms", []),
                flags={flag_map[f] for f in obj_data.get("flags", []) if f in flag_map},
            )
            self._globals.append(item)

        for obj_data in data.get("local_globals", []):
            item = Item(
                id=obj_data["id"],
                name=obj_data["name"],
                base_description=obj_data["base_description"],
                synonyms=obj_data.get("synonyms", []),
                flags={flag_map[f] for f in obj_data.get("flags", []) if f in flag_map},
            )
            entry = _LocalGlobalEntry(
                item=item, visible_in=list(obj_data.get("visible_in", []))
            )
            self._local_globals.append(entry)

    def get_visible_objects(self, location_id: str) -> list[Item]:
        """Return all objects visible in this location."""
        result = list(self._globals)
        for entry in self._local_globals:
            if location_id in entry.visible_in:
                result.append(entry.item)
        return result

    def find(self, query: str, location_id: str) -> Item | None:
        """Find object by name/synonym visible in given location."""
        q = query.lower().strip()
        for obj in self.get_visible_objects(location_id):
            if q == obj.name.lower():
                return obj
            if q in [s.lower() for s in obj.synonyms]:
                return obj
        return None

    def activate_local_global(self, obj_id: str, location_ids: list[str]) -> None:
        """Add locations to a local-global's visible_in list (runtime activation)."""
        for entry in self._local_globals:
            if entry.item.id == obj_id:
                for loc_id in location_ids:
                    if loc_id not in entry.visible_in:
                        entry.visible_in.append(loc_id)
                return

    def deactivate_local_global(self, obj_id: str, location_id: str) -> None:
        """Remove a location from a local-global's visible_in list."""
        for entry in self._local_globals:
            if entry.item.id == obj_id:
                entry.visible_in = [
                    loc for loc in entry.visible_in if loc != location_id
                ]
                return
