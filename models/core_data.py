
from dataclasses import dataclass
from typing import List

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
    source: str  # Where/how it was discovered
    revealed: bool = False
    connections: List[str] = None  # IDs of related clues
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = []

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