"""Tests for the interaction system: _find_interaction, _check_conditions,
_apply_effects, and _handle_use."""

import pytest
from unittest.mock import MagicMock, patch
from src.models.models import Item
from src.models.core_data import GameFlag, Interaction


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
    engine.door_registry.get.return_value = None
    engine._context = None
    engine.game_flags = {}
    engine.items = {}
    engine.npcs = {}
    engine.clues = {}

    loc = MagicMock()
    loc.children = []
    loc.npcs = []
    loc.exits = []
    engine.locations = {"room": loc}

    player = MagicMock()
    player.inventory = []
    player.current_location = "room"
    player.current_investigation.discovered_clues = {}
    engine.current_player = player

    return engine


def make_item(item_id, name, synonyms=None, flags=None, interactions=None):
    return Item(
        id=item_id,
        name=name,
        base_description=f"Un {name}.",
        synonyms=synonyms or [],
        flags=flags or set(),
        interactions=interactions or [],
    )


# ──────────────────────────────────────────────
# _find_interaction
# ──────────────────────────────────────────────

class TestFindInteraction:
    def test_finds_on_primary_object(self):
        engine = make_engine()
        ix = Interaction(action="use", with_item="balas")
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas")
        assert engine._find_interaction(pistola, balas, "use") is ix

    def test_symmetric_finds_on_secondary(self):
        """Option A: if not on primary, try secondary."""
        engine = make_engine()
        ix = Interaction(action="use", with_item="pistola")
        balas = make_item("balas", "balas", interactions=[ix])
        pistola = make_item("pistola", "pistola")
        assert engine._find_interaction(pistola, balas, "use") is ix

    def test_returns_none_when_no_match(self):
        engine = make_engine()
        pistola = make_item("pistola", "pistola")
        balas = make_item("balas", "balas")
        assert engine._find_interaction(pistola, balas, "use") is None

    def test_matches_by_synonym(self):
        engine = make_engine()
        ix = Interaction(action="use", with_item="bala")  # synonym
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas", synonyms=["bala", "munición"])
        assert engine._find_interaction(pistola, balas, "use") is ix

    def test_no_secondary_object(self):
        engine = make_engine()
        ix = Interaction(action="use", with_item=None)
        llave = make_item("llave", "llave", interactions=[ix])
        assert engine._find_interaction(llave, None, "use") is ix


# ──────────────────────────────────────────────
# _check_conditions
# ──────────────────────────────────────────────

class TestCheckConditions:
    def test_empty_conditions_always_pass(self):
        engine = make_engine()
        met, category = engine._check_conditions([])
        assert met is True
        assert category == "ok"

    def test_has_item_passes_when_in_inventory(self):
        engine = make_engine()
        balas = make_item("balas", "balas")
        engine.current_player.inventory = [balas]
        met, _ = engine._check_conditions([{"has_item": "balas"}])
        assert met is True

    def test_has_item_fails_when_not_in_inventory(self):
        engine = make_engine()
        engine.current_player.inventory = []
        met, category = engine._check_conditions([{"has_item": "balas"}])
        assert met is False
        assert category == "physical"

    def test_has_clue_passes_when_discovered(self):
        engine = make_engine()
        engine.current_player.current_investigation.discovered_clues = {"pista_x": object()}
        met, _ = engine._check_conditions([{"has_clue": "pista_x"}])
        assert met is True

    def test_has_clue_fails_with_knowledge_category(self):
        engine = make_engine()
        engine.current_player.current_investigation.discovered_clues = {}
        met, category = engine._check_conditions([{"has_clue": "pista_x"}])
        assert met is False
        assert category == "knowledge"

    def test_physical_failure_takes_priority_over_knowledge(self):
        """If items are missing, category is 'physical' even if clue also missing."""
        engine = make_engine()
        engine.current_player.inventory = []
        engine.current_player.current_investigation.discovered_clues = {}
        conditions = [{"has_item": "llave"}, {"has_clue": "pista_x"}]
        met, category = engine._check_conditions(conditions)
        assert met is False
        assert category == "physical"

    def test_game_flag_passes_when_set(self):
        engine = make_engine()
        engine.game_flags = {"puerta_abierta": True}
        met, _ = engine._check_conditions([{"game_flag": "puerta_abierta"}])
        assert met is True

    def test_game_flag_fails_when_not_set(self):
        engine = make_engine()
        engine.game_flags = {}
        met, category = engine._check_conditions([{"game_flag": "puerta_abierta"}])
        assert met is False
        assert category == "physical"


# ──────────────────────────────────────────────
# _apply_effects
# ──────────────────────────────────────────────

class TestApplyEffects:
    def test_set_flag(self):
        engine = make_engine()
        engine._apply_effects([{"set_flag": "pistola_cargada"}])
        assert engine.game_flags.get("pistola_cargada") is True

    def test_reveal_clue(self):
        engine = make_engine()
        clue = MagicMock()
        engine.clues = {"pista_x": clue}
        engine.current_player.current_investigation.discovered_clues = {}
        engine._apply_effects([{"reveal_clue": "pista_x"}])
        assert "pista_x" in engine.current_player.current_investigation.discovered_clues

    def test_reveal_clue_ignores_unknown(self):
        engine = make_engine()
        engine.clues = {}
        engine._apply_effects([{"reveal_clue": "no_existe"}])  # no crash

    def test_unlock_exit(self):
        engine = make_engine()
        door = MagicMock()
        engine.door_registry.get.return_value = door
        engine._apply_effects([{"unlock_exit": "puerta_culto"}])
        door.remove_flag.assert_called_once_with(GameFlag.LOCKED)
        door.add_flag.assert_called_once_with(GameFlag.OPEN)

    def test_message_returned(self):
        engine = make_engine()
        result = engine._apply_effects([{"message": "¡Funciona!"}])
        assert result == "¡Funciona!"

    def test_null_message_not_included(self):
        engine = make_engine()
        result = engine._apply_effects([{"message": None}])
        assert result == ""

    def test_multiple_effects_combined(self):
        engine = make_engine()
        engine._apply_effects([
            {"set_flag": "pistola_cargada"},
            {"message": "Listo."},
        ])
        assert engine.game_flags.get("pistola_cargada") is True


# ──────────────────────────────────────────────
# _handle_use (integration)
# ──────────────────────────────────────────────

class TestHandleUse:
    def _setup(self, engine, pistola, balas):
        engine.items = {"pistola": pistola, "balas": balas}
        engine.locations["room"].children = ["pistola", "balas"]
        engine._context = None

    def test_success_applies_effects(self):
        engine = make_engine()
        ix = Interaction(
            action="use",
            with_item="balas",
            conditions=[],
            on_success=[{"set_flag": "pistola_cargada"}, {"message": "Pistola cargada."}],
        )
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas")
        self._setup(engine, pistola, balas)

        result = engine._handle_use({"action": "use", "target": "pistola", "recipient": "balas"})
        assert "Pistola cargada." in result
        assert engine.game_flags.get("pistola_cargada") is True

    def test_physical_failure_message(self):
        engine = make_engine()
        ix = Interaction(
            action="use",
            with_item="balas",
            conditions=[{"has_item": "balas"}],
            on_success=[{"message": "Pistola cargada."}],
            on_failure=[{"message": "No tienes balas."}],
        )
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas")
        self._setup(engine, pistola, balas)
        engine.current_player.inventory = []

        result = engine._handle_use({"action": "use", "target": "pistola", "recipient": "balas"})
        assert "No tienes balas." in result

    def test_knowledge_failure_gumshoe_hint(self):
        engine = make_engine()
        ix = Interaction(
            action="use",
            with_item="balas",
            conditions=[{"has_clue": "como_cargar"}],
            on_success=[{"message": "Cargada."}],
            on_failure=[{"message": None}],
        )
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas")
        self._setup(engine, pistola, balas)

        result = engine._handle_use({"action": "use", "target": "pistola", "recipient": "balas"})
        assert "pistola" in result.lower()
        assert "balas" in result.lower()
        assert "información" in result.lower()

    def test_no_interaction_defined(self):
        engine = make_engine()
        pistola = make_item("pistola", "pistola")
        balas = make_item("balas", "balas")
        self._setup(engine, pistola, balas)

        result = engine._handle_use({"action": "use", "target": "pistola", "recipient": "balas"})
        assert "pistola" in result.lower()
        assert "balas" in result.lower()

    def test_symmetric_order_works(self):
        """usar balas con pistola should find interaction defined on pistola."""
        engine = make_engine()
        ix = Interaction(
            action="use",
            with_item="balas",
            conditions=[],
            on_success=[{"message": "Pistola cargada."}],
        )
        pistola = make_item("pistola", "pistola", interactions=[ix])
        balas = make_item("balas", "balas")
        self._setup(engine, pistola, balas)

        # reversed order
        result = engine._handle_use({"action": "use", "target": "balas", "recipient": "pistola"})
        assert "Pistola cargada." in result

    def test_object_not_found(self):
        engine = make_engine()
        result = engine._handle_use({"action": "use", "target": "dragón", "recipient": ""})
        assert "dragón" in result.lower()
