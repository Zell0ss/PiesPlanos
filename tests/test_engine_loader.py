"""Tests for engine loading doors, globals, and handlers."""

import pytest
from unittest.mock import patch, MagicMock


def make_engine():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer

    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        engine = GameEngine()
    return engine


def test_engine_has_global_registry(make_engine=make_engine):
    engine = make_engine()
    assert hasattr(engine, "global_registry")
    assert engine.global_registry is not None


def test_engine_has_door_registry(make_engine=make_engine):
    engine = make_engine()
    assert hasattr(engine, "door_registry")
    assert engine.door_registry is not None


def test_global_registry_loaded_with_objects(make_engine=make_engine):
    engine = make_engine()
    # floor and walls should be globally visible
    objs = engine.global_registry.get_visible_objects("anywhere")
    ids = [o.id for o in objs]
    assert "floor" in ids
    assert "walls" in ids


def test_door_registry_loaded_with_doors(make_engine=make_engine):
    engine = make_engine()
    door = engine.door_registry.get("main_door")
    assert door is not None
    assert "jazz_club" in door.connects


def test_handler_registered_on_location(make_engine=make_engine):
    engine = make_engine()
    # jazz_club location should have on_enter hook registered
    jazz_club = engine.locations.get("jazz_club")
    assert jazz_club is not None
    assert jazz_club.on_enter is not None
