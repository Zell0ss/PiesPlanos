"""Tests for _handle_talk() and _handle_say()."""

from unittest.mock import MagicMock, patch
from src.models.models import Location, NPC


def make_engine():
    from src.engine import GameEngine
    from src.models.ai_enhancer import MockAIEnhancer

    with patch("src.engine.ClaudeEnhancer", MockAIEnhancer):
        engine = GameEngine.__new__(GameEngine)
    engine.ai_enhancer = MockAIEnhancer()
    engine.global_registry = MagicMock()
    engine.door_registry = MagicMock()
    engine._context = None
    engine.items = {}
    engine.clues = {}
    return engine


def make_npc(npc_id="jack", name="Jack Napier"):
    return NPC(
        id=npc_id,
        name=name,
        base_description="Un barman cansado.",
        personality={"temperament": "melancholic"},
        conversation_prompt="You are Jack, a tired barman.",
    )


def make_location_with_npc(npc_id="jack"):
    return Location(
        id="jazz_club",
        name="Club Azul",
        base_description="El club.",
        npcs=[npc_id],
    )


# ── _handle_talk ──────────────────────────────────────────────────────────────


def test_talk_returns_npc_response():
    engine = make_engine()
    npc = make_npc()
    loc = make_location_with_npc()
    engine.locations = {"jazz_club": loc}
    engine.npcs = {"jack": npc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_talk({"action": "talk", "target": "Jack Napier"})

    assert isinstance(result, str)
    assert len(result) > 0


def test_talk_npc_not_in_location_returns_error():
    engine = make_engine()
    loc = Location(
        id="jazz_club", name="Club Azul", base_description="El club.", npcs=[]
    )
    engine.locations = {"jazz_club": loc}
    engine.npcs = {}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_talk({"action": "talk", "target": "Jack Napier"})

    assert "Jack Napier" in result or "aquí" in result.lower()


def test_talk_adds_to_conversation_history():
    engine = make_engine()
    npc = make_npc()
    loc = make_location_with_npc()
    engine.locations = {"jazz_club": loc}
    engine.npcs = {"jack": npc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    assert len(npc.conversation_history) == 0
    engine._handle_talk({"action": "talk", "target": "Jack Napier"})
    assert len(npc.conversation_history) == 1


def test_talk_matches_npc_by_synonym():
    engine = make_engine()
    npc = NPC(
        id="jack",
        name="Jack Napier",
        base_description="El barman.",
        personality={},
        synonyms=["barman", "barra", "jack"],
    )
    loc = make_location_with_npc()
    engine.locations = {"jazz_club": loc}
    engine.npcs = {"jack": npc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_talk({"action": "talk", "target": "barman"})

    assert isinstance(result, str)
    assert len(result) > 0


def test_talk_unknown_location_returns_error():
    engine = make_engine()
    engine.locations = {}
    engine.npcs = {}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "nowhere"

    result = engine._handle_talk({"action": "talk", "target": "Jack Napier"})

    assert isinstance(result, str)
    assert len(result) > 0


# ── _handle_say ──────────────────────────────────────────────────────────────


def test_say_passes_message_to_npc():
    engine = make_engine()
    npc = make_npc()
    loc = make_location_with_npc()
    engine.locations = {"jazz_club": loc}
    engine.npcs = {"jack": npc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_say(
        {"action": "say", "target": "Jack Napier", "message": "¿Conocías a la víctima?"}
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert npc.conversation_history[0].player_input == "¿Conocías a la víctima?"


def test_say_empty_message_returns_prompt():
    engine = make_engine()
    npc = make_npc()
    loc = make_location_with_npc()
    engine.locations = {"jazz_club": loc}
    engine.npcs = {"jack": npc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_say(
        {"action": "say", "target": "Jack Napier", "message": ""}
    )

    assert isinstance(result, str)
    assert len(result) > 0
    # Should not have called the NPC (no history added)
    assert len(npc.conversation_history) == 0


def test_say_npc_not_present_returns_error():
    engine = make_engine()
    loc = Location(
        id="jazz_club", name="Club Azul", base_description="El club.", npcs=[]
    )
    engine.locations = {"jazz_club": loc}
    engine.npcs = {}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_say(
        {"action": "say", "target": "Jack Napier", "message": "Hola"}
    )

    assert isinstance(result, str)
    assert len(result) > 0
