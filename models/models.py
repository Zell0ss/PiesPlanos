# AI-Enhanced Investigation Text Adventure Game
# Core Classes and Architecture
# %%
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from models.core_data import ClueData, ConversationEntry, Connector
from models.ai_enhancer import AIEnhancer

# ==============================================================================
# Core Game Classes
# ==============================================================================
# %%
@dataclass
class Item:
    """
    Represents an item in the game world.
        - Represents interactive objects in the game world
        - Can be examined (with AI-enhanced descriptions) and used with targets
        - Holds clues that can be discovered under certain conditions
        - Has properties like being "fixed" (immovable/in-gathereable) with reasons to avoid "carry thorin" situation
        - Tracks examination state
    """
    id: str
    name: str
    base_description: str
    properties: Dict[str, Any] = field(default_factory=dict)
    clues: List[ClueData] = field(default_factory=list)
    examined: bool = False
    fixed: bool = False  # most items can be moved or get to the inventory
    reason_fixed: Optional[str] = None  # if fixed, why?

    def examine(self, ai_enhancer: AIEnhancer, context: Dict[str, Any] = None) -> str:
        """Get enhanced examination description spiced with any extra context we want to add"""
        self.examined = True
        if context:
            return ai_enhancer.enhance_description(self.base_description, context)
        return self.base_description
    
    def use(self, ai_enhancer: AIEnhancer, action:str, target: str) -> str:
        """
        Items have a basic use, directly commented by AI. but others would have a key usage more specific
        ie: shot a gun, use a key to open something, etc
        """
        result = "nothing special happens"
        return ai_enhancer.enhance_usage(object = self.base_description, action=action, target=target, result=result)
    
    def get_available_clues(self) -> List[ClueData]:
        """Get clues this NPC can potentially reveal"""
        return [clue for clue in self.clues if not clue.revealed]
    
    def reveal_clue(self, clue_id: str) -> Optional[ClueData]:
        """Mark a clue as revealed and return it"""
        for clue in self.clues:
            if clue.id == clue_id:
                clue.revealed = True
                return clue
        return None    

# %%
@dataclass
class NPC:
    """
    Represents a non-player character in the game world
  - Non-player characters with AI-enhanced conversational abilities
  - Has personality traits, mood states, and relationship levels with player
  - Maintains conversation history and can reveal clues through dialogue/interactions
  - Uses AIEnhancer to generate contextual responses based on personality and history
  - Manages conversation memory with summarization for long interactions
"""
    id: str
    name: str
    base_description: str
    personality: Dict[str, Any]
    clues: List[ClueData] = field(default_factory=list)
    conversation_history: List = field(default_factory=list)
    current_mood: str = "neutral"  # neutral, suspicious, friendly, angry, scared
    relationship_level: int = 0  # -10 to +10
    conversation_prompt: Optional[str] = None

    def answer_conversation(self, ai_enhancer: AIEnhancer, player_input: str, context: Dict[str, Any] = None) -> str:
        """Answer player input with AI-enhanced response"""
        npc_data = {
            "name": self.name,
            "description": self.base_description,
            "personality": self.personality,
            "current_mood": self.current_mood,
            "relationship_level": self.relationship_level,
            "conversation_prompt":self.conversation_prompt
            }
        response = ai_enhancer.generate_npc_response(npc_data, 
                                                    self.conversation_history, 
                                                    player_input, 
                                                    context.get("must_include"))
        self.add_conversation(player_input, response)
        return response
        
    def add_conversation(self, player_input: str, response: str, clues_revealed: List[str] = None):
        """Add conversation entry to history"""
        entry = ConversationEntry(
            timestamp=datetime.now().isoformat(),
            player_input=player_input,
            npc_response=response,
            mood_state=self.current_mood,
            clues_revealed=clues_revealed or []
        )
        self.conversation_history.append(entry)
        
        # Manage conversation history length
        if len(self.conversation_history) > 50:
            # Keep recent conversations, summarize older ones
            self._summarize_old_conversations()
    
    def _summarize_old_conversations(self):
        """Summarize older conversations to manage memory"""
        # Implementation would use AI to summarize and compress history
        self.conversation_history = AIEnhancer.summarize_conversation(self.conversation_history)
    
    def get_available_clues(self) -> List[ClueData]:
        """Get clues this NPC can potentially reveal"""
        return [clue for clue in self.clues if not clue.revealed]
    
    def reveal_clue(self, clue_id: str) -> Optional[ClueData]:
        """Mark a clue as revealed and return it"""
        for clue in self.clues:
            if clue.id == clue_id:
                clue.revealed = True
                return clue
        return None
    
# %%

@dataclass
class Location:
    """
  Represents game world locations with
  - connections between them
    - destination: another location_id
    - item: door/exit item_id
  - Contains items and NPCs, tracks visit status and investigation completion
  - Supports AI-enhanced descriptions with contextual information
  - Has directional connections to other locations
  - illustration path
    """
    id: str
    name: str
    base_description: str
    connectors: List[Connector] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    npcs: List = field(default_factory=list)
    illustration_path: Optional[str] = None
    visited: bool = False
    investigation_complete: bool = False
    
    def add_exit(self,connector: Connector):
        self.connectors.append(connector)

    def remove_exit(self,connector: Connector):
        self.connectors.remove(connector)

    def add_item(self, item: Item):
        """Add item to location"""
        self.items.append(item)
    
    def remove_item(self, item_id: str) -> Optional[Item]:
        """Remove and return item from location"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                return self.items.pop(i)
        return None
    
    def add_npc(self, npc: NPC):
        """Add NPC to location"""
        self.npcs.append(npc)
    
    def get_description(self, ai_enhancer: AIEnhancer, context: Dict[str, Any] = None) -> str:
        """Get enhanced location description"""
        if context and ai_enhancer:
            return ai_enhancer.enhance_description(self.base_description, context)
        return self.base_description

# %%
@dataclass
class Investigation:
    """
    Manages the overall investigation progress and clue connections
        - Tracks discovered clues and connections between them
        - Calculates progress percentage based on clues found and relationships discovered
        - Records key breakthroughs and maintains case metadata
        - Provides progress summaries for the player
    """
    case_id: str
    title: str
    description: str
    discovered_clues: Dict[str, ClueData] = field(default_factory=dict)  # clue_id: ClueData
    clue_connections: List = field(default_factory=list)  # List of connections between clues
    progress_percentage: int = 0
    key_breakthroughs: List = field(default_factory=list)
        
    def add_clue(self, clue: ClueData):
        """Add a discovered clue to the investigation"""
        self.discovered_clues[clue.id] = clue
        self._update_progress()
    
    def connect_clues(self, clue_id1: str, clue_id2: str, connection_type: str = "related"):
        """Create connection between two clues"""
        connection = {
            "clue1": clue_id1,
            "clue2": clue_id2,
            "type": connection_type,
            "discovered_at": datetime.now().isoformat()
        }
        self.clue_connections.append(connection)
        self._update_progress()
    
    def _update_progress(self):
        """Update investigation progress based on clues and connections"""
        # Simple progress calculation - can be made more sophisticated
        clue_count = len(self.discovered_clues)
        connection_count = len(self.clue_connections)
        self.progress_percentage = min(100, (clue_count * 10) + (connection_count * 5))
    
    def get_progress_summary(self) -> str:
        """Get summary of investigation progress"""
        return f"Progress: {self.progress_percentage}% - {len(self.discovered_clues)} clues discovered"

# %%
@dataclass
class Player:
    """
    Represents the player character and their progress
        - Has inventory
        - Has investigation skills. Different investigations (games) will have different skillset to choose from
        - Tracks current location, active investigation, and session data
        - Manages inventory items with add/remove/check functionality
        - Records playtime and session information
  """
    id: str
    name: str
    current_location: Optional[str] = None
    inventory: List = field(default_factory=list)
    investigation_skills: Dict[str, int] = field(default_factory=lambda: {
        "observation": 5,
        "interrogation": 5,
        "chemistry": 0,
        "photograpy": 0,
        "locksmith": 0,
        "guns": 0,
        "blades": 0,
        "streetwise": 0,
        "stealth": 0,
        "survival": 0
    })
    current_investigation: Optional[Investigation] = None
    session_start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    total_play_time: int = 0
        
    def add_item(self, item: Item):
        """Add item to player inventory"""
        self.inventory.append(item)
    
    def remove_item(self, item_id: str) -> Optional[Item]:
        """Remove item from inventory"""
        for i, item in enumerate(self.inventory):
            if item.id == item_id:
                return self.inventory.pop(i)
        return None
    
    def has_item(self, item_id: str) -> bool:
        """Check if player has specific item"""
        return any(item.id == item_id for item in self.inventory)
