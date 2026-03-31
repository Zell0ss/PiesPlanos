from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional


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
    children: list[str] = field(default_factory=list)  # list of child IDs
    parent_id: str | None = None

    def has_flag(self, flag: GameFlag) -> bool:
        return flag in self.flags

    def add_flag(self, flag: GameFlag) -> None:
        self.flags.add(flag)

    def remove_flag(self, flag: GameFlag) -> None:
        self.flags.discard(flag)

    def examine(self, ai_enhancer=None, context: dict = None) -> str:
        """Get enhanced description. Overridden by Item to also set EXAMINED flag."""
        if context and ai_enhancer:
            return ai_enhancer.enhance_description(self.base_description, context)
        return self.base_description


@dataclass
class Exit:
    """
    Connection from a location to another.
    Navigation by name/alias, not compass direction (though aliases can include compass).
    """

    destination: str
    name: str
    aliases: list[str] = field(default_factory=list)
    door_id: str | None = None
    condition: str | None = None

    def matches(self, query: str) -> bool:
        """Return True if query matches this exit's name or any alias."""
        q = query.lower().strip()
        if q == self.name.lower():
            return True
        return q in [a.lower() for a in self.aliases]


@dataclass
class ClueData:
    """
    Dataclass representing discoverable investigation clues
        - Tracks source of discovery and revelation status
        - Maintains connections to related clues for building case theory
    """

    id: str
    title: str
    description: str
    revealed: bool = False
    connections: List[str] = None  # IDs of related clues

    def __post_init__(self):
        if self.connections is None:
            self.connections = []


@dataclass
class Interaction:
    """Defines what happens when a player uses one object on/with another.

    YAML uses 'with' (Python keyword); load via Interaction.from_dict().

    conditions items:
        has_item: item_id        — player must carry this item
        has_clue: clue_id        — player must have discovered this clue
        game_flag: flag_name     — engine flag must be True

    effects items (on_success / on_failure):
        set_flag: flag_name      — activate an engine flag
        reveal_clue: clue_id     — add clue to discovered_clues
        unlock_exit: door_id     — remove LOCKED flag from a door
        message: "text" | null   — narrative message (null = auto-generate)
    """

    action: str
    with_item: Optional[str] = None
    conditions: List[dict] = field(default_factory=list)
    on_success: List[dict] = field(default_factory=list)
    on_failure: List[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Interaction":
        d = dict(d)
        d["with_item"] = d.pop("with", None)
        return cls(**d)


@dataclass
class ConversationEntry:
    """
    Single conversation exchange with NPC
        - Records timestamps, dialogue, NPC mood states, and any clues revealed
        - Used to build conversation history for context in AI responses
    """

    timestamp: str
    player_input: str
    npc_response: str
    mood_state: str
    clues_revealed: List[str] = None

    def __post_init__(self):
        if self.clues_revealed is None:
            self.clues_revealed = []
