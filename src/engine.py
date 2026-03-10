# %%
# AI-Enhanced Investigation Text Adventure Game
# The game is designed as an investigative text adventure where players explore locations, examine items, talk to NPCs, 
# and solve mysteries using natural language commands enhanced by AI for more immersive interactions.

import src.models.models as models
from src.models.core_data import ClueData, Exit
from src.models.ai_enhancer import ClaudeEnhancer
from src.models.game_context import GameContext
from src.models.global_registry import GlobalRegistry
from src.models.door_registry import DoorRegistry
from src.utils.utils import PersistenceManager
from datetime import datetime
from typing import Dict
import os
import importlib
import logging
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
        self._context = None  # GameContext instance, created when game starts

        # Load GlobalRegistry
        self.global_registry = GlobalRegistry()
        globals_path = "game_data/files/globals.yaml"
        if os.path.exists(globals_path):
            with open(globals_path, 'r', encoding='utf-8') as f:
                globals_data = yaml.safe_load(f)
            if globals_data:
                self.global_registry.load_from_dict(globals_data)

        # Load DoorRegistry
        self.door_registry = DoorRegistry()
        doors_path = "game_data/files/doors.yaml"
        if os.path.exists(doors_path):
            with open(doors_path, 'r', encoding='utf-8') as f:
                doors_data = yaml.safe_load(f)
            if doors_data:
                self.door_registry.load_from_list(doors_data)

        # Auto-load default game content if present
        default_content_path = "game_data"
        if os.path.exists(f"{default_content_path}/files/locations.yaml"):
            self.load_game_content(default_content_path)

    def _get_context(self) -> GameContext:
        """
        Get or create the current game context.

        Returns:
            GameContext: Context object with current game state
        """
        if self._context is None:
            self._context = GameContext(self)
        return self._context

    def _invalidate_context(self):
        """Invalidate cached context when game state changes"""
        if self._context:
            self._context.invalidate()
    def _load_handlers(self) -> None:
        """Load Python handler files from game_data/handlers/ and register hooks on locations."""
        handlers_dir = "game_data/handlers"
        if not os.path.exists(handlers_dir):
            return
        _log = logging.getLogger(__name__)
        for filename in os.listdir(handlers_dir):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
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
                _log.warning(f"Could not load handler {module_name}: {e}")

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
            self.locations = {}
            for loc_data in locations:
                # Rename 'items' → 'children' (items are children of the location)
                loc_data = dict(loc_data)
                if "items" in loc_data:
                    loc_data["children"] = loc_data.pop("items")
                # Convert exit dicts → Exit objects
                raw_exits = loc_data.pop("exits", []) or []
                loc_data["exits"] = [
                    Exit(**ex) if isinstance(ex, dict) else ex
                    for ex in raw_exits
                ]
                # Normalise npcs: YAML may have a bare string instead of a list
                npcs_raw = loc_data.get("npcs")
                if isinstance(npcs_raw, str):
                    loc_data["npcs"] = [npcs_raw]
                elif npcs_raw is None:
                    loc_data["npcs"] = []
                location = models.Location(**loc_data)
                self.locations[location.id] = location

        # Register lifecycle hooks from game_data/handlers/
        self._load_handlers()

    def start_new_game(self, player_name: str, case_id: str, game_data:dict = None):
        """Initialize a new game session"""

        # player_id = f"{player_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        player_id = f"{player_name.lower().replace(' ', '')}"
        self.current_player = models.Player(player_id, player_name)
        self.load_game_content(content_path=game_data.get("content_path"))
                               
        # Initialize first case/investigation
        investigation = models.Investigation(case_id, 
                                             game_data.get("name"), 
                                             game_data.get("description") )
        self.current_player.current_investigation = investigation
        self.current_player.current_location = game_data.get("init_location")
        
        self.game_state = "playing"
    
    def process_command(self, command: str) -> str:
        """Process player command and return response"""
        if not self.current_player or self.game_state != "playing":
            return "Game not active. Please start a new game."

        # Get context object
        context = self._get_context()

        # Use AI to interpret command
        interpretation = self.ai_enhancer.interpret_command(
            command=command,
            context=context.to_dict()
        )

        # Route to appropriate handler first
        action = interpretation.get("action")

        # Skip target resolution for actions that don't need it
        if action not in ["inventory"]:
            # Get target and recipient to resolve string references to actual objects
            target = interpretation.get("target")
            location = context.current_location
            items = context.available_items
            npcs = context.npcs
            exits = context.exits

            if target == location.name:
                interpretation["target"] = location
            elif target in items:
                interpretation["target"] = items[target]
            elif target in exits:
                interpretation["target"] = exits[target]
            elif target in npcs:
                interpretation["target"] = npcs[target]

            recipient = interpretation.get("recipient")
            if recipient in items:
                interpretation["recipient"] = items[recipient]
            elif recipient in exits:
                interpretation["recipient"] = exits[recipient]
            elif recipient in npcs:
                interpretation["recipient"] = npcs[recipient]

        if action == "examine":
            return self._handle_examine(interpretation)
        if action in ["say", "ask"]:
            return self._handle_say(interpretation)
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
        context = self._get_context()
        if interpretation.get("target"):
            return self.ai_enhancer.enhance_examine(interpretation["target"], context=context.to_dict())
        return "You look around carefully, noting the details..."
    
    def _handle_talk(self, interpretation: Dict) -> str:
        """Handle conversation commands"""
        return "The conversation reveals interesting information..."
    
    def _handle_say(self, interpretation: Dict) -> str:
        """Handle conversation commands"""
        return "The conversation reveals interesting information..."
    
    def _handle_move(self, action: dict) -> str:
        """
        Handle movement between locations using named exits.
        Resolves by exit name, aliases, or destination name/synonyms.
        """
        from src.models.core_data import GameFlag
        target = action.get("target", "").lower().strip()
        current_loc = self.locations.get(self.current_player.current_location)

        if not current_loc:
            return "No sé dónde estás."

        # Find matching exit by name or alias
        exit_ = current_loc.find_exit(target)

        # Also try matching destination name or synonyms
        if not exit_:
            for e in current_loc.exits:
                dest_loc = self.locations.get(e.destination)
                if dest_loc:
                    if target == dest_loc.name.lower():
                        exit_ = e
                        break
                    if any(target == s.lower() for s in dest_loc.synonyms):
                        exit_ = e
                        break

        if not exit_:
            return f"No encuentras forma de ir a '{target}' desde aquí."

        # Check door if exit has one
        if exit_.door_id and hasattr(self, 'door_registry'):
            door = self.door_registry.get(exit_.door_id)
            if door and door.has_flag(GameFlag.LOCKED):
                return f"La {door.name} está cerrada con llave."
            if door and not door.has_flag(GameFlag.OPEN):
                return f"La {door.name} está cerrada. Quizás deberías abrirla primero."

        # Check condition if exit has one (no door)
        if exit_.condition:
            if not self.game_state.get(exit_.condition, False):
                return "Algo te impide pasar."

        # Move player
        self.current_player.current_location = exit_.destination
        new_loc = self.locations.get(exit_.destination)

        # Invalidate context after movement as location changes
        self._invalidate_context()

        # Fire on_enter hook if present
        if new_loc and new_loc.on_enter:
            new_loc.on_enter(new_loc, self.current_player, self)

        # Return location description
        if new_loc:
            context = self._get_context().to_dict() if hasattr(self, '_get_context') else {}
            return new_loc.get_description(self.ai_enhancer, context)
        return "Has llegado a otro lugar."
    
    def _handle_inventory(self) -> str:
        """Handle inventory commands"""
        if not self.current_player.inventory:
            return "Your inventory is empty."
        
        items = [item.name for item in self.current_player.inventory]
        return f"You are carrying: {', '.join(items)}"
    
    def _resolve_object(self, query: str):
        """
        Resolve a string query to a game object using 6-step priority search.

        Search order:
        1. Player inventory
        2. Current location children (items)
        3. Current location NPCs
        4. GlobalRegistry (global_objects + visible local_globals)
        5. (covered by GlobalRegistry)
        6. Open containers in current location

        Args:
            query: The string to match against object names/synonyms.

        Returns:
            The matching game object, or None if not found.
        """
        from src.models.core_data import GameFlag
        q = query.lower().strip()

        # Step 1: Player inventory
        for item in getattr(self.current_player, 'inventory', []):
            if self._matches_object(item, q):
                return item

        # Steps 2-5: Location-based search
        current_loc = self.locations.get(getattr(self.current_player, 'current_location', None))
        if current_loc:
            # Step 2: Location children
            for child_id in current_loc.children:
                obj = self.items.get(child_id)
                if obj and self._matches_object(obj, q):
                    return obj

            # Step 3: NPCs in location
            for npc_id in current_loc.npcs:
                npc = self.npcs.get(npc_id)
                if npc and self._matches_object(npc, q):
                    return npc

            # Step 4 & 5: GlobalRegistry (handles global_objects + local_globals)
            if hasattr(self, 'global_registry') and self.global_registry:
                global_obj = self.global_registry.find(q, self.current_player.current_location)
                if global_obj:
                    return global_obj

            # Step 6: Open containers in location
            for child_id in current_loc.children:
                container = self.items.get(child_id)
                if (container and
                        container.has_flag(GameFlag.CONTAINER) and
                        container.has_flag(GameFlag.OPEN)):
                    for nested_id in container.children:
                        nested = self.items.get(nested_id)
                        if nested and self._matches_object(nested, q):
                            return nested

        return None

    def _matches_object(self, obj, query: str) -> bool:
        """
        Check if object name or synonyms match query (case-insensitive).

        Args:
            obj: Any game object with name and synonyms attributes.
            query: Lowercased query string to match against.

        Returns:
            True if the query matches the object's name or any synonym.
        """
        if query == obj.name.lower():
            return True
        return query in [s.lower() for s in obj.synonyms]

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

# %%
