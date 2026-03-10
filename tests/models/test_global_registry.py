# tests/models/test_global_registry.py
import pytest
from src.models.global_registry import GlobalRegistry
from src.models.core_data import GameFlag


def test_global_objects_visible_everywhere():
    registry = GlobalRegistry()
    registry.load_from_dict(
        {
            "global_objects": [
                {
                    "id": "floor",
                    "name": "suelo",
                    "base_description": "El suelo.",
                    "synonyms": ["suelo"],
                    "flags": ["SCENERY", "FIXED"],
                }
            ],
            "local_globals": [],
        }
    )
    results = registry.get_visible_objects("any_location")
    ids = [obj.id for obj in results]
    assert "floor" in ids


def test_local_globals_only_in_declared_rooms():
    registry = GlobalRegistry()
    registry.load_from_dict(
        {
            "global_objects": [],
            "local_globals": [
                {
                    "id": "jazz_music",
                    "name": "música",
                    "base_description": "Jazz.",
                    "synonyms": ["música"],
                    "flags": ["SCENERY"],
                    "visible_in": ["jazz_club", "band_room"],
                }
            ],
        }
    )
    in_club = [o.id for o in registry.get_visible_objects("jazz_club")]
    in_street = [o.id for o in registry.get_visible_objects("jazz_street")]
    assert "jazz_music" in in_club
    assert "jazz_music" not in in_street


def test_find_by_synonym():
    registry = GlobalRegistry()
    registry.load_from_dict(
        {
            "global_objects": [
                {
                    "id": "floor",
                    "name": "suelo",
                    "base_description": "El suelo.",
                    "synonyms": ["suelo", "piso"],
                    "flags": ["SCENERY"],
                }
            ],
            "local_globals": [],
        }
    )
    obj = registry.find("piso", "anywhere")
    assert obj is not None
    assert obj.id == "floor"


def test_find_returns_none_if_not_visible():
    registry = GlobalRegistry()
    registry.load_from_dict(
        {
            "global_objects": [],
            "local_globals": [
                {
                    "id": "rain",
                    "name": "lluvia",
                    "base_description": "Lluvia.",
                    "synonyms": ["lluvia"],
                    "flags": ["SCENERY"],
                    "visible_in": ["jazz_street"],
                }
            ],
        }
    )
    obj = registry.find("lluvia", "jazz_club")
    assert obj is None


def test_activate_local_global():
    registry = GlobalRegistry()
    registry.load_from_dict(
        {
            "global_objects": [],
            "local_globals": [
                {
                    "id": "blood_trail",
                    "name": "sangre",
                    "base_description": "Sangre.",
                    "synonyms": ["sangre"],
                    "flags": ["SCENERY", "INVISIBLE"],
                    "visible_in": [],
                }
            ],
        }
    )
    # Not visible initially
    assert registry.find("sangre", "jazz_club") is None
    # Activate it
    registry.activate_local_global("blood_trail", ["jazz_club"])
    assert registry.find("sangre", "jazz_club") is not None
