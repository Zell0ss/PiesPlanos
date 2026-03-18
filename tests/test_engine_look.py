"""Tests for _handle_look() — describe the current location."""

from unittest.mock import MagicMock, patch
from src.models.models import Location, Item, NPC
from src.models.core_data import GameFlag, Exit


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
    engine.npcs = {}
    engine.clues = {}
    return engine


def test_look_returns_location_description():
    engine = make_engine()
    loc = Location(
        id="jazz_club", name="Club Azul", base_description="El interior del club."
    )
    engine.locations = {"jazz_club": loc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    result = engine._handle_look()

    assert isinstance(result, str)
    assert len(result) > 0


def test_look_fires_on_look_hook():
    engine = make_engine()
    hook = MagicMock()
    loc = Location(
        id="jazz_club", name="Club Azul", base_description="El club.", on_look=hook
    )
    engine.locations = {"jazz_club": loc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    engine._handle_look()

    hook.assert_called_once_with(loc, engine.current_player, engine)


def test_look_skips_hook_when_none():
    engine = make_engine()
    loc = Location(id="jazz_club", name="Club Azul", base_description="El club.")
    engine.locations = {"jazz_club": loc}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "jazz_club"

    # Should not raise
    result = engine._handle_look()
    assert isinstance(result, str)


def test_look_unknown_location_returns_message():
    engine = make_engine()
    engine.locations = {}
    engine.current_player = MagicMock()
    engine.current_player.current_location = "nowhere"

    result = engine._handle_look()

    assert isinstance(result, str)
    assert len(result) > 0


def test_examine_location_name_falls_back_to_look():
    """examine with the current location's name should describe the room, not fail."""
    engine = make_engine()
    loc = Location(
        id="jazz_club", name="Club Azul", base_description="El interior del club."
    )
    engine.locations = {"jazz_club": loc}
    engine.current_player = MagicMock()
    engine.current_player.inventory = []
    engine.current_player.current_location = "jazz_club"
    engine.global_registry.find.return_value = None
    engine.door_registry.find_by_synonym.return_value = None

    result = engine._handle_examine({"action": "examine", "target": "Club Azul"})

    assert isinstance(result, str)
    assert len(result) > 0
    # Should not be the "no ves ningún" error
    assert "Club Azul" not in result or "No ves" not in result


# ── _room_footer ───────────────────────────────────────────────────────────────


def _make_engine_with_location(loc, items=None, npcs=None):
    engine = make_engine()
    engine.locations = {loc.id: loc}
    engine.items = items or {}
    engine.npcs = npcs or {}
    engine.current_player = MagicMock()
    engine.current_player.current_location = loc.id
    engine.current_player.inventory = []
    return engine


def test_look_footer_includes_visible_items():
    gun = Item(id="gun", name="pistola", base_description=".", synonyms=[])
    loc = Location(id="room", name="Sala", base_description="Oscuro.", children=["gun"])
    engine = _make_engine_with_location(loc, items={"gun": gun})

    result = engine._handle_look()

    assert "pistola" in result


def test_look_footer_excludes_scenery_items():
    piano = Item(
        id="piano",
        name="piano",
        base_description=".",
        synonyms=[],
        flags={GameFlag.SCENERY},
    )
    loc = Location(
        id="room", name="Sala", base_description="Oscuro.", children=["piano"]
    )
    engine = _make_engine_with_location(loc, items={"piano": piano})

    result = engine._handle_look()

    assert "piano" not in result


def test_look_footer_excludes_invisible_items():
    trail = Item(
        id="trail",
        name="rastro de sangre",
        base_description=".",
        synonyms=[],
        flags={GameFlag.INVISIBLE},
    )
    loc = Location(
        id="room", name="Sala", base_description="Oscuro.", children=["trail"]
    )
    engine = _make_engine_with_location(loc, items={"trail": trail})

    result = engine._handle_look()

    assert "rastro de sangre" not in result


def test_look_footer_includes_npcs():
    npc = NPC(id="jack", name="Jack Napier", base_description=".", personality={})
    loc = Location(
        id="room", name="Sala", base_description="Oscuro.", children=[], npcs=["jack"]
    )
    engine = _make_engine_with_location(loc, npcs={"jack": npc})

    result = engine._handle_look()

    assert "Jack Napier" in result


def test_look_footer_includes_exits():
    exit_ = Exit(
        destination="street", name="puerta principal", aliases=["salir", "sur"]
    )
    street = Location(id="street", name="La Calle", base_description=".")
    loc = Location(id="room", name="Sala", base_description="Oscuro.", exits=[exit_])
    engine = _make_engine_with_location(loc)
    engine.locations["street"] = street

    result = engine._handle_look()

    assert "La Calle" in result
    assert "Salidas" in result


def test_look_footer_no_exits_section_when_none():
    loc = Location(id="room", name="Sala", base_description="Oscuro.", exits=[])
    engine = _make_engine_with_location(loc)

    result = engine._handle_look()

    assert "Salidas" not in result


def test_room_footer_empty_room_no_footer():
    loc = Location(
        id="room",
        name="Sala",
        base_description="Oscuro.",
        children=[],
        npcs=[],
        exits=[],
    )
    engine = _make_engine_with_location(loc)

    footer = engine._room_footer(loc)

    assert footer == ""
