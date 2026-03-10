"""Tests for _handle_move() with named exit resolution."""
import pytest
from unittest.mock import MagicMock, patch
from src.models.models import Location
from src.models.core_data import Exit, GameFlag


def make_engine_with_locations():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    with patch('src.engine.ClaudeEnhancer', MockAIEnhancer):
        engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine._context = None  # normally set by __init__
    engine.items = {}
    engine.npcs = {}
    engine.clues = {}
    engine.game_state = "playing"
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine.door_registry.get.return_value = None  # no door by default

    street = Location(
        id="jazz_street", name="Calle", base_description="La calle.",
        synonyms=["calle", "exterior"],
        exits=[Exit(
            destination="jazz_club",
            name="puerta principal",
            aliases=["entrar", "norte", "n"],
            door_id=None
        )]
    )
    club = Location(
        id="jazz_club", name="Club", base_description="El club.",
        synonyms=["club", "interior"]
    )
    engine.locations = {"jazz_street": street, "jazz_club": club}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_street"
    engine.current_player.inventory = []
    return engine


def test_move_by_exit_name(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    engine._handle_move({"action": "move", "target": "puerta principal"})
    assert engine.current_player.current_location == "jazz_club"


def test_move_by_alias(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    engine._handle_move({"action": "move", "target": "norte"})
    assert engine.current_player.current_location == "jazz_club"


def test_move_by_destination_name(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    engine._handle_move({"action": "move", "target": "club"})
    assert engine.current_player.current_location == "jazz_club"


def test_move_no_exit_returns_message(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    result = engine._handle_move({"action": "move", "target": "dragón"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_move_blocked_by_locked_door(make_engine_with_locations=make_engine_with_locations):
    from src.models.models import Door
    engine = make_engine_with_locations()
    # Set up an exit with a locked door
    locked_door = Door(
        id="locked_door", name="puerta cerrada", base_description=".",
        connects=("jazz_street", "jazz_club"),
        flags={GameFlag.DOOR, GameFlag.LOCKED}
    )
    engine.door_registry.get.return_value = locked_door
    engine.locations["jazz_street"].exits[0].door_id = "locked_door"
    result = engine._handle_move({"action": "move", "target": "puerta principal"})
    assert engine.current_player.current_location == "jazz_street"  # didn't move
    assert isinstance(result, str)


def test_move_fires_on_enter_hook(make_engine_with_locations=make_engine_with_locations):
    engine = make_engine_with_locations()
    called = []
    engine.locations["jazz_club"].on_enter = lambda loc, player, eng: called.append(True)
    engine._handle_move({"action": "move", "target": "puerta principal"})
    assert called == [True]
