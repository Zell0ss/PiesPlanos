"""Tests for the DoorRegistry class."""
import pytest
from src.models.door_registry import DoorRegistry
from src.models.core_data import GameFlag


def test_load_door():
    """Test loading a single door from YAML data."""
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "main_door",
        "name": "puerta principal",
        "base_description": "Una puerta.",
        "synonyms": ["puerta"],
        "flags": ["DOOR", "OPENABLE", "OPEN"],
        "connects": ["jazz_street", "jazz_club"],
        "key_id": None,
        "unlock_condition": None
    }])
    door = registry.get("main_door")
    assert door is not None
    assert door.id == "main_door"
    assert door.name == "puerta principal"
    assert door.has_flag(GameFlag.OPEN)
    assert door.has_flag(GameFlag.DOOR)


def test_door_other_side():
    """Test that door.other_side() returns the correct destination."""
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "main_door",
        "name": "puerta principal",
        "base_description": "Una puerta.",
        "synonyms": ["puerta"],
        "flags": ["DOOR", "OPEN"],
        "connects": ["jazz_street", "jazz_club"],
        "key_id": None,
        "unlock_condition": None
    }])
    door = registry.get("main_door")
    assert door.other_side("jazz_street") == "jazz_club"
    assert door.other_side("jazz_club") == "jazz_street"
    assert door.other_side("unknown") is None


def test_doors_for_location():
    """Test finding all doors that connect to a specific location."""
    registry = DoorRegistry()
    registry.load_from_list([
        {
            "id": "d1",
            "name": "d1",
            "base_description": "d1",
            "synonyms": [],
            "flags": [],
            "connects": ["room_a", "room_b"],
            "key_id": None,
            "unlock_condition": None
        },
        {
            "id": "d2",
            "name": "d2",
            "base_description": "d2",
            "synonyms": [],
            "flags": [],
            "connects": ["room_a", "room_c"],
            "key_id": None,
            "unlock_condition": None
        },
        {
            "id": "d3",
            "name": "d3",
            "base_description": "d3",
            "synonyms": [],
            "flags": [],
            "connects": ["room_x", "room_y"],
            "key_id": None,
            "unlock_condition": None
        },
    ])
    doors = registry.doors_for_location("room_a")
    ids = [d.id for d in doors]
    assert "d1" in ids
    assert "d2" in ids
    assert "d3" not in ids
    assert len(doors) == 2


def test_find_by_synonym():
    """Test finding a door by name or synonym."""
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "main_door",
        "name": "puerta principal",
        "base_description": "Una puerta.",
        "synonyms": ["puerta", "entrada"],
        "flags": [],
        "connects": ["a", "b"],
        "key_id": None,
        "unlock_condition": None
    }])
    # Find by name
    door = registry.find_by_synonym("puerta principal")
    assert door is not None
    assert door.id == "main_door"

    # Find by synonym
    door = registry.find_by_synonym("entrada")
    assert door is not None
    assert door.id == "main_door"

    # Find by another synonym
    door = registry.find_by_synonym("puerta")
    assert door is not None
    assert door.id == "main_door"

    # Case insensitive
    door = registry.find_by_synonym("ENTRADA")
    assert door is not None

    # Not found
    door = registry.find_by_synonym("nonexistent")
    assert door is None


def test_multiple_doors():
    """Test loading multiple doors and retrieving them."""
    registry = DoorRegistry()
    registry.load_from_list([
        {
            "id": "door_a",
            "name": "Door A",
            "base_description": "First door",
            "synonyms": ["a"],
            "flags": ["DOOR"],
            "connects": ["room_1", "room_2"],
            "key_id": None,
            "unlock_condition": None
        },
        {
            "id": "door_b",
            "name": "Door B",
            "base_description": "Second door",
            "synonyms": ["b"],
            "flags": ["DOOR"],
            "connects": ["room_2", "room_3"],
            "key_id": None,
            "unlock_condition": None
        }
    ])
    assert registry.get("door_a") is not None
    assert registry.get("door_b") is not None
    assert registry.get("nonexistent") is None


def test_door_flags():
    """Test that all specified flags are properly set."""
    registry = DoorRegistry()
    registry.load_from_list([{
        "id": "locked_door",
        "name": "locked door",
        "base_description": "A locked door",
        "synonyms": [],
        "flags": ["DOOR", "OPENABLE", "LOCKABLE", "LOCKED"],
        "connects": ["a", "b"],
        "key_id": "key_1",
        "unlock_condition": None
    }])
    door = registry.get("locked_door")
    assert door.has_flag(GameFlag.DOOR)
    assert door.has_flag(GameFlag.OPENABLE)
    assert door.has_flag(GameFlag.LOCKABLE)
    assert door.has_flag(GameFlag.LOCKED)
    assert not door.has_flag(GameFlag.OPEN)
    assert door.key_id == "key_1"


def test_empty_registry():
    """Test that an empty registry returns None for nonexistent doors."""
    registry = DoorRegistry()
    assert registry.get("any_id") is None
    assert registry.find_by_synonym("any_query") is None
    assert registry.doors_for_location("any_location") == []
