"""Tests for _handle_examine() using the 6-step resolver."""

import pytest
from unittest.mock import MagicMock, patch
from src.models.models import Item, Location
from src.models.core_data import GameFlag


def make_engine():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer

    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine.global_registry = MagicMock()
    engine.global_registry.find.return_value = None
    engine.door_registry = MagicMock()
    engine.door_registry.find_by_synonym.return_value = None
    engine._context = None
    engine.items = {}
    engine.npcs = {}
    engine.clues = {}
    return engine


def test_examine_item_in_location(make_engine=make_engine):
    engine = make_engine()
    piano = Item(
        id="piano", name="piano", base_description="Un piano viejo.", synonyms=["piano"]
    )
    loc = Location(
        id="jazz_club", name="Club", base_description="El club.", children=["piano"]
    )
    engine.locations = {"jazz_club": loc}
    engine.items = {"piano": piano}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_examine({"action": "examine", "target": "piano"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_examine_sets_examined_flag(make_engine=make_engine):
    engine = make_engine()
    gun = Item(
        id="gun", name="pistola", base_description="Una pistola.", synonyms=["pistola"]
    )
    loc = Location(
        id="jazz_club", name="Club", base_description="El club.", children=["gun"]
    )
    engine.locations = {"jazz_club": loc}
    engine.items = {"gun": gun}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "jazz_club"

    assert not gun.has_flag(GameFlag.EXAMINED)
    engine._handle_examine({"action": "examine", "target": "pistola"})
    assert gun.has_flag(GameFlag.EXAMINED)


def test_examine_item_in_open_container(make_engine=make_engine):
    engine = make_engine()
    contract = Item(
        id="contract",
        name="contrato",
        base_description="Un contrato.",
        synonyms=["contrato"],
    )
    desk = Item(
        id="desk",
        name="escritorio",
        base_description="Un escritorio.",
        synonyms=["escritorio"],
        flags={GameFlag.CONTAINER, GameFlag.OPEN},
        children=["contract"],
    )
    loc = Location(
        id="office", name="Oficina", base_description="Una oficina.", children=["desk"]
    )
    engine.locations = {"office": loc}
    engine.items = {"desk": desk, "contract": contract}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "office"

    result = engine._handle_examine({"action": "examine", "target": "contrato"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_examine_not_found_returns_message(make_engine=make_engine):
    engine = make_engine()
    loc = Location(id="jazz_club", name="Club", base_description="El club.")
    engine.locations = {"jazz_club": loc}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_examine({"action": "examine", "target": "dragón"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_examine_pre_resolved_object(make_engine=make_engine):
    """Bug #1 regression: _handle_examine must not crash when target is already an Item."""
    engine = make_engine()
    piano = Item(
        id="piano", name="piano", base_description="Un piano viejo.", synonyms=["piano"]
    )
    loc = Location(
        id="jazz_club", name="Club", base_description="El club.", children=["piano"]
    )
    engine.locations = {"jazz_club": loc}
    engine.items = {"piano": piano}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "jazz_club"

    # Simulate process_command having pre-resolved "piano" → Item object
    result = engine._handle_examine({"action": "examine", "target": piano})
    assert isinstance(result, str)
    assert len(result) > 0
    assert piano.has_flag(GameFlag.EXAMINED)
