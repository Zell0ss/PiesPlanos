"""Tests for the 6-step object resolution in GameEngine."""
import pytest
from unittest.mock import MagicMock, patch
from src.models.models import Item, Location
from src.models.core_data import GameFlag, Exit


def make_engine():
    """Create a minimal engine with mocked AI to avoid API calls."""
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer
    with patch('src.engine.ClaudeEnhancer', MockAIEnhancer):
        engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    # Mock registries (will be properly loaded in Task 10)
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine.global_registry.find.return_value = None
    engine.door_registry.find_by_synonym.return_value = None
    return engine


def test_resolve_from_inventory():
    engine = make_engine()
    gun = Item(id="gun", name="pistola", base_description=".", synonyms=["pistola", "arma"])
    engine.player = MagicMock()
    engine.player.inventory = [gun]
    engine.player.current_location = "jazz_club"
    engine.locations = {}
    engine.items = {}
    engine.npcs = {}
    result = engine._resolve_object("pistola")
    assert result is not None
    assert result.id == "gun"


def test_resolve_from_location_children():
    engine = make_engine()
    engine.player = MagicMock()
    engine.player.inventory = []
    engine.player.current_location = "jazz_club"
    piano = Item(id="piano", name="piano", base_description=".", synonyms=["piano"])
    loc = Location(id="jazz_club", name="Club", base_description=".", children=["piano"])
    engine.locations = {"jazz_club": loc}
    engine.items = {"piano": piano}
    engine.npcs = {}
    result = engine._resolve_object("piano")
    assert result is not None
    assert result.id == "piano"


def test_resolve_prefers_inventory_over_room():
    engine = make_engine()
    inv_gun = Item(id="gun_inv", name="pistola", base_description=".", synonyms=["pistola"])
    room_gun = Item(id="gun_room", name="pistola", base_description=".", synonyms=["pistola"])
    engine.player = MagicMock()
    engine.player.inventory = [inv_gun]
    engine.player.current_location = "jazz_club"
    loc = Location(id="jazz_club", name="Club", base_description=".", children=["gun_room"])
    engine.locations = {"jazz_club": loc}
    engine.items = {"gun_room": room_gun}
    engine.npcs = {}
    result = engine._resolve_object("pistola")
    assert result.id == "gun_inv"  # inventory wins


def test_resolve_from_open_container():
    engine = make_engine()
    engine.player = MagicMock()
    engine.player.inventory = []
    engine.player.current_location = "office"
    contract = Item(id="contract", name="contrato", base_description=".", synonyms=["contrato"])
    desk = Item(id="desk", name="escritorio", base_description=".",
                synonyms=["escritorio"],
                flags={GameFlag.CONTAINER, GameFlag.OPEN},
                children=["contract"])
    loc = Location(id="office", name="Oficina", base_description=".", children=["desk"])
    engine.locations = {"office": loc}
    engine.items = {"desk": desk, "contract": contract}
    engine.npcs = {}
    result = engine._resolve_object("contrato")
    assert result is not None
    assert result.id == "contract"


def test_resolve_not_found_returns_none():
    engine = make_engine()
    engine.player = MagicMock()
    engine.player.inventory = []
    engine.player.current_location = "jazz_club"
    loc = Location(id="jazz_club", name="Club", base_description=".", children=[])
    engine.locations = {"jazz_club": loc}
    engine.items = {}
    engine.npcs = {}
    result = engine._resolve_object("dragón")
    assert result is None


def test_matches_object_by_name():
    engine = make_engine()
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    item = Item(id="gun", name="pistola", base_description=".", synonyms=["arma"])
    assert engine._matches_object(item, "pistola")


def test_matches_object_by_synonym():
    engine = make_engine()
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    item = Item(id="gun", name="pistola", base_description=".", synonyms=["arma", "revólver"])
    assert engine._matches_object(item, "arma")
    assert not engine._matches_object(item, "cuchillo")
