# %%
# AI-Enhanced Investigation Text Adventure Game
# The game is designed as an investigative text adventure where players explore locations, examine items, talk to NPCs,
# and solve mysteries using natural language commands enhanced by AI for more immersive interactions.

import dataclasses
import src.models.models as models
from src.models.core_data import ClueData, ConversationEntry, Exit, GameFlag
from src.models.ai_enhancer import ClaudeEnhancer
from src.models.game_context import GameContext
from src.models.global_registry import GlobalRegistry
from src.models.door_registry import DoorRegistry
from src.utils.utils import PersistenceManager
from datetime import datetime
from typing import Dict
import os
import importlib
from src.utils.logging_config import get_logger
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
        self.game_flags: dict = {}  # runtime condition flags for conditioned exits
        self._context = None  # GameContext instance, created when game starts

        # Load GlobalRegistry
        self.global_registry = GlobalRegistry()
        globals_path = "game_data/files/globals.yaml"
        if os.path.exists(globals_path):
            with open(globals_path, "r", encoding="utf-8") as f:
                globals_data = yaml.safe_load(f)
            if globals_data:
                self.global_registry.load_from_dict(globals_data)

        # Load DoorRegistry
        self.door_registry = DoorRegistry()
        doors_path = "game_data/files/doors.yaml"
        if os.path.exists(doors_path):
            with open(doors_path, "r", encoding="utf-8") as f:
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
        _log = get_logger(__name__)
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
            for item in items:
                if "flags" in item:
                    item["flags"] = {
                        GameFlag[f] for f in item["flags"] if f in GameFlag.__members__
                    }
                if "interactions" in item:
                    from src.models.core_data import Interaction
                    item["interactions"] = [
                        Interaction.from_dict(i) for i in (item["interactions"] or [])
                    ]
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
                    Exit(**ex) if isinstance(ex, dict) else ex for ex in raw_exits
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

    def start_new_game(self, player_name: str, case_id: str, game_data: dict = None):
        """Initialize a new game session"""

        # player_id = f"{player_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        player_id = f"{player_name.lower().replace(' ', '')}"
        self.current_player = models.Player(player_id, player_name)
        self.load_game_content(content_path=game_data.get("content_path"))

        # Initialize first case/investigation
        investigation = models.Investigation(
            case_id, game_data.get("name"), game_data.get("description")
        )
        self.current_player.current_investigation = investigation
        self.current_player.current_location = game_data.get("init_location")

        self.game_state = "playing"

    def extract_delta(self) -> dict:
        """Compute current game state as a JSON-serializable delta.

        Returns only what differs from the YAML baseline, not the full object graph.
        """
        player = self.current_player
        investigation = player.current_investigation

        # Visited location ids
        visited = [loc_id for loc_id, loc in self.locations.items() if loc.visited]

        # Per-object flag snapshots (all objects, not just diffs — cheap and safe)
        object_flags: dict = {}
        for obj_id, obj in self.items.items():
            if obj.flags:
                object_flags[obj_id] = [f.name for f in obj.flags]
        # Also capture door flags
        for door_id, door in getattr(self.door_registry, "_doors", {}).items():
            if door.flags:
                object_flags[door_id] = [f.name for f in door.flags]

        # NPC conversation history
        npc_conversations: dict = {}
        for npc_id, npc in self.npcs.items():
            if npc.conversation_history:
                npc_conversations[npc_id] = [
                    dataclasses.asdict(entry) for entry in npc.conversation_history
                ]

        return {
            "current_location": player.current_location,
            "inventory": [item.id for item in player.inventory],
            "visited": visited,
            "object_flags": object_flags,
            "engine_flags": dict(self.game_flags),
            "discovered_clues": list(investigation.discovered_clues.keys()),
            "clue_connections": list(investigation.clue_connections),
            "npc_conversations": npc_conversations,
        }

    def apply_delta(self, delta: dict) -> None:
        """Overlay a saved delta onto the already-loaded YAML baseline.

        Must be called AFTER start_new_game() — requires self.items, self.locations,
        self.npcs, self.clues, and self.current_player to already be initialized.
        """
        if self.current_player is None:
            raise RuntimeError("apply_delta() must be called after start_new_game()")

        player = self.current_player
        investigation = player.current_investigation

        # Location
        player.current_location = delta.get("current_location", player.current_location)

        # Inventory: reconstruct Item objects from ids
        inv_ids = delta.get("inventory", [])
        player.inventory = [
            self.items[item_id] for item_id in inv_ids if item_id in self.items
        ]

        # Visited flags
        for loc_id in delta.get("visited", []):
            if loc_id in self.locations:
                self.locations[loc_id].visited = True

        # Object flags (items + doors)
        all_objects = dict(self.items)
        for door_id, door in getattr(self.door_registry, "_doors", {}).items():
            all_objects[door_id] = door
        for obj_id, flag_names in delta.get("object_flags", {}).items():
            if obj_id in all_objects:
                flags = set()
                for name in flag_names:
                    try:
                        flags.add(GameFlag[name])
                    except KeyError:
                        pass  # skip stale/renamed flags from old delta
                all_objects[obj_id].flags = flags

        # Engine-level condition flags (REPLACE, not merge)
        self.game_flags = dict(delta.get("engine_flags", {}))

        # Discovered clues: reconstruct {id: ClueData} from clue registry
        for clue_id in delta.get("discovered_clues", []):
            if clue_id in self.clues:
                investigation.discovered_clues[clue_id] = self.clues[clue_id]

        # Clue connections (plain dicts, restore verbatim)
        investigation.clue_connections = list(delta.get("clue_connections") or [])
        investigation._update_progress()

        # NPC conversation history
        for npc_id, history_rows in delta.get("npc_conversations", {}).items():
            if npc_id in self.npcs:
                self.npcs[npc_id].conversation_history = [
                    ConversationEntry(**row) for row in history_rows
                ]

    def process_command(self, command: str) -> str:
        """Process player command and return response"""
        if not self.current_player or self.game_state != "playing":
            return "Game not active. Please start a new game."

        # Get context object
        context = self._get_context()

        # Use AI to interpret command
        interpretation = self.ai_enhancer.interpret_command(
            command=command, context=context.to_dict()
        )

        # Route to appropriate handler
        action = interpretation.get("action")

        if action == "look":
            return self._handle_look()
        if action == "examine":
            return self._handle_examine(interpretation)
        if action in ["say", "ask"]:
            return self._handle_say(interpretation)
        elif action == "talk":
            return self._handle_talk(interpretation)
        elif action in ["move", "go"]:
            return self._handle_move(interpretation)
        elif action == "inventory":
            return self._handle_inventory()
        elif action == "use":
            return self._handle_use(interpretation)
        elif action in ["take", "pick"]:
            return self._handle_take(interpretation)
        elif action == "drop":
            return self._handle_drop(interpretation)
        else:
            return "No entiendo ese comando. Prueba con mirar, examinar, hablar con alguien, o ir a algún sitio."

    def _room_footer(self, location) -> str:
        """Build the deterministic room footer: visible items, NPCs, exits.

        This section is NEVER AI-enhanced — it is authoritative game state.
        """
        parts = []

        # Visible items: children that are not SCENERY or INVISIBLE
        visible = [
            self.items[child_id].name
            for child_id in location.children
            if child_id in self.items
            and not self.items[child_id].has_flag(GameFlag.SCENERY)
            and not self.items[child_id].has_flag(GameFlag.INVISIBLE)
        ]
        if visible:
            parts.append("Puedes ver: " + ", ".join(visible) + ".")

        # NPCs present in this location
        present_npcs = [
            self.npcs[npc_id].name for npc_id in location.npcs if npc_id in self.npcs
        ]
        if present_npcs:
            verb = "está" if len(present_npcs) == 1 else "están"
            parts.append(", ".join(present_npcs) + f" {verb} aquí.")

        # Exits: destination name + first alias as command hint
        exit_strs = []
        for exit_ in location.exits:
            dest_loc = self.locations.get(exit_.destination)
            dest_name = dest_loc.name if dest_loc else exit_.destination
            hint = exit_.aliases[0] if exit_.aliases else exit_.name
            exit_strs.append(f"{dest_name} [{hint}]")
        if exit_strs:
            parts.append("Salidas: " + " · ".join(exit_strs))

        return "\n".join(parts)

    def _handle_look(self) -> str:
        """Describe the current location to the player."""
        current_loc = self.locations.get(self.current_player.current_location)
        if not current_loc:
            return "No sé dónde estás."

        # Fire on_look hook if present
        if current_loc.on_look:
            current_loc.on_look(current_loc, self.current_player, self)

        context = self._get_context().to_dict() if hasattr(self, "_get_context") else {}
        prose = current_loc.get_description(self.ai_enhancer, context)
        footer = self._room_footer(current_loc)
        return f"{prose}\n\n{footer}" if footer else prose

    def _handle_examine(self, action: dict) -> str:
        """
        Examine an object using the 6-step resolver.
        Sets EXAMINED flag and returns AI-enhanced description.
        """
        target = action.get("target", "")
        # process_command may have already resolved target to an object
        if isinstance(target, str):
            target_str = target.strip()
            obj = self._resolve_object(target_str)
        else:
            obj = target
            target_str = getattr(target, "name", str(target))

        if not obj:
            # Fallback: if target matches the current location, treat as look
            current_loc = self.locations.get(self.current_player.current_location)
            if current_loc and target_str.lower() in (
                current_loc.name.lower(),
                "room",
                "around",
                "habitación",
                "sala",
                "lugar",
            ):
                return self._handle_look()
            return f"No ves ningún '{target_str}' aquí."

        context = self._get_context().to_dict() if hasattr(self, "_get_context") else {}
        return obj.examine(self.ai_enhancer, context)

    def _resolve_npc_in_location(self, target: str):
        """Return (npc, None) or (None, error_message) for an NPC in the current room."""
        current_loc = self.locations.get(self.current_player.current_location)
        if not current_loc:
            return None, "No sé dónde estás."
        target_lower = target.lower().strip()
        for npc_id in getattr(current_loc, "npcs", []):
            npc = self.npcs.get(npc_id)
            if npc and (
                target_lower == npc.name.lower()
                or any(target_lower == s.lower() for s in npc.synonyms)
            ):
                return npc, None
        return None, f"{target} no está en esta habitación."

    def _handle_talk(self, action: dict) -> str:
        """Initiate conversation with an NPC in the current location."""
        npc, error = self._resolve_npc_in_location(action.get("target", ""))
        if error:
            return error
        player_input = action.get("message") or f"Hola, {npc.name}."
        context = self._get_context().to_dict() if hasattr(self, "_get_context") else {}
        context["must_include"] = None
        return npc.answer_conversation(self.ai_enhancer, player_input, context)

    def _handle_say(self, action: dict) -> str:
        """Say something specific to an NPC in the current location."""
        npc, error = self._resolve_npc_in_location(action.get("target", ""))
        if error:
            return error
        player_input = action.get("message", "").strip()
        if not player_input:
            return "¿Qué quieres decirle?"
        context = self._get_context().to_dict() if hasattr(self, "_get_context") else {}
        context["must_include"] = None
        return npc.answer_conversation(self.ai_enhancer, player_input, context)

    def _handle_move(self, action: dict) -> str:
        """
        Handle movement between locations using named exits.
        Resolves by exit name, aliases, or destination name/synonyms.
        """
        from src.models.core_data import GameFlag

        target = self._strip_articles(action.get("target", "").lower().strip())
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
        if exit_.door_id and hasattr(self, "door_registry"):
            door = self.door_registry.get(exit_.door_id)
            if door and door.has_flag(GameFlag.LOCKED):
                return f"La {door.name} está cerrada con llave."
            if door and not door.has_flag(GameFlag.OPEN):
                return f"La {door.name} está cerrada. Quizás deberías abrirla primero."

        # Check condition if exit has one (no door)
        if exit_.condition:
            if not self.game_flags.get(exit_.condition, False):
                return "Algo te impide pasar."

        # Move player
        self.current_player.current_location = exit_.destination
        new_loc = self.locations.get(exit_.destination)

        # Invalidate context after movement as location changes
        self._invalidate_context()

        # Fire on_enter hook if present
        if new_loc and new_loc.on_enter:
            new_loc.on_enter(new_loc, self.current_player, self)

        # Mark location as visited (after on_enter so hook sees unvisited state)
        if new_loc:
            new_loc.visited = True

        # Return location description
        if new_loc:
            context = (
                self._get_context().to_dict() if hasattr(self, "_get_context") else {}
            )
            prose = new_loc.get_description(self.ai_enhancer, context)
            footer = self._room_footer(new_loc)
            return f"{prose}\n\n{footer}" if footer else prose
        return "Has llegado a otro lugar."

    def _handle_inventory(self) -> str:
        """Handle inventory commands"""
        if not self.current_player.inventory:
            return "No llevas nada encima."
        items = [item.name for item in self.current_player.inventory]
        return "Llevas encima: " + ", ".join(items) + "."

    def _handle_take(self, action: dict) -> str:
        """Pick up a TAKEABLE item from the current location or open container."""
        target_str = self._strip_articles(action.get("target", "").lower().strip())
        obj = self._resolve_object(target_str)

        if not obj or not isinstance(obj, models.Item):
            return f"No ves ningún '{action.get('target', target_str)}' aquí."
        if not obj.has_flag(GameFlag.TAKEABLE):
            return f"No puedes coger {obj.name}."

        # Remove from current location children (or container) and add to inventory
        current_loc = self.locations.get(self.current_player.current_location)
        if current_loc and obj.id in current_loc.children:
            current_loc.children.remove(obj.id)
        else:
            # Try containers
            for child_id in getattr(current_loc, "children", []):
                container = self.items.get(child_id)
                if container and obj.id in container.children:
                    container.children.remove(obj.id)
                    break

        self.current_player.inventory.append(obj)
        self._invalidate_context()
        return f"Coges {obj.name}."

    def _handle_drop(self, action: dict) -> str:
        """Drop an inventory item into the current location."""
        target_str = self._strip_articles(action.get("target", "").lower().strip())
        obj = next(
            (
                item
                for item in self.current_player.inventory
                if self._matches_object(item, target_str)
            ),
            None,
        )
        if not obj:
            return f"No llevas ningún '{action.get('target', target_str)}' encima."

        self.current_player.inventory.remove(obj)
        current_loc = self.locations.get(self.current_player.current_location)
        if current_loc:
            current_loc.children.append(obj.id)
        self._invalidate_context()
        return f"Dejas {obj.name} en el suelo."

    def _find_interaction(self, obj_a, obj_b, action: str):
        """Search for an interaction definition in obj_a (with=obj_b) then obj_b (with=obj_a).

        Option A: symmetric search — natural language order doesn't matter.
        """

        def _search(primary, secondary):
            for ix in getattr(primary, "interactions", []):
                if ix.action != action:
                    continue
                if ix.with_item is None:
                    return ix
                if secondary is None:
                    continue
                if (
                    ix.with_item == secondary.id
                    or ix.with_item == secondary.name.lower()
                    or ix.with_item in [s.lower() for s in secondary.synonyms]
                ):
                    return ix
            return None

        result = _search(obj_a, obj_b)
        if result is None and obj_b is not None:
            result = _search(obj_b, obj_a)
        return result

    def _check_conditions(self, conditions: list) -> tuple[bool, str]:
        """Evaluate a condition list.  Returns (all_met, failure_category).

        failure_category: 'ok' | 'physical' | 'knowledge'
        'knowledge' means physical items are present but a clue is missing — GUMSHOE hint.
        """
        physical_ok = True
        investigation = self.current_player.current_investigation

        for cond in conditions:
            if "has_item" in cond:
                item_id = cond["has_item"]
                if not any(i.id == item_id for i in self.current_player.inventory):
                    physical_ok = False
            elif "game_flag" in cond:
                if not self.game_flags.get(cond["game_flag"], False):
                    physical_ok = False

        if not physical_ok:
            return False, "physical"

        for cond in conditions:
            if "has_clue" in cond:
                if cond["has_clue"] not in investigation.discovered_clues:
                    return False, "knowledge"

        return True, "ok"

    def _apply_effects(self, effects: list) -> str:
        """Apply a list of effects and return any narrative message."""
        messages = []
        investigation = self.current_player.current_investigation

        for effect in effects:
            if "set_flag" in effect:
                self.game_flags[effect["set_flag"]] = True
            elif "reveal_clue" in effect:
                clue_id = effect["reveal_clue"]
                if clue_id in self.clues and clue_id not in investigation.discovered_clues:
                    investigation.discovered_clues[clue_id] = self.clues[clue_id]
            elif "unlock_exit" in effect:
                door = self.door_registry.get(effect["unlock_exit"])
                if door:
                    door.remove_flag(GameFlag.LOCKED)
                    door.add_flag(GameFlag.OPEN)
            elif "message" in effect and effect["message"] is not None:
                messages.append(effect["message"])

        return "\n".join(messages)

    def _handle_use(self, action: dict) -> str:
        """Handle 'usar X con Y' — resolve both objects, find interaction, check conditions."""
        target_str = self._strip_articles(action.get("target", "").lower().strip())
        with_raw = action.get("recipient") or action.get("with") or ""
        with_str = self._strip_articles(with_raw.lower().strip())

        obj_a = self._resolve_object(target_str)
        obj_b = self._resolve_object(with_str) if with_str else None

        if not obj_a:
            return f"No ves ningún '{action.get('target', target_str)}' aquí."

        interaction = self._find_interaction(obj_a, obj_b, "use")

        if not interaction:
            if obj_b:
                return f"No pasa nada especial al usar {obj_a.name} con {obj_b.name}."
            return f"No sabes cómo usar {obj_a.name} aquí."

        met, failure_type = self._check_conditions(interaction.conditions)

        if met:
            msg = self._apply_effects(interaction.on_success)
            self._invalidate_context()
            return msg or f"Usas {obj_a.name}{' con ' + obj_b.name if obj_b else ''}."

        # Failure — check for explicit message or auto-generate (GUMSHOE)
        for fe in interaction.on_failure:
            if "message" in fe:
                if fe["message"] is not None:
                    return fe["message"]
                # null → auto-generate contextual hint
                if failure_type == "knowledge" and obj_b:
                    return (
                        f"Tienes {obj_a.name} y {obj_b.name}, "
                        f"pero algo te dice que te falta información."
                    )
                return "No puedes hacer eso todavía."

        # Default fallback
        if failure_type == "knowledge":
            return "Tienes lo que necesitas, pero te falta algo más."
        return "No puedes hacer eso."

    _SPANISH_ARTICLES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "al"}

    def _strip_articles(self, text: str) -> str:
        """Remove leading Spanish articles/prepositions from a query string."""
        words = text.split()
        while words and words[0] in self._SPANISH_ARTICLES:
            words = words[1:]
        return " ".join(words) if words else text

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

        q = self._strip_articles(query.lower().strip())

        # Step 1: Player inventory
        for item in getattr(self.current_player, "inventory", []):
            if self._matches_object(item, q):
                return item

        # Steps 2-5: Location-based search
        current_loc = self.locations.get(
            getattr(self.current_player, "current_location", None)
        )
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
            if hasattr(self, "global_registry") and self.global_registry:
                global_obj = self.global_registry.find(
                    q, self.current_player.current_location
                )
                if global_obj:
                    return global_obj

            # Step 5b: Doors listed in location's local_globals
            if hasattr(self, "door_registry") and self.door_registry:
                for door_id in getattr(current_loc, "local_globals", []):
                    door = self.door_registry.get(door_id)
                    if door and self._matches_object(door, q):
                        return door

            # Step 6: Open containers in location
            for child_id in current_loc.children:
                container = self.items.get(child_id)
                if (
                    container
                    and container.has_flag(GameFlag.CONTAINER)
                    and container.has_flag(GameFlag.OPEN)
                ):
                    for nested_id in container.children:
                        nested = self.items.get(nested_id)
                        if nested and self._matches_object(nested, q):
                            return nested

        return None

    def _matches_object(self, obj, query: str) -> bool:
        """
        Check if object name or synonyms match query (case-insensitive).

        Also matches on the first word of the name so "jack" finds "Jack Napier".

        Args:
            obj: Any game object with name and synonyms attributes.
            query: Lowercased query string to match against.

        Returns:
            True if the query matches the object's name, first word, or any synonym.
        """
        if query == obj.name.lower():
            return True
        # First-word partial match: "jack" → "Jack Napier"
        name_parts = obj.name.lower().split()
        if name_parts and query == name_parts[0]:
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
