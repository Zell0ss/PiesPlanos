"""Tests for bot/session_manager.py."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from bot.session_manager import SessionManager


def make_manager():
    """Return SessionManager with mocked dependencies."""
    pool = MagicMock()
    game_cards = [
        {"name": "The Invisible Cadaver",
         "description": "A body in a jazz club",
         "content_path": "/data/PiesPlanos/game_data",
         "init_location": "jazz_street"}
    ]
    return SessionManager(pool=pool, game_cards=game_cards, ttl_minutes=30)


def make_fake_engine():
    engine = MagicMock()
    engine.process_command = MagicMock(return_value="You see a street.")
    engine.extract_delta = MagicMock(return_value={
        "current_location": "jazz_street",
        "inventory": [], "visited": [], "object_flags": {},
        "engine_flags": {}, "discovered_clues": [],
        "clue_connections": [], "npc_conversations": {}
    })
    engine.apply_delta = MagicMock()
    return engine


class TestSessionManagerNewPlayer:
    @pytest.mark.asyncio
    async def test_get_or_create_returns_engine_for_new_user(self):
        manager = make_manager()
        with (
            patch("bot.session_manager.db.get_player", new_callable=AsyncMock, return_value=None),
            patch("bot.session_manager.db.upsert_player", new_callable=AsyncMock),
            patch("bot.session_manager.GameEngine") as MockEngine,
        ):
            MockEngine.return_value = make_fake_engine()
            engine = await manager.get_or_create(
                chat_id=111, player_name="Lola", case_id="The Invisible Cadaver"
            )
        assert engine is not None

    @pytest.mark.asyncio
    async def test_new_player_calls_start_new_game(self):
        manager = make_manager()
        fake_engine = make_fake_engine()
        with (
            patch("bot.session_manager.db.get_player", new_callable=AsyncMock, return_value=None),
            patch("bot.session_manager.db.upsert_player", new_callable=AsyncMock),
            patch("bot.session_manager.GameEngine", return_value=fake_engine),
        ):
            await manager.get_or_create(
                chat_id=111, player_name="Lola", case_id="The Invisible Cadaver"
            )
        fake_engine.start_new_game.assert_called_once()


class TestSessionManagerReturningPlayer:
    @pytest.mark.asyncio
    async def test_returning_player_calls_apply_delta(self):
        manager = make_manager()
        fake_engine = make_fake_engine()
        player_row = {"telegram_id": 111, "player_name": "Lola",
                      "case_id": "The Invisible Cadaver",
                      "last_active": datetime.now()}
        state_row = {"current_location": "jazz_street", "inventory": [],
                     "visited": ["jazz_street"], "object_flags": {},
                     "engine_flags": {}, "discovered_clues": [], "clue_connections": []}
        with (
            patch("bot.session_manager.db.get_player", new_callable=AsyncMock,
                  return_value=player_row),
            patch("bot.session_manager.db.get_player_state", new_callable=AsyncMock,
                  return_value=state_row),
            patch("bot.session_manager.db.get_npc_conversations", new_callable=AsyncMock,
                  return_value={}),
            patch("bot.session_manager.GameEngine", return_value=fake_engine),
        ):
            await manager.get_or_create(chat_id=111)
        fake_engine.apply_delta.assert_called_once()


class TestSessionManagerTTL:
    @pytest.mark.asyncio
    async def test_in_memory_session_reused_within_ttl(self):
        manager = make_manager()
        fake_engine = make_fake_engine()
        manager._sessions[111] = {
            "engine": fake_engine,
            "last_active": datetime.now(),
        }
        with patch("bot.session_manager.db.get_player", new_callable=AsyncMock) as mock_get:
            engine = await manager.get_or_create(chat_id=111)
        mock_get.assert_not_called()  # No DB call — session was in memory
        assert engine is fake_engine

    @pytest.mark.asyncio
    async def test_expired_session_triggers_restore(self):
        manager = make_manager()
        fake_engine = make_fake_engine()
        expired_time = datetime.now() - timedelta(minutes=31)
        manager._sessions[111] = {
            "engine": fake_engine,
            "last_active": expired_time,
        }
        player_row = {"telegram_id": 111, "player_name": "Lola",
                      "case_id": "The Invisible Cadaver",
                      "last_active": expired_time}
        state_row = {"current_location": "jazz_street", "inventory": [],
                     "visited": [], "object_flags": {}, "engine_flags": {},
                     "discovered_clues": [], "clue_connections": []}
        with (
            patch("bot.session_manager.db.get_player", new_callable=AsyncMock,
                  return_value=player_row),
            patch("bot.session_manager.db.get_player_state", new_callable=AsyncMock,
                  return_value=state_row),
            patch("bot.session_manager.db.get_npc_conversations", new_callable=AsyncMock,
                  return_value={}),
            patch("bot.session_manager.GameEngine") as MockEngine,
        ):
            MockEngine.return_value = make_fake_engine()
            engine = await manager.get_or_create(chat_id=111)
        # Should have created a NEW engine (old one expired)
        assert engine is not fake_engine


class TestSessionManagerSave:
    @pytest.mark.asyncio
    async def test_save_calls_db_functions(self):
        manager = make_manager()
        fake_engine = make_fake_engine()
        fake_engine.extract_delta.return_value = {
            "current_location": "jazz_street",
            "inventory": [], "visited": [], "object_flags": {},
            "engine_flags": {}, "discovered_clues": [], "clue_connections": [],
            "npc_conversations": {"jack": []}
        }
        with (
            patch("bot.session_manager.db.upsert_player_state", new_callable=AsyncMock) as mock_state,
            patch("bot.session_manager.db.upsert_npc_conversation", new_callable=AsyncMock) as mock_npc,
            patch("bot.session_manager.db.touch_player", new_callable=AsyncMock),
        ):
            await manager.save(chat_id=111, engine=fake_engine)
        mock_state.assert_called_once()
        mock_npc.assert_called_once_with(
            manager._pool, telegram_id=111, npc_id="jack", history=[]
        )
