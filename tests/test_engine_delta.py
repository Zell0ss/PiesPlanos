"""Tests for GameEngine.extract_delta() and apply_delta()."""

import dataclasses
from unittest.mock import MagicMock, patch

import pytest

from src.engine import GameEngine
from src.models.ai_enhancer import MockAIEnhancer
from src.models.core_data import GameFlag, ClueData, ConversationEntry
from src.models import models


def make_playing_engine() -> GameEngine:
    """Return a GameEngine in 'playing' state with minimal fake data."""
    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine._context = None
    engine.game_state = "playing"
    engine.game_flags = {}
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine.door_registry._doors = {}

    # Minimal item
    item = models.Item.__new__(models.Item)
    item.id = "old_lighter"
    item.flags = {GameFlag.TAKEABLE}

    # Minimal location
    loc = models.Location.__new__(models.Location)
    loc.id = "jazz_street"
    loc.visited = True

    engine.items = {"old_lighter": item}
    engine.locations = {"jazz_street": loc}
    engine.npcs = {}
    engine.clues = {}

    # Minimal player
    player = models.Player("p1", "Lola")
    player.current_location = "jazz_street"
    player.inventory = [item]

    investigation = models.Investigation("case1", "The Case", "A murder.")
    player.current_investigation = investigation

    engine.current_player = player
    return engine


class TestExtractDelta:
    def test_returns_dict(self):
        engine = make_playing_engine()
        delta = engine.extract_delta()
        assert isinstance(delta, dict)

    def test_current_location(self):
        engine = make_playing_engine()
        delta = engine.extract_delta()
        assert delta["current_location"] == "jazz_street"

    def test_inventory_serialized_as_ids(self):
        engine = make_playing_engine()
        delta = engine.extract_delta()
        assert delta["inventory"] == ["old_lighter"]

    def test_visited_locations(self):
        engine = make_playing_engine()
        delta = engine.extract_delta()
        assert "jazz_street" in delta["visited"]

    def test_object_flags_uses_flag_names(self):
        engine = make_playing_engine()
        delta = engine.extract_delta()
        assert "old_lighter" in delta["object_flags"]
        assert "TAKEABLE" in delta["object_flags"]["old_lighter"]

    def test_engine_flags_passthrough(self):
        engine = make_playing_engine()
        engine.game_flags = {"blood_trail": True}
        delta = engine.extract_delta()
        assert delta["engine_flags"] == {"blood_trail": True}

    def test_discovered_clues_as_list_of_ids(self):
        engine = make_playing_engine()
        clue = ClueData(id="cl1", title="Blood Stain", description="blood")
        engine.current_player.current_investigation.discovered_clues = {"cl1": clue}
        delta = engine.extract_delta()
        assert delta["discovered_clues"] == ["cl1"]

    def test_npc_conversation_history(self):
        engine = make_playing_engine()
        npc = models.NPC.__new__(models.NPC)
        npc.id = "jack"
        entry = ConversationEntry(
            timestamp="2026-01-01T00:00:00",
            player_input="hello",
            npc_response="hi",
            mood_state="neutral",
            clues_revealed=[],
        )
        npc.conversation_history = [entry]
        engine.npcs = {"jack": npc}
        delta = engine.extract_delta()
        assert "jack" in delta["npc_conversations"]
        assert delta["npc_conversations"]["jack"][0]["player_input"] == "hello"


class TestApplyDelta:
    def test_restores_current_location(self):
        engine = make_playing_engine()
        engine.current_player.current_location = "jazz_street"
        # Add a second location
        loc2 = models.Location.__new__(models.Location)
        loc2.id = "jazz_club"
        loc2.visited = False
        engine.locations["jazz_club"] = loc2

        engine.apply_delta(
            {
                "current_location": "jazz_club",
                "inventory": [],
                "visited": [],
                "object_flags": {},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        assert engine.current_player.current_location == "jazz_club"

    def test_restores_inventory(self):
        engine = make_playing_engine()
        engine.current_player.inventory = []

        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": ["old_lighter"],
                "visited": [],
                "object_flags": {},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        assert len(engine.current_player.inventory) == 1
        assert engine.current_player.inventory[0].id == "old_lighter"

    def test_restores_visited(self):
        engine = make_playing_engine()
        engine.locations["jazz_street"].visited = False

        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": ["jazz_street"],
                "object_flags": {},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        assert engine.locations["jazz_street"].visited is True

    def test_restores_object_flags(self):
        engine = make_playing_engine()
        engine.items["old_lighter"].flags = set()

        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": [],
                "object_flags": {"old_lighter": ["TAKEABLE"]},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        assert GameFlag.TAKEABLE in engine.items["old_lighter"].flags

    def test_restores_engine_flags(self):
        engine = make_playing_engine()
        engine.game_flags = {"pre_existing": True}  # pre-populate
        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": [],
                "object_flags": {},
                "engine_flags": {"fog": True},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        # Must REPLACE, not merge — pre_existing key should be gone
        assert engine.game_flags == {"fog": True}
        assert "pre_existing" not in engine.game_flags

    def test_restores_discovered_clues(self):
        engine = make_playing_engine()
        clue = ClueData(id="cl1", title="Blood Stain", description="blood")
        engine.clues = {"cl1": clue}

        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": [],
                "object_flags": {},
                "engine_flags": {},
                "discovered_clues": ["cl1"],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        assert "cl1" in engine.current_player.current_investigation.discovered_clues

    def test_restores_npc_conversations(self):
        engine = make_playing_engine()
        npc = models.NPC.__new__(models.NPC)
        npc.id = "jack"
        npc.conversation_history = []
        engine.npcs = {"jack": npc}

        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": [],
                "object_flags": {},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {
                    "jack": [
                        {
                            "timestamp": "2026-01-01T00:00:00",
                            "player_input": "hello",
                            "npc_response": "hi",
                            "mood_state": "neutral",
                            "clues_revealed": [],
                        }
                    ]
                },
            }
        )
        assert len(npc.conversation_history) == 1
        assert isinstance(npc.conversation_history[0], ConversationEntry)
        assert npc.conversation_history[0].player_input == "hello"

    def test_round_trip_extract_then_apply(self):
        """Extract delta, create fresh engine, apply delta, assert state matches."""
        engine = make_playing_engine()
        delta = engine.extract_delta()

        # Fresh engine with same baseline
        engine2 = make_playing_engine()
        engine2.current_player.current_location = "initial"
        engine2.current_player.inventory = []
        engine2.locations["jazz_street"].visited = False

        engine2.apply_delta(delta)
        assert engine2.current_player.current_location == "jazz_street"
        assert len(engine2.current_player.inventory) == 1
        assert engine2.locations["jazz_street"].visited is True

    def test_unknown_flag_name_is_skipped(self):
        engine = make_playing_engine()
        # Should not raise — unknown flags are silently skipped
        engine.apply_delta(
            {
                "current_location": "jazz_street",
                "inventory": [],
                "visited": [],
                "object_flags": {"old_lighter": ["NONEXISTENT_FLAG"]},
                "engine_flags": {},
                "discovered_clues": [],
                "clue_connections": [],
                "npc_conversations": {},
            }
        )
        # old_lighter.flags should be empty (unknown flag skipped)
        assert GameFlag.TAKEABLE not in engine.items["old_lighter"].flags

    def test_empty_delta_does_not_crash(self):
        engine = make_playing_engine()
        original_location = engine.current_player.current_location
        engine.apply_delta({})
        # Location unchanged (fallback to current value)
        assert engine.current_player.current_location == original_location
