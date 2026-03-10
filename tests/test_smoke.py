"""
Smoke tests — verify the full stack loads and basic commands work.
Uses MockAIEnhancer to avoid API calls.
"""

import pytest
from unittest.mock import patch


@pytest.fixture
def engine():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer

    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        game = GameEngine()
    game.start_new_game(
        "detective",
        "case_01",
        {
            "content_path": "game_data",
            "name": "Test Case",
            "description": "A test.",
            "init_location": "jazz_club",
        },
    )
    return game


def test_engine_loads(engine):
    assert engine is not None
    assert len(engine.locations) > 0
    assert len(engine.items) > 0


def test_engine_has_registries(engine):
    assert engine.global_registry is not None
    assert engine.door_registry is not None


def test_starting_location_exists(engine):
    loc_id = engine.current_player.current_location
    assert loc_id in engine.locations


def test_global_objects_loaded(engine):
    objs = engine.global_registry.get_visible_objects("anywhere")
    ids = [o.id for o in objs]
    assert "floor" in ids
    assert "walls" in ids


def test_doors_loaded(engine):
    door = engine.door_registry.get("main_door")
    assert door is not None


def test_handler_registered(engine):
    jazz_club = engine.locations.get("jazz_club")
    if jazz_club:  # only if jazz_club is the starting location or loaded
        assert jazz_club.on_enter is not None


def test_examine_command(engine):
    # Examine an item known to be in the starting location
    loc_id = engine.current_player.current_location
    loc = engine.locations[loc_id]
    if loc.children:
        first_item_id = loc.children[0]
        item = engine.items.get(first_item_id)
        if item:
            result = engine.process_command(
                f"examina {item.synonyms[0] if item.synonyms else item.name}"
            )
            assert isinstance(result, str)
            assert len(result) > 0


def test_inventory_command(engine):
    result = engine.process_command("inventario")
    assert isinstance(result, str)


def test_move_command(engine):
    loc_id = engine.current_player.current_location
    loc = engine.locations[loc_id]
    if loc.exits:
        exit_ = loc.exits[0]
        result = engine.process_command(f"ve a {exit_.name}")
        assert isinstance(result, str)
        assert len(result) > 0
