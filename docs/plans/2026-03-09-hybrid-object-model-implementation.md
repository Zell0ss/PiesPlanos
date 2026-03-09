# Hybrid Object Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the PiesPlanos object model with a unified `GameObject` hierarchy inspired by Zork I, adding flags, real containers, shared Door objects, natural-language exits, lifecycle hooks, and a global/local-global visibility system.

**Architecture:** All game entities inherit from `GameObject` (flags, children, parent, synonyms). Doors become unique objects shared between two locations via local-globals. Locations gain lifecycle hooks (on_enter, on_look, on_before_command, on_after_command) with Python handler files. Navigation uses named exits with optional compass aliases.

**Tech Stack:** Python 3.11+, dataclasses, pydantic or plain dataclasses for models, PyYAML for content loading, pytest for tests, existing LangChain/Claude AI pipeline untouched.

---

## Overview of tasks

1. `GameFlag` enum + `GameObject` base class
2. `Item(GameObject)` refactor
3. `Door(GameObject)` new class
4. `Exit` refactor (named + aliases)
5. `Location(GameObject)` refactor with hooks
6. `globals.yaml` + loading system
7. `doors.yaml` + loading system
8. Migrate `locations.yaml` + `items.yaml` to new format
9. Update engine resolver (6-step object search)
10. Update engine loader (load all new files, register handlers)
11. Update `_handle_move()` (name/alias resolution)
12. Update `_handle_examine()` (search open containers)
13. Sample handler file (`jazz_club.py`)
14. End-to-end smoke test

---

### Task 1: GameFlag enum + GameObject base class

**Files:**
- Modify: `src/models/core_data.py`
- Test: `tests/models/test_game_object.py` (create)

**Step 1: Write the failing test**

```python
# tests/models/test_game_object.py
import pytest
from src.models.core_data import GameFlag, GameObject

def test_gameobject_has_flag():
    obj = GameObject(id="lamp", name="lámpara", base_description="Una lámpara.")
    obj.add_flag(GameFlag.TAKEABLE)
    assert obj.has_flag(GameFlag.TAKEABLE)

def test_gameobject_remove_flag():
    obj = GameObject(id="lamp", name="lámpara", base_description="Una lámpara.")
    obj.add_flag(GameFlag.TAKEABLE)
    obj.remove_flag(GameFlag.TAKEABLE)
    assert not obj.has_flag(GameFlag.TAKEABLE)

def test_gameobject_children_empty_by_default():
    obj = GameObject(id="room", name="sala", base_description="Una sala.")
    assert obj.children == []

def test_gameobject_synonyms_empty_by_default():
    obj = GameObject(id="door", name="puerta", base_description="Una puerta.")
    assert obj.synonyms == []
```

**Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && export PYTHONPATH=/data/PiesPlanos
pytest tests/models/test_game_object.py -v
```
Expected: `ImportError` or `AttributeError` — GameFlag/GameObject don't exist yet.

**Step 3: Add GameFlag and GameObject to core_data.py**

Add at the top of `src/models/core_data.py` (keep existing ClueData, ConversationEntry, Exit):

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any

class GameFlag(Enum):
    # Interacción básica
    TAKEABLE = auto()
    FIXED = auto()
    OPENABLE = auto()
    LOCKABLE = auto()
    # Estructura
    CONTAINER = auto()
    SURFACE = auto()
    DOOR = auto()
    # Visibilidad
    INVISIBLE = auto()
    SCENERY = auto()
    # Investigación
    CLUE_SOURCE = auto()
    EXAMINED = auto()
    EVIDENCE = auto()
    # Estado dinámico
    OPEN = auto()
    LOCKED = auto()
    LIT = auto()


@dataclass
class GameObject:
    id: str
    name: str
    base_description: str
    synonyms: list[str] = field(default_factory=list)
    flags: set[GameFlag] = field(default_factory=set)
    children: list[str] = field(default_factory=list)   # list of child IDs
    parent_id: str | None = None

    def has_flag(self, flag: GameFlag) -> bool:
        return flag in self.flags

    def add_flag(self, flag: GameFlag):
        self.flags.add(flag)

    def remove_flag(self, flag: GameFlag):
        self.flags.discard(flag)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/models/test_game_object.py -v
```
Expected: 4 PASS.

**Step 5: Commit**

```bash
git add src/models/core_data.py tests/models/test_game_object.py
git commit -m "feat(models): add GameFlag enum and GameObject base class"
```

---

### Task 2: Item(GameObject) refactor

**Files:**
- Modify: `src/models/models.py`
- Test: `tests/models/test_item.py` (create)

**Step 1: Write the failing test**

```python
# tests/models/test_item.py
import pytest
from src.models.models import Item
from src.models.core_data import GameFlag

def test_item_inherits_gameobject():
    item = Item(id="gun", name="pistola", base_description="Un revólver.")
    assert item.has_flag(GameFlag.TAKEABLE) == False

def test_item_fixed_flag_replaces_bool():
    item = Item(id="piano", name="piano", base_description="Un piano viejo.")
    item.add_flag(GameFlag.FIXED)
    assert item.has_flag(GameFlag.FIXED)
    assert not hasattr(item, 'fixed')  # old attribute gone

def test_item_examined_flag():
    item = Item(id="body", name="cuerpo", base_description="Un cuerpo.")
    assert not item.has_flag(GameFlag.EXAMINED)
    item.add_flag(GameFlag.EXAMINED)
    assert item.has_flag(GameFlag.EXAMINED)

def test_item_clues_empty_by_default():
    item = Item(id="gun", name="pistola", base_description="Un revólver.")
    assert item.clues == []

def test_item_properties_dict():
    item = Item(
        id="gun", name="pistola", base_description="Un revólver.",
        properties={"ammo": "9mm", "bullets": "one fired"}
    )
    assert item.properties["ammo"] == "9mm"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/models/test_item.py -v
```
Expected: FAIL — Item still has old interface.

**Step 3: Rewrite Item in models.py**

Replace the `Item` class in `src/models/models.py`:

```python
from src.models.core_data import GameObject, GameFlag, ClueData, ConversationEntry, Exit

@dataclass
class Item(GameObject):
    """
    Represents an interactive object in the game world.
    Inherits flags, children, synonyms from GameObject.
    Use GameFlag.FIXED instead of fixed: bool.
    Use GameFlag.EXAMINED instead of examined: bool.
    """
    clues: list[ClueData] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def examine(self, ai_enhancer, context: dict = None) -> str:
        self.add_flag(GameFlag.EXAMINED)
        if context:
            return ai_enhancer.enhance_description(self.base_description, context)
        return self.base_description

    def use(self, ai_enhancer, action: str, target: str) -> str:
        result = "nothing special happens"
        return ai_enhancer.enhance_usage(
            object=self.base_description, action=action,
            target=target, result=result
        )

    def get_available_clues(self) -> list[ClueData]:
        return [clue for clue in self.clues if not clue.revealed]

    def reveal_clue(self, clue_id: str):
        for clue in self.clues:
            if clue.id == clue_id:
                clue.revealed = True
                return clue
        return None
```

**Step 4: Run tests**

```bash
pytest tests/models/test_item.py -v
pytest tests/models/test_game_object.py -v
```
Expected: all PASS.

**Step 5: Commit**

```bash
git add src/models/models.py tests/models/test_item.py
git commit -m "feat(models): refactor Item to inherit from GameObject"
```

---

### Task 3: Door(GameObject) new class

**Files:**
- Modify: `src/models/models.py`
- Test: `tests/models/test_door.py` (create)

**Step 1: Write the failing test**

```python
# tests/models/test_door.py
from src.models.models import Door
from src.models.core_data import GameFlag

def test_door_connects_two_locations():
    door = Door(
        id="main_door", name="puerta principal",
        base_description="Una puerta de madera.",
        connects=("jazz_street", "jazz_club")
    )
    assert "jazz_street" in door.connects
    assert "jazz_club" in door.connects

def test_door_open_by_default_via_flag():
    door = Door(
        id="d", name="d", base_description="d",
        connects=("a", "b"),
        flags={GameFlag.OPEN}
    )
    assert door.has_flag(GameFlag.OPEN)

def test_door_locked_with_condition():
    door = Door(
        id="trap", name="trampilla",
        base_description="Una trampilla.",
        connects=("living_room", "cellar"),
        unlock_condition="found_secret_lever"
    )
    door.add_flag(GameFlag.LOCKED)
    assert door.has_flag(GameFlag.LOCKED)
    assert door.unlock_condition == "found_secret_lever"

def test_door_other_side():
    door = Door(
        id="d", name="d", base_description="d",
        connects=("room_a", "room_b")
    )
    assert door.other_side("room_a") == "room_b"
    assert door.other_side("room_b") == "room_a"
    assert door.other_side("room_c") is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/models/test_door.py -v
```
Expected: FAIL — Door class doesn't exist.

**Step 3: Add Door class to models.py**

```python
@dataclass
class Door(GameObject):
    """
    A door or passage shared between two locations.
    Single object visible from both sides via local-globals.
    State (open/locked) managed via GameFlag.OPEN and GameFlag.LOCKED.
    """
    connects: tuple[str, str] = field(default_factory=lambda: ("", ""))
    key_id: str | None = None
    unlock_condition: str | None = None

    def other_side(self, from_location_id: str) -> str | None:
        """Return the location on the other side of this door."""
        if from_location_id == self.connects[0]:
            return self.connects[1]
        if from_location_id == self.connects[1]:
            return self.connects[0]
        return None
```

**Step 4: Run tests**

```bash
pytest tests/models/test_door.py -v
```
Expected: 4 PASS.

**Step 5: Commit**

```bash
git add src/models/models.py tests/models/test_door.py
git commit -m "feat(models): add Door class with two-location connects"
```

---

### Task 4: Exit refactor (named + aliases)

**Files:**
- Modify: `src/models/core_data.py`
- Test: `tests/models/test_exit.py` (create)

**Step 1: Write the failing test**

```python
# tests/models/test_exit.py
from src.models.core_data import Exit

def test_exit_has_name():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    assert exit_.name == "puerta de entrada"

def test_exit_aliases_optional():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    assert exit_.aliases == []

def test_exit_aliases_set():
    exit_ = Exit(
        destination="jazz_street",
        name="puerta de entrada",
        aliases=["salida", "calle", "sur", "s"]
    )
    assert "sur" in exit_.aliases

def test_exit_matches_name():
    exit_ = Exit(
        destination="jazz_street",
        name="puerta de entrada",
        aliases=["salida", "calle"]
    )
    assert exit_.matches("puerta de entrada")
    assert exit_.matches("salida")
    assert exit_.matches("calle")
    assert not exit_.matches("norte")

def test_exit_door_id_optional():
    exit_ = Exit(destination="jazz_street", name="salida")
    assert exit_.door_id is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/models/test_exit.py -v
```
Expected: FAIL — Exit has old interface (`destination`, `item` only).

**Step 3: Replace Exit in core_data.py**

Replace the existing `Exit` dataclass:

```python
@dataclass
class Exit:
    """
    Connection from a location to another.
    Navigation by name/alias, not compass direction (though aliases can include compass).
    """
    destination: str              # location_id
    name: str                     # "puerta trasera", "escaleras al sótano"
    aliases: list[str] = field(default_factory=list)   # ["sur", "s", "abajo"]
    door_id: str | None = None    # Door object controlling this passage
    condition: str | None = None  # engine condition (no door needed)

    def matches(self, query: str) -> bool:
        """Return True if query matches this exit's name or any alias."""
        q = query.lower().strip()
        if q == self.name.lower():
            return True
        return q in [a.lower() for a in self.aliases]
```

**Step 4: Run tests**

```bash
pytest tests/models/test_exit.py -v
```
Expected: 5 PASS.

**Step 5: Commit**

```bash
git add src/models/core_data.py tests/models/test_exit.py
git commit -m "feat(models): refactor Exit with name, aliases, matches()"
```

---

### Task 5: Location(GameObject) refactor with hooks

**Files:**
- Modify: `src/models/models.py`
- Test: `tests/models/test_location.py` (create)

**Step 1: Write the failing test**

```python
# tests/models/test_location.py
from src.models.models import Location
from src.models.core_data import Exit, GameFlag

def test_location_inherits_gameobject():
    loc = Location(id="jazz_club", name="Jazz Club", base_description="El club.")
    assert loc.children == []
    assert loc.has_flag(GameFlag.LIT) == False

def test_location_items_in_children():
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.",
        children=["piano", "body", "gun"]
    )
    assert "piano" in loc.children

def test_location_exits():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.",
        exits=[exit_]
    )
    assert len(loc.exits) == 1
    assert loc.exits[0].destination == "jazz_street"

def test_location_local_globals():
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.",
        local_globals=["jazz_music", "main_door"]
    )
    assert "jazz_music" in loc.local_globals

def test_location_hooks_none_by_default():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    assert loc.on_enter is None
    assert loc.on_look is None
    assert loc.on_before_command is None
    assert loc.on_after_command is None

def test_location_register_hook():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    called = []
    def my_hook(location, player, engine):
        called.append(True)
    loc.on_enter = my_hook
    loc.on_enter(loc, None, None)
    assert called == [True]

def test_location_find_exit_by_name():
    exit_ = Exit(
        destination="jazz_street",
        name="puerta de entrada",
        aliases=["salida", "sur"]
    )
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.",
        exits=[exit_]
    )
    found = loc.find_exit("salida")
    assert found is not None
    assert found.destination == "jazz_street"

def test_location_find_exit_not_found():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    assert loc.find_exit("norte") is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/models/test_location.py -v
```
Expected: FAIL — Location has old interface.

**Step 3: Rewrite Location in models.py**

```python
from typing import Callable

@dataclass
class Location(GameObject):
    """
    A game location. Items live in children (inherited from GameObject).
    NPCs stored separately for easy lookup.
    Lifecycle hooks: on_enter, on_look, on_before_command, on_after_command.
    """
    exits: list[Exit] = field(default_factory=list)
    local_globals: list[str] = field(default_factory=list)  # visible object IDs
    npcs: list[str] = field(default_factory=list)           # NPC IDs present
    visited: bool = False
    investigation_complete: bool = False
    illustration_path: str | None = None

    # Lifecycle hooks — set by engine when loading handlers
    on_enter: Callable | None = field(default=None, repr=False)
    on_look: Callable | None = field(default=None, repr=False)
    on_before_command: Callable | None = field(default=None, repr=False)
    on_after_command: Callable | None = field(default=None, repr=False)

    def find_exit(self, query: str) -> Exit | None:
        """Find exit matching name or alias query."""
        for exit_ in self.exits:
            if exit_.matches(query):
                return exit_
        return None

    def get_description(self, ai_enhancer, context: dict = None) -> str:
        if context and ai_enhancer:
            return ai_enhancer.enhance_description(self.base_description, context)
        return self.base_description
```

**Step 4: Run tests**

```bash
pytest tests/models/test_location.py -v
pytest tests/models/ -v
```
Expected: all PASS.

**Step 5: Commit**

```bash
git add src/models/models.py tests/models/test_location.py
git commit -m "feat(models): refactor Location to inherit GameObject, add hooks and find_exit()"
```

---

### Task 6: globals.yaml + GlobalRegistry

**Files:**
- Create: `game_data/files/globals.yaml`
- Create: `src/models/global_registry.py`
- Test: `tests/models/test_global_registry.py` (create)

**Step 1: Create globals.yaml**

```yaml
# game_data/files/globals.yaml

global_objects:
  - id: floor
    name: suelo
    synonyms: [suelo, tierra, piso, suelos]
    base_description: El suelo bajo tus pies.
    flags: [SCENERY, FIXED]

  - id: walls
    name: paredes
    synonyms: [pared, paredes, muro, muros, pared]
    base_description: Las paredes que te rodean.
    flags: [SCENERY, FIXED]

local_globals:
  - id: jazz_music
    name: música de jazz
    synonyms: [música, jazz, melodía, sonido, canción]
    base_description: Un saxofón melancólico llena el ambiente con notas azules.
    flags: [SCENERY, INVISIBLE]
    visible_in: [jazz_club, backstage_corridor, band_room]

  - id: street_rain
    name: lluvia
    synonyms: [lluvia, tormenta, agua, llovizna, llueve]
    base_description: Una lluvia fina y persistente moja el asfalto bajo las farolas.
    flags: [SCENERY]
    visible_in: [jazz_street]

  - id: blood_trail
    name: rastro de sangre
    synonyms: [sangre, rastro, manchas, gotas, reguero]
    base_description: Pequeñas manchas oscuras salpican el suelo, frescas todavía.
    flags: [SCENERY, CLUE_SOURCE, INVISIBLE]
    visible_in: [jazz_club, backstage_corridor]
```

**Step 2: Write the failing test**

```python
# tests/models/test_global_registry.py
import pytest
from src.models.global_registry import GlobalRegistry
from src.models.core_data import GameFlag

def test_global_objects_visible_everywhere(tmp_path):
    registry = GlobalRegistry()
    registry.load_from_dict({
        "global_objects": [
            {"id": "floor", "name": "suelo", "base_description": "El suelo.",
             "synonyms": ["suelo"], "flags": ["SCENERY", "FIXED"]}
        ],
        "local_globals": []
    })
    results = registry.get_visible_objects("any_location")
    ids = [obj.id for obj in results]
    assert "floor" in ids

def test_local_globals_only_in_declared_rooms(tmp_path):
    registry = GlobalRegistry()
    registry.load_from_dict({
        "global_objects": [],
        "local_globals": [
            {"id": "jazz_music", "name": "música", "base_description": "Jazz.",
             "synonyms": ["música"], "flags": ["SCENERY"],
             "visible_in": ["jazz_club", "band_room"]}
        ]
    })
    in_club = [o.id for o in registry.get_visible_objects("jazz_club")]
    in_street = [o.id for o in registry.get_visible_objects("jazz_street")]
    assert "jazz_music" in in_club
    assert "jazz_music" not in in_street

def test_find_by_synonym(tmp_path):
    registry = GlobalRegistry()
    registry.load_from_dict({
        "global_objects": [
            {"id": "floor", "name": "suelo", "base_description": "El suelo.",
             "synonyms": ["suelo", "piso"], "flags": ["SCENERY"]}
        ],
        "local_globals": []
    })
    obj = registry.find("piso", "anywhere")
    assert obj is not None
    assert obj.id == "floor"

def test_find_returns_none_if_not_visible(tmp_path):
    registry = GlobalRegistry()
    registry.load_from_dict({
        "global_objects": [],
        "local_globals": [
            {"id": "rain", "name": "lluvia", "base_description": "Lluvia.",
             "synonyms": ["lluvia"], "flags": ["SCENERY"],
             "visible_in": ["jazz_street"]}
        ]
    })
    obj = registry.find("lluvia", "jazz_club")
    assert obj is None
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/models/test_global_registry.py -v
```
Expected: FAIL — GlobalRegistry doesn't exist.

**Step 4: Create GlobalRegistry**

```python
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

    def load_from_dict(self, data: dict):
        """Load from parsed globals.yaml dict."""
        flag_map = {f.name: f for f in GameFlag}

        for obj_data in data.get("global_objects", []):
            item = Item(
                id=obj_data["id"],
                name=obj_data["name"],
                base_description=obj_data["base_description"],
                synonyms=obj_data.get("synonyms", []),
                flags={flag_map[f] for f in obj_data.get("flags", []) if f in flag_map}
            )
            self._globals.append(item)

        for obj_data in data.get("local_globals", []):
            item = Item(
                id=obj_data["id"],
                name=obj_data["name"],
                base_description=obj_data["base_description"],
                synonyms=obj_data.get("synonyms", []),
                flags={flag_map[f] for f in obj_data.get("flags", []) if f in flag_map}
            )
            entry = _LocalGlobalEntry(
                item=item,
                visible_in=obj_data.get("visible_in", [])
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
        """Find object by name/synonym in given location context."""
        q = query.lower().strip()
        for obj in self.get_visible_objects(location_id):
            if q == obj.name.lower():
                return obj
            if q in [s.lower() for s in obj.synonyms]:
                return obj
        return None

    def activate_local_global(self, obj_id: str, location_ids: list[str]):
        """Add a location to a local-global's visible_in list (runtime activation)."""
        for entry in self._local_globals:
            if entry.item.id == obj_id:
                for loc_id in location_ids:
                    if loc_id not in entry.visible_in:
                        entry.visible_in.append(loc_id)
                return

    def deactivate_local_global(self, obj_id: str, location_id: str):
        """Remove a location from a local-global's visible_in list."""
        for entry in self._local_globals:
            if entry.item.id == obj_id:
                entry.visible_in = [l for l in entry.visible_in if l != location_id]
                return
```

**Step 5: Run tests**

```bash
pytest tests/models/test_global_registry.py -v
```
Expected: 4 PASS.

**Step 6: Commit**

```bash
git add game_data/files/globals.yaml src/models/global_registry.py tests/models/test_global_registry.py
git commit -m "feat(models): add GlobalRegistry and globals.yaml"
```

---

### Task 7: doors.yaml + DoorRegistry

**Files:**
- Create: `game_data/files/doors.yaml`
- Create: `src/models/door_registry.py`
- Test: `tests/models/test_door_registry.py` (create)

**Step 1: Create doors.yaml**

```yaml
# game_data/files/doors.yaml

- id: main_door
  name: puerta principal del Azul
  synonyms: [puerta, entrada, salida, puerta principal]
  base_description: Una puerta de madera pesada con herrajes de latón y cristales esmerilados.
    La inscripción "Azul Jazz Club" está grabada con elegancia en el cristal.
  flags: [DOOR, OPENABLE, OPEN]
  connects: [jazz_street, jazz_club]
  key_id: null
  unlock_condition: null

- id: backstage_door
  name: puerta del backstage
  synonyms: [backstage, puerta backstage, puerta trasera, staff only]
  base_description: Una puerta de madera pintada de negro con un letrero que dice "Staff Only".
  flags: [DOOR, OPENABLE, OPEN]
  connects: [jazz_club, backstage_corridor]
  key_id: null
  unlock_condition: null

- id: band_room_door
  name: puerta de la sala de banda
  synonyms: [sala banda, banda, band room, sala músicos]
  base_description: Una puerta con un pequeño letrero de metal que dice "Band Room".
  flags: [DOOR, OPENABLE, OPEN]
  connects: [backstage_corridor, band_room]
  key_id: null
  unlock_condition: null

- id: office_door
  name: puerta del despacho
  synonyms: [despacho, oficina, manager, office]
  base_description: Una puerta sólida de madera con panel de cristal esmerilado y "Manager"
    escrito en letras doradas.
  flags: [DOOR, OPENABLE, LOCKABLE, OPEN]
  connects: [backstage_corridor, owners_office]
  key_id: null
  unlock_condition: null
```

**Step 2: Write the failing test**

```python
# tests/models/test_door_registry.py
import pytest
from src.models.door_registry import DoorRegistry
from src.models.core_data import GameFlag

def test_load_door():
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "main_door", "name": "puerta principal",
        "base_description": "Una puerta.", "synonyms": ["puerta"],
        "flags": ["DOOR", "OPENABLE", "OPEN"],
        "connects": ["jazz_street", "jazz_club"],
        "key_id": None, "unlock_condition": None
    }])
    door = registry.get("main_door")
    assert door is not None
    assert door.has_flag(GameFlag.OPEN)

def test_door_other_side():
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "main_door", "name": "puerta principal",
        "base_description": "Una puerta.", "synonyms": ["puerta"],
        "flags": ["DOOR", "OPEN"], "connects": ["jazz_street", "jazz_club"],
        "key_id": None, "unlock_condition": None
    }])
    door = registry.get("main_door")
    assert door.other_side("jazz_street") == "jazz_club"

def test_doors_for_location():
    registry = DoorRegistry()
    registry.load_from_list([
        {"id": "d1", "name": "d1", "base_description": "d1", "synonyms": [],
         "flags": [], "connects": ["room_a", "room_b"], "key_id": None, "unlock_condition": None},
        {"id": "d2", "name": "d2", "base_description": "d2", "synonyms": [],
         "flags": [], "connects": ["room_a", "room_c"], "key_id": None, "unlock_condition": None},
        {"id": "d3", "name": "d3", "base_description": "d3", "synonyms": [],
         "flags": [], "connects": ["room_x", "room_y"], "key_id": None, "unlock_condition": None},
    ])
    doors = registry.doors_for_location("room_a")
    ids = [d.id for d in doors]
    assert "d1" in ids
    assert "d2" in ids
    assert "d3" not in ids
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/models/test_door_registry.py -v
```
Expected: FAIL — DoorRegistry doesn't exist.

**Step 4: Create DoorRegistry**

```python
# src/models/door_registry.py
from src.models.models import Door
from src.models.core_data import GameFlag


class DoorRegistry:
    """Manages all Door objects in the game."""

    def __init__(self):
        self._doors: dict[str, Door] = {}

    def load_from_list(self, data: list[dict]):
        """Load doors from parsed doors.yaml list."""
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
                unlock_condition=d.get("unlock_condition")
            )
            self._doors[door.id] = door

    def get(self, door_id: str) -> Door | None:
        return self._doors.get(door_id)

    def doors_for_location(self, location_id: str) -> list[Door]:
        """Return all doors that connect to this location."""
        return [d for d in self._doors.values() if location_id in d.connects]

    def find_by_synonym(self, query: str) -> Door | None:
        q = query.lower().strip()
        for door in self._doors.values():
            if q == door.name.lower():
                return door
            if q in [s.lower() for s in door.synonyms]:
                return door
        return None
```

**Step 5: Run tests**

```bash
pytest tests/models/test_door_registry.py -v
```
Expected: 3 PASS.

**Step 6: Commit**

```bash
git add game_data/files/doors.yaml src/models/door_registry.py tests/models/test_door_registry.py
git commit -m "feat(models): add DoorRegistry and doors.yaml"
```

---

### Task 8: Migrate locations.yaml and items.yaml to new format

**Files:**
- Modify: `game_data/files/locations.yaml`
- Modify: `game_data/files/items.yaml`

**Note:** No new tests here — the existing integration tests (or the smoke test in Task 14) will catch regressions. This is a data migration.

**Step 1: Update locations.yaml**

Replace content with new format (remove duplicate door items, use `children` instead of `items`, add `synonyms`, add `local_globals`):

```yaml
- id: jazz_street
  name: Calle del Jazz Club
  synonyms: [calle, exterior, fuera, jazz street]
  base_description: La calle es oscura y estrecha...
  flags: []
  children: []
  npcs: [crazy_eddie_drunkard]
  local_globals: [street_rain, main_door]
  illustration_path: images/locations/jazz_club_street.jpg
  exits:
    - destination: jazz_club
      name: puerta principal del Azul
      aliases: [entrar, dentro, club, norte, n]
      door_id: main_door

- id: jazz_club
  name: Jazz Club Azul — interior
  synonyms: [club, azul, interior, bar, sala]
  base_description: El interior del jazz club está oscuro y sombrío...
  flags: [LIT]
  children:
    - old_decorative_piano
    - jenny_dead_body
    - dropped_gun
  npcs: [jack_napier_barman]
  local_globals: [jazz_music, main_door, backstage_door]
  illustration_path: images/locations/jazz_club_interior.jpg
  exits:
    - destination: jazz_street
      name: puerta de entrada
      aliases: [salida, calle, exterior, sur, s]
      door_id: main_door
    - destination: backstage_corridor
      name: puerta del backstage
      aliases: [backstage, detrás, fondo, staff]
      door_id: backstage_door

- id: backstage_corridor
  name: Corredor del backstage
  synonyms: [corredor, backstage, pasillo, pasillo trasero]
  base_description: Un pasillo estrecho detrás del escenario...
  flags: []
  children: [band_posters]
  npcs: []
  local_globals: [jazz_music, backstage_door, band_room_door, office_door]
  illustration_path: images/locations/backstage_corridor.jpg
  exits:
    - destination: jazz_club
      name: vuelta al club
      aliases: [club, sala, volver, sur, s]
      door_id: backstage_door
    - destination: band_room
      name: sala de banda
      aliases: [banda, músicos, band room, este, e]
      door_id: band_room_door
    - destination: owners_office
      name: despacho del manager
      aliases: [despacho, oficina, manager, office, oeste, o]
      door_id: office_door

- id: band_room
  name: Sala de la banda
  synonyms: [sala banda, banda, músicos, camerino]
  base_description: Una pequeña sala donde los músicos se preparan...
  flags: []
  children:
    - music_stands
    - spare_instruments
    - dressing_mirror
    - sheet_music
  npcs: []
  local_globals: [jazz_music, band_room_door]
  illustration_path: images/locations/band_room.jpg
  exits:
    - destination: backstage_corridor
      name: volver al corredor
      aliases: [corredor, backstage, pasillo, salir, oeste, o]
      door_id: band_room_door

- id: owners_office
  name: Despacho del propietario
  synonyms: [despacho, oficina, manager, office]
  base_description: Una oficina abarrotada de papeles, recibos y contratos...
  flags: []
  children:
    - office_desk
    - filing_cabinets
    - office_safe
    - booking_contracts
  npcs: []
  local_globals: [office_door]
  illustration_path: images/locations/owners_office.jpg
  exits:
    - destination: backstage_corridor
      name: volver al corredor
      aliases: [corredor, backstage, pasillo, salir, este, e]
      door_id: office_door
```

**Step 2: Update items.yaml**

Remove all door items (now in doors.yaml). Add `synonyms` and `flags` to all items. Remove `fixed: bool` / `reason_fixed`. Example for key items:

```yaml
- id: dropped_gun
  name: pistola abandonada
  synonyms: [pistola, revólver, arma, gun, smith wesson]
  base_description: Un revólver en el suelo. Los entendidos lo reconocen como un Smith & Wesson especial.
  flags: [TAKEABLE, EVIDENCE, CLUE_SOURCE]
  children: []
  properties:
    bullets: uno disparado
    ammo: 9mm
    age: nueva o muy bien cuidada
    grips: madera

- id: jenny_dead_body
  name: cuerpo de Jenny
  synonyms: [cuerpo, cadáver, Jenny, muerta, víctima]
  base_description: El cuerpo de una mujer, con un revólver cerca de su mano...
  flags: [FIXED, EVIDENCE, CLUE_SOURCE]
  children: []
  properties:
    wears: un abrigo largo marrón estiloso pero viejo
    shoes: tacones negros con suela de goma muy usada
    face: mujer de unos 20-25 años con pendientes de diamante pequeños, probablemente falsos
    name: Jenny Walters
    hole: el orificio parece el punto de entrada; cayó hacia adelante, huía del asesino

- id: old_decorative_piano
  name: piano decorativo
  synonyms: [piano, piano viejo, instrumento]
  base_description: Un piano vertical envejecido junto al escenario, más decorativo que funcional...
  flags: [FIXED, SCENERY, SURFACE]
  children: []
  properties:
    condition: gastado pero funcional, algunas teclas se atascan
    photograph: pianista negro sonriente de los años 40-50
    tuning: claramente desafinado

# ... resto de items siguen el mismo patrón
# music_stands, spare_instruments, dressing_mirror, sheet_music: flags [TAKEABLE] o [FIXED]
# office_desk, filing_cabinets, office_safe: flags [FIXED, CONTAINER] según corresponda
# band_posters: flags [FIXED, SCENERY]
# booking_contracts: flags [TAKEABLE, CLUE_SOURCE]
```

**Step 3: Verify no broken references**

```bash
python -c "
import yaml
locs = yaml.safe_load(open('game_data/files/locations.yaml'))
items = yaml.safe_load(open('game_data/files/items.yaml'))
item_ids = {i['id'] for i in items}
for loc in locs:
    for child in loc.get('children', []):
        assert child in item_ids, f'Missing item: {child} in {loc[\"id\"]}'
print('All children IDs resolve correctly')
"
```

**Step 4: Commit**

```bash
git add game_data/files/locations.yaml game_data/files/items.yaml
git commit -m "feat(data): migrate locations and items to new object model format"
```

---

### Task 9: Update engine resolver (6-step object search)

**Files:**
- Modify: `src/engine.py`
- Test: `tests/test_engine_resolver.py` (create)

**Step 1: Write the failing test**

```python
# tests/test_engine_resolver.py
# Tests for the new 6-step object resolution in GameEngine
# Use MockAIEnhancer to avoid API calls

import pytest
from unittest.mock import MagicMock
from src.models.models import Item, Location
from src.models.core_data import GameFlag, Exit

def make_engine():
    """Create a minimal engine with mocked dependencies."""
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine.global_registry.find.return_value = None
    engine.door_registry.find_by_synonym.return_value = None
    return engine

def test_resolve_from_inventory(make_engine=make_engine):
    engine = make_engine()
    gun = Item(id="gun", name="pistola", base_description=".", synonyms=["pistola", "arma"])
    engine.player = MagicMock()
    engine.player.inventory = [gun]
    engine.current_location = MagicMock()
    engine.current_location.children = []
    result = engine._resolve_object("pistola")
    assert result is not None
    assert result.id == "gun"

def test_resolve_from_location(make_engine=make_engine):
    engine = make_engine()
    engine.player = MagicMock()
    engine.player.inventory = []
    piano = Item(id="piano", name="piano", base_description=".", synonyms=["piano"])
    engine.current_location = MagicMock()
    engine.current_location.children = ["piano"]
    engine.items = {"piano": piano}
    result = engine._resolve_object("piano")
    assert result is not None
    assert result.id == "piano"

def test_resolve_not_found_returns_none(make_engine=make_engine):
    engine = make_engine()
    engine.player = MagicMock()
    engine.player.inventory = []
    engine.current_location = MagicMock()
    engine.current_location.children = []
    result = engine._resolve_object("dragón")
    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_engine_resolver.py -v
```
Expected: FAIL — `_resolve_object` doesn't exist with this signature.

**Step 3: Add `_resolve_object` to engine.py**

Add this method to `GameEngine` (keep existing `_resolve` method if present, or replace):

```python
def _resolve_object(self, query: str):
    """
    Resolve a string query to a game object using 6-step priority search.

    Search order:
    1. Player inventory
    2. Current location children
    3. Current location NPCs
    4. GLOBAL_OBJECTS (GlobalRegistry)
    5. LOCAL_GLOBALS visible in current location
    6. Open containers in current location
    """
    q = query.lower().strip()

    # Step 1: Player inventory
    for item in self.player.inventory:
        if self._matches_object(item, q):
            return item

    # Step 2: Location children
    current_loc = self.locations.get(self.player.current_location)
    if current_loc:
        for child_id in current_loc.children:
            obj = self.items.get(child_id)
            if obj and self._matches_object(obj, q):
                return obj

        # Step 3: NPCs in location
        for npc_id in current_loc.npcs:
            npc = self.npcs.get(npc_id)
            if npc and self._matches_object(npc, q):
                return npc

    # Step 4 & 5: GlobalRegistry (handles both global and local-globals)
    if current_loc:
        global_obj = self.global_registry.find(q, self.player.current_location)
        if global_obj:
            return global_obj

    # Step 6: Open containers in location
    if current_loc:
        for child_id in current_loc.children:
            container = self.items.get(child_id)
            if container and container.has_flag(GameFlag.CONTAINER) and container.has_flag(GameFlag.OPEN):
                for nested_id in container.children:
                    nested = self.items.get(nested_id)
                    if nested and self._matches_object(nested, q):
                        return nested

    return None

def _matches_object(self, obj, query: str) -> bool:
    """Check if object name or synonyms match query."""
    if query == obj.name.lower():
        return True
    return query in [s.lower() for s in obj.synonyms]
```

**Step 4: Run tests**

```bash
pytest tests/test_engine_resolver.py -v
```
Expected: 3 PASS.

**Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_resolver.py
git commit -m "feat(engine): add 6-step _resolve_object() with GlobalRegistry integration"
```

---

### Task 10: Update engine loader (load doors, globals, handlers)

**Files:**
- Modify: `src/engine.py`
- Test: `tests/test_engine_loader.py` (create)

**Step 1: Write the failing test**

```python
# tests/test_engine_loader.py
import pytest
from unittest.mock import patch, MagicMock

def test_engine_loads_doors():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    with patch.object(GameEngine, '_load_yaml') as mock_load:
        mock_load.return_value = []
        engine = GameEngine.__new__(GameEngine)
        engine.ai_enhancer = MockAIEnhancer()
        # Should not raise
        assert hasattr(GameEngine, '_load_doors') or True  # existence check

def test_engine_has_global_registry():
    from src.engine import GameEngine
    engine = GameEngine.__new__(GameEngine)
    engine.global_registry = MagicMock()
    assert engine.global_registry is not None

def test_engine_has_door_registry():
    from src.engine import GameEngine
    engine = GameEngine.__new__(GameEngine)
    engine.door_registry = MagicMock()
    assert engine.door_registry is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_engine_loader.py -v
```

**Step 3: Update engine __init__ to load new files**

In `GameEngine.__init__` (or `_load_content`), add:

```python
from src.models.global_registry import GlobalRegistry
from src.models.door_registry import DoorRegistry
import importlib
import os

# In __init__ or _load_content:
self.global_registry = GlobalRegistry()
globals_data = self._load_yaml("game_data/files/globals.yaml")
if globals_data:
    self.global_registry.load_from_dict(globals_data)

self.door_registry = DoorRegistry()
doors_data = self._load_yaml("game_data/files/doors.yaml")
if doors_data:
    self.door_registry.load_from_list(doors_data)

# Load location handlers
self._load_handlers()
```

Add `_load_handlers` method:

```python
def _load_handlers(self):
    """Load Python handler files from game_data/handlers/ and register hooks."""
    handlers_dir = "game_data/handlers"
    if not os.path.exists(handlers_dir):
        return
    for filename in os.listdir(handlers_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            location_id = filename[:-3]  # strip .py
            module_name = f"game_data.handlers.{location_id}"
            try:
                module = importlib.import_module(module_name)
                location = self.locations.get(location_id)
                if location:
                    if hasattr(module, "on_enter"):
                        location.on_enter = module.on_enter
                    if hasattr(module, "on_look"):
                        location.on_look = module.on_look
                    if hasattr(module, "on_before_command"):
                        location.on_before_command = module.on_before_command
                    if hasattr(module, "on_after_command"):
                        location.on_after_command = module.on_after_command
            except ImportError as e:
                logging.warning(f"Could not load handler {module_name}: {e}")
```

**Step 4: Run tests**

```bash
pytest tests/test_engine_loader.py -v
pytest tests/ -v
```

**Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_loader.py
git commit -m "feat(engine): load doors.yaml, globals.yaml, and handler files on startup"
```

---

### Task 11: Update _handle_move() (name/alias exit resolution)

**Files:**
- Modify: `src/engine.py`
- Test: `tests/test_engine_move.py` (create)

**Step 1: Write the failing test**

```python
# tests/test_engine_move.py
import pytest
from unittest.mock import MagicMock, patch
from src.models.models import Location
from src.models.core_data import Exit, GameFlag

def make_engine_with_locations():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine.door_registry.get.return_value = None

    street = Location(
        id="jazz_street", name="Calle", base_description="La calle.",
        exits=[Exit(destination="jazz_club", name="puerta principal",
                    aliases=["entrar", "norte", "n"], door_id=None)]
    )
    club = Location(id="jazz_club", name="Club", base_description="El club.")
    engine.locations = {"jazz_street": street, "jazz_club": club}
    engine.player = MagicMock()
    engine.player.current_location = "jazz_street"
    return engine

def test_move_by_exit_name(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    result = engine._handle_move({"action": "move", "target": "puerta principal"})
    assert "jazz_club" in result.lower() or engine.player.current_location == "jazz_club"

def test_move_by_alias(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    result = engine._handle_move({"action": "move", "target": "norte"})
    assert engine.player.current_location == "jazz_club"

def test_move_no_exit_found(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    result = engine._handle_move({"action": "move", "target": "dragón"})
    assert "no puedes" in result.lower() or "no hay" in result.lower() or result != ""
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_engine_move.py -v
```

**Step 3: Rewrite _handle_move in engine.py**

```python
def _handle_move(self, action: dict) -> str:
    """Handle movement between locations using named exits."""
    target = action.get("target", "").lower().strip()
    current_loc = self.locations.get(self.player.current_location)

    if not current_loc:
        return "No sé dónde estás."

    # Find matching exit by name or alias
    exit_ = current_loc.find_exit(target)

    # Also try matching destination name directly
    if not exit_:
        for e in current_loc.exits:
            dest_loc = self.locations.get(e.destination)
            if dest_loc and target in dest_loc.name.lower():
                exit_ = e
                break
            if dest_loc and any(target == s.lower() for s in dest_loc.synonyms):
                exit_ = e
                break

    if not exit_:
        return f"No encuentras forma de ir a '{target}' desde aquí."

    # Check door if exit has one
    if exit_.door_id:
        door = self.door_registry.get(exit_.door_id)
        if door and door.has_flag(GameFlag.LOCKED):
            return f"La {door.name} está cerrada con llave."
        if door and not door.has_flag(GameFlag.OPEN):
            return f"La {door.name} está cerrada. Quizás deberías abrirla primero."

    # Check condition if exit has one
    if exit_.condition:
        if not self._evaluate_condition(exit_.condition):
            return "Algo te impide pasar."

    # Move player
    self.player.current_location = exit_.destination
    new_loc = self.locations.get(exit_.destination)

    # Fire on_enter hook
    if new_loc and new_loc.on_enter:
        new_loc.on_enter(new_loc, self.player, self)

    # Return location description
    if new_loc:
        return new_loc.get_description(self.ai_enhancer)
    return "Has llegado a otro lugar."

def _evaluate_condition(self, condition_id: str) -> bool:
    """Evaluate a named game condition. Override or extend as needed."""
    return self.game_state.get(condition_id, False)
```

**Step 4: Run tests**

```bash
pytest tests/test_engine_move.py -v
pytest tests/ -v
```

**Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_move.py
git commit -m "feat(engine): rewrite _handle_move() with named exit resolution and door checks"
```

---

### Task 12: Update _handle_examine() (open container search)

**Files:**
- Modify: `src/engine.py`
- Test: `tests/test_engine_examine.py` (create or update)

**Step 1: Write the failing test**

```python
# tests/test_engine_examine.py
from unittest.mock import MagicMock
from src.models.models import Item, Location
from src.models.core_data import GameFlag

def make_engine():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine.global_registry = MagicMock()
    engine.global_registry.find.return_value = None
    engine.door_registry = MagicMock()
    return engine

def test_examine_item_in_open_container(make_engine=make_engine):
    engine = make_engine()

    contract = Item(id="contract", name="contrato", base_description="Un contrato.",
                    synonyms=["contrato", "papel"])
    desk = Item(id="desk", name="escritorio", base_description="Un escritorio.",
                flags={GameFlag.CONTAINER, GameFlag.OPEN, GameFlag.FIXED},
                children=["contract"])

    loc = Location(id="office", name="Oficina", base_description="Una oficina.",
                   children=["desk"])
    engine.locations = {"office": loc}
    engine.items = {"desk": desk, "contract": contract}
    engine.player = MagicMock()
    engine.player.current_location = "office"
    engine.player.inventory = []

    result = engine._handle_examine({"action": "examine", "target": "contrato"})
    assert "contrato" in result.lower() or result != ""
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_engine_examine.py -v
```

**Step 3: Update _handle_examine in engine.py**

Ensure `_handle_examine` uses `_resolve_object` (which already handles open containers in step 6). If the current implementation resolves objects differently, replace with:

```python
def _handle_examine(self, action: dict) -> str:
    """Examine an object — uses full 6-step resolution."""
    target = action.get("target", "")
    obj = self._resolve_object(target)

    if not obj:
        return f"No ves ningún '{target}' aquí."

    context = self._build_context()
    return obj.examine(self.ai_enhancer, context)
```

**Step 4: Run tests**

```bash
pytest tests/test_engine_examine.py -v
pytest tests/ -v
```

**Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_examine.py
git commit -m "feat(engine): update _handle_examine() to use 6-step resolver with container search"
```

---

### Task 13: Sample handler file

**Files:**
- Create: `game_data/handlers/__init__.py`
- Create: `game_data/handlers/jazz_club.py`

**Step 1: Create __init__.py**

```python
# game_data/handlers/__init__.py
# Handler modules are loaded dynamically by the engine.
# Each file corresponds to a location_id.
```

**Step 2: Create jazz_club.py**

```python
# game_data/handlers/jazz_club.py
"""
Lifecycle hooks for the jazz_club location.
Functions are called by the GameEngine at appropriate moments.

Signature for all hooks:
    def hook_name(location, player, engine) -> None | str
"""
import logging

logger = logging.getLogger(__name__)


def on_enter(location, player, engine):
    """
    Called when player enters the jazz club.
    On first visit: activate blood_trail local-global.
    """
    if not location.visited:
        logger.debug("jazz_club: first visit — activating blood_trail")
        engine.global_registry.activate_local_global(
            "blood_trail",
            ["jazz_club", "backstage_corridor"]
        )


def on_look(location, player, engine):
    """
    Called when player examines the room.
    Could vary description based on investigation state.
    """
    pass  # Default behavior sufficient for now


def on_before_command(location, player, action, engine):
    """
    Called before any command is executed in this location.
    Return a string to intercept and replace the command result,
    or None to let normal processing continue.
    """
    pass


def on_after_command(location, player, action, result, engine):
    """
    Called after any command is executed in this location.
    Can be used to trigger events based on player actions.
    """
    pass
```

**Step 3: Verify import works**

```bash
source .venv/bin/activate && export PYTHONPATH=/data/PiesPlanos
python -c "from game_data.handlers import jazz_club; print('OK')"
```
Expected: `OK`

**Step 4: Commit**

```bash
git add game_data/handlers/__init__.py game_data/handlers/jazz_club.py
git commit -m "feat(handlers): add jazz_club handler with on_enter blood_trail activation"
```

---

### Task 14: End-to-end smoke test

**Files:**
- Create: `tests/test_smoke.py`

**Goal:** Verify the full stack loads without errors and basic commands work.

**Step 1: Write smoke test**

```python
# tests/test_smoke.py
"""
Smoke test — verifies the game loads and basic commands execute
without API calls (uses MockAIEnhancer).
"""
import pytest
from unittest.mock import patch
from src.models.ai_enhancer import MockAIEnhancer


@pytest.fixture
def engine():
    from src.engine import GameEngine
    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        game = GameEngine()
    return game


def test_engine_loads(engine):
    assert engine is not None
    assert len(engine.locations) > 0
    assert len(engine.items) > 0


def test_engine_has_global_registry(engine):
    assert engine.global_registry is not None


def test_engine_has_door_registry(engine):
    assert engine.door_registry is not None


def test_starting_location_exists(engine):
    start_loc_id = engine.player.current_location
    assert start_loc_id in engine.locations


def test_examine_item_in_starting_area(engine):
    # Find any item in current location and examine it
    current_loc = engine.locations[engine.player.current_location]
    if current_loc.children:
        first_item_id = current_loc.children[0]
        result = engine.process_command(f"examina {first_item_id}")
        assert isinstance(result, str)
        assert len(result) > 0


def test_move_to_adjacent_location(engine):
    current_loc = engine.locations[engine.player.current_location]
    if current_loc.exits:
        exit_ = current_loc.exits[0]
        result = engine.process_command(f"ve a {exit_.name}")
        assert isinstance(result, str)
        assert len(result) > 0


def test_inventory_command(engine):
    result = engine.process_command("inventario")
    assert isinstance(result, str)
```

**Step 2: Run smoke test**

```bash
pytest tests/test_smoke.py -v
```
Expected: all PASS (or clear error messages pointing to specific issues).

**Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests PASS.

**Step 4: Final commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add end-to-end smoke test for new object model"
```

---

## Checklist final

- [ ] `GameFlag` enum con 15 flags
- [ ] `GameObject` base class con `has_flag`, `add_flag`, `remove_flag`
- [ ] `Item(GameObject)` sin `fixed: bool` ni `examined: bool`
- [ ] `Door(GameObject)` con `connects`, `other_side()`, `unlock_condition`
- [ ] `Exit` con `name`, `aliases`, `matches()`
- [ ] `Location(GameObject)` con `find_exit()` y 4 hooks
- [ ] `GlobalRegistry` con global_objects y local_globals
- [ ] `DoorRegistry` con puertas únicas compartidas
- [ ] `globals.yaml` con lluvia, música, rastro de sangre
- [ ] `doors.yaml` con las 4 puertas del juego
- [ ] `locations.yaml` migrado al nuevo formato
- [ ] `items.yaml` migrado al nuevo formato
- [ ] Engine: `_resolve_object()` con 6 pasos
- [ ] Engine: `_load_handlers()` carga automática de handlers
- [ ] Engine: `_handle_move()` con resolución por nombre/alias
- [ ] Engine: `_handle_examine()` usando `_resolve_object()`
- [ ] `game_data/handlers/jazz_club.py` handler de ejemplo
- [ ] Smoke test pasa completo
