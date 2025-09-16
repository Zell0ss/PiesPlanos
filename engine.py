# %%
# AI-Enhanced Investigation Text Adventure Game
# The game is designed as an investigative text adventure where players explore locations, examine items, talk to NPCs, 
# and solve mysteries using natural language commands enhanced by AI for more immersive interactions.

import models.models as models
from  models.core_data import ClueData
from models.ai_enhancer import AIEnhancer, MockAIEnhancer, ClaudeEnhancer
from utils import PersistenceManager
from datetime import datetime
from typing import Dict
import os
from dotenv import load_dotenv

import yaml
load_dotenv()

# %%
class GameEngine:
    """
    Main game engine coordinating all systems
    
    Attributes:
        ai_enhancer (AIEnhancer): AI-enhanced natural language processing
        persistence (PersistenceManager): Persistence manager for saving and loading game data
        current_player (Player): Currently active player
        locations (Dict[str, Location]): Dictionary of locations in the game
        clues (Dict[str, ClueData]): Dictionary of clues in the game
        game_state (str): Current game state
    """
    
    def __init__(self):
        self.ai_enhancer = ClaudeEnhancer()
        self.persistence = PersistenceManager()
        self.current_player = None
        self.locations = {}
        self.clues = {}
        self.items = {}
        self.npcs = {}
        self.game_state = "menu"  # menu, playing, paused, ended
        
    def load_game_content(self, content_path: str):
        """Load game content from YAML files"""
        # Implementation would load locations, NPCs, items, etc. from YAML
        with open(f"{content_path}/files/clues.yaml", "r") as file:
            clues = yaml.safe_load(file)
            self.clues = {clue["id"]: ClueData(**clue) for clue in clues}
        
        with open(f"{content_path}/files/items.yaml", "r") as file:
            items = yaml.safe_load(file)
            self.items = {item["id"]: models.Item(**item) for item in items}
        
        with open(f"{content_path}/files/npcs.yaml", "r") as file:
            npcs = yaml.safe_load(file)
            self.npcs = {npc["id"]: models.NPC(**npc) for npc in npcs}
        
        with open(f"{content_path}/files/locations.yaml", "r") as file:
            locations = yaml.safe_load(file)
            self.locations = {location["id"]: models.Location(**location) for location in locations}
        
    
    def start_new_game(self, player_name: str, case_id: str, game_data:dict = None):
        """Initialize a new game session"""

        player_id = f"{player_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_player = models.Player(player_id, player_name)
        self.load_game_content(content_path=game_data.get("content_path"))
                               
        # Initialize first case/investigation
        investigation = models.Investigation(case_id, 
                                             game_data.get("name"), 
                                             game_data.get("description") )
        self.current_player.current_investigation = investigation
        
        self.game_state = "playing"
    
    def process_command(self, command: str) -> str:
        """Process player command and return response"""
        if not self.current_player or self.game_state != "playing":
            return "Game not active. Please start a new game."
        
        # Use AI to interpret command
        interpretation = self.ai_enhancer.interpret_command(command=command, context={
            "current_location": self.current_player.current_location,
            "inventory": [item.name for item in self.current_player.inventory],
            "investigation_progress": self.current_player.current_investigation.progress_percentage
        })
        
        # Route to appropriate handler
        action = interpretation.get("action", "unknown")
        
        if action == "examine":
            return self._handle_examine(interpretation)
        elif action == "talk":
            return self._handle_talk(interpretation)
        elif action == "move":
            return self._handle_move(interpretation)
        elif action == "inventory":
            return self._handle_inventory()
        else:
            return f"I don't understand '{command}'. Try examining something or talking to someone."
    
    def _handle_examine(self, interpretation: Dict) -> str:
        """Handle examine commands"""
        return "You look around carefully, noting the details..."
    
    def _handle_talk(self, interpretation: Dict) -> str:
        """Handle conversation commands"""
        return "The conversation reveals interesting information..."
    
    def _handle_move(self, interpretation: Dict) -> str:
        """Handle movement commands"""
        return "You move to a new location..."
    
    def _handle_inventory(self) -> str:
        """Handle inventory commands"""
        if not self.current_player.inventory:
            return "Your inventory is empty."
        
        items = [item.name for item in self.current_player.inventory]
        return f"You are carrying: {', '.join(items)}"
    
    def save_game(self) -> bool:
        """Save current game state"""
        if self.current_player:
            return self.persistence.save_player(self.current_player)
        return False
    
    def load_game(self, player_id: str) -> bool:
        """Load game state from database"""
        self.current_player = self.persistence.load_player(player_id)
        return self.current_player is not None



# # %%
# engine = GameEngine()
# engine.load_game_content("/data/PiesPlanos/game_data")

# # %%
# engine.locations

# # %%
# from  models.core_data import ClueData
# with open("/data/PiesPlanos/game_data/files/clues.yaml", "r") as file:
#     clues = yaml.safe_load(file)
#     clues_dict = {clue["id"]: ClueData(**clue) for clue in clues}

# # %%
# from  models.models import Item
# with open("/data/PiesPlanos/game_data/files/items.yaml", "r") as file:
#     items = yaml.safe_load(file)
#     items_dict = {item["id"]: Item(**item) for item in items}

# # %%
# with open("/data/PiesPlanos/game_data/files/locations.yaml", "r") as file:
#     locations = yaml.safe_load(file)
#     locations = {location["id"]: models.Location(**location) for location in locations}
# # %%
