"""Tests for bot/session_manager.py."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
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


def make_manager_with_admin():
    pool = MagicMock()
    game_cards = [{"name": "The Invisible Cadaver", "description": "A body",
                   "content_path": "/data/PiesPlanos/game_data",
                   "init_location": "jazz_street"}]
    return SessionManager(pool=pool, game_cards=game_cards,
                          ttl_minutes=30, admin_id=815566372)


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


class TestPendingCache:
    @pytest.mark.asyncio
    async def test_load_pending_populates_cache(self):
        manager = make_manager_with_admin()
        with patch("bot.session_manager.db.get_pending_players",
                   new_callable=AsyncMock, return_value=[111, 222]):
            await manager.load_pending()
        assert 111 in manager._pending
        assert 222 in manager._pending
        assert manager._pending[111] == 0

    @pytest.mark.asyncio
    async def test_handle_pending_increments_and_allows_reply(self):
        manager = make_manager_with_admin()
        manager._pending[111] = 0
        result = await manager.handle_pending(111)
        assert result is True
        assert manager._pending[111] == 1

    @pytest.mark.asyncio
    async def test_handle_pending_silences_after_limit(self):
        manager = make_manager_with_admin()
        manager._pending[111] = 3  # at limit
        result = await manager.handle_pending(111)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_player_status_returns_status_string(self):
        manager = make_manager_with_admin()
        row = {"telegram_id": 111, "player_name": "Ana", "case_id": "c1",
               "status": "pending", "pending_attempts": 0,
               "created_at": None, "last_active": None}
        with patch("bot.session_manager.db.get_player",
                   new_callable=AsyncMock, return_value=row):
            status = await manager.get_player_status(111)
        assert status == "pending"

    @pytest.mark.asyncio
    async def test_get_player_status_returns_none_when_missing(self):
        manager = make_manager_with_admin()
        with patch("bot.session_manager.db.get_player",
                   new_callable=AsyncMock, return_value=None):
            status = await manager.get_player_status(999)
        assert status is None

    @pytest.mark.asyncio
    async def test_activate_updates_db_and_notifies_user(self):
        manager = make_manager_with_admin()
        manager._pending[111] = 2
        bot = AsyncMock()
        with patch("bot.session_manager.db.activate_player",
                   new_callable=AsyncMock, return_value="Ana"):
            name = await manager.activate(111, bot)
        assert name == "Ana"
        assert 111 not in manager._pending
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert call_kwargs[1]["chat_id"] == 111 or call_kwargs[0][0] == 111

    @pytest.mark.asyncio
    async def test_activate_raises_on_unknown_uid(self):
        manager = make_manager_with_admin()
        bot = AsyncMock()
        with patch("bot.session_manager.db.activate_player",
                   new_callable=AsyncMock,
                   side_effect=ValueError("UID no encontrado o ya activo.")):
            with pytest.raises(ValueError, match="UID no encontrado o ya activo"):
                await manager.activate(999, bot)
