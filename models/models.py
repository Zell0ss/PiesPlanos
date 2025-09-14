# AI-Enhanced Investigation Text Adventure Game
# Core Classes and Architecture
# %%
from datetime import datetime
from typing import Dict, List, Optional, Any
from models.core_data import ClueData, ConversationEntry
from models.ai_enhancer import AIEnhancer

# ==============================================================================
# Core Game Classes
# ==============================================================================
# %%
class Item:
    """
    Represents an item in the game world.
    An item can basically be examided and used. 
    It can hold a clue or clues and get it only in certain conditions
    """
    
    def __init__(self, 
                 item_id: str, 
                 name: str, 
                 description: str, 
                 properties: Dict[str, Any] = None, 
                 clues: List[ClueData] = None, 
                 fixed: bool = False, 
                 reason_fixed: str = None):
        self.id = item_id
        self.name = name
        self.base_description = description
        self.properties = properties or {}
        self.clues = clues or []
        self.examined = False
        self.fixed = fixed # most items can be moved or get to the inventory
        self.reason_fixed = reason_fixed    # if fixed, why?

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
        

# %%
class NPC:
    """Represents a non-player character with AI-enhanced interactions.
    It can hold a clue or clues and get it only in certain conditions"""
    
    def __init__(self, npc_id: str, name: str, description: str, 
                 personality: Dict[str, Any], clues: List[ClueData] = None, conversation_prompt: str = None):
        self.id = npc_id
        self.name = name
        self.base_description = description
        self.personality = personality
        self.clues = clues or []
        self.conversation_history = []
        self.current_mood = "neutral"  # neutral, suspicious, friendly, angry, scared
        self.relationship_level = 0  # -10 to +10
        self.conversation_prompt = conversation_prompt

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
        pass
    
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
class Location:
    """Represents a location in the game world"""
    
    def __init__(self, location_id: str, name: str, description: str, 
                 connections: Dict[str, str] = None, illustration_path: str = None):
        self.id = location_id
        self.name = name
        self.base_description = description
        self.connections = connections or {}  # direction: location_id
        self.items = []
        self.npcs = []
        self.illustration_path = illustration_path
        self.visited = False
        self.investigation_complete = False
    
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
class Investigation:
    """Manages the overall investigation progress and clue connections"""
    
    def __init__(self, case_id: str, title: str, description: str):
        self.case_id = case_id
        self.title = title
        self.description = description
        self.discovered_clues = {}  # clue_id: ClueData
        self.clue_connections = []  # List of connections between clues
        self.progress_percentage = 0
        self.key_breakthroughs = []
        
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
class Player:
    """Represents the player character and their progress"""
    
    def __init__(self, player_id: str, name: str):
        self.id = player_id
        self.name = name
        self.current_location = None
        self.inventory = []
        self.investigation_skills = {
            "observation": 5,
            "interrogation": 5,
            "deduction": 5,
            "intuition": 5
        }
        self.current_investigation = None
        self.session_start_time = datetime.now().isoformat()
        self.total_play_time = 0
        
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
