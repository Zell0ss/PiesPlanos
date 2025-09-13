
from dataclasses import dataclass
from typing import List

# ==============================================================================
# Core Data Classes: the clues and the conversation entries
# We need them in AI enhancer and in the Game classes
# ==============================================================================

@dataclass
class ClueData:
    """Represents a clue that can be discovered during investigation"""
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
    """Single conversation exchange with NPC"""
    timestamp: str
    player_input: str
    npc_response: str
    mood_state: str
    clues_revealed: List[str] = None
    
    def __post_init__(self):
        if self.clues_revealed is None:
            self.clues_revealed = []