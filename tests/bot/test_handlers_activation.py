"""Tests for activation-related handler flows."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import bot.handlers as handlers


def make_update(
    chat_id: int, text: str = "", first_name: str = "Ana", args: list = None
):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.first_name = first_name
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    context = MagicMock()
    context.args = args or []
    context.bot = AsyncMock()
    return update, context


def setup_handlers(admin_id=815566372):
    sm = MagicMock()
    sm.get_or_create = AsyncMock()
    sm.save = AsyncMock()
    sm.handle_pending = AsyncMock(return_value=True)
    sm.get_player_status = AsyncMock(return_value=None)
    sm._pending = {}
    handlers.session_manager = sm
    handlers.admin_id = admin_id
    return sm


class TestOnStartActivation:
    @pytest.mark.asyncio
    async def test_admin_start_calls_upsert_with_active(self):
        sm = setup_handlers(admin_id=999)
        update, ctx = make_update(chat_id=999, first_name="Admin")
        with patch(
            "bot.handlers.db.upsert_player", new_callable=AsyncMock
        ) as mock_upsert, patch(
            "bot.handlers.db.get_player", new_callable=AsyncMock, return_value=None
        ):
            sm.get_or_create = AsyncMock()
            await handlers.on_start(update, ctx)
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args
        assert call_kwargs[1].get("status") == "active" or "active" in call_kwargs[0]

    @pytest.mark.asyncio
    async def test_new_user_start_shows_pending_message_with_uid(self):
        sm = setup_handlers()
        update, ctx = make_update(chat_id=111, first_name="Ana")
        with patch("bot.handlers.db.upsert_player", new_callable=AsyncMock), patch(
            "bot.handlers.db.get_player", new_callable=AsyncMock, return_value=None
        ):
            await handlers.on_start(update, ctx)
        reply_text = update.message.reply_text.call_args[0][0]
        assert "111" in reply_text  # UID in message

    @pytest.mark.asyncio
    async def test_existing_active_user_start_shows_welcome_back(self):
        sm = setup_handlers()
        sm.get_or_create = AsyncMock()
        update, ctx = make_update(chat_id=111, first_name="Ana")
        active_row = {
            "telegram_id": 111,
            "player_name": "Ana",
            "case_id": "The Invisible Cadaver",
            "status": "active",
            "pending_attempts": 0,
            "created_at": None,
            "last_active": None,
        }
        with patch(
            "bot.handlers.db.get_player",
            new_callable=AsyncMock,
            return_value=active_row,
        ):
            await handlers.on_start(update, ctx)
        reply_text = update.message.reply_text.call_args[0][0]
        assert "mirar" in reply_text.lower()


class TestOnMessagePendingGuard:
    @pytest.mark.asyncio
    async def test_pending_in_cache_gets_reply_on_first_attempts(self):
        sm = setup_handlers()
        sm._pending = {111: 0}
        sm.handle_pending = AsyncMock(return_value=True)
        update, ctx = make_update(chat_id=111, text="mirar")
        await handlers.on_message(update, ctx)
        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "111" in reply  # UID shown

    @pytest.mark.asyncio
    async def test_pending_in_cache_silenced_after_limit(self):
        sm = setup_handlers()
        sm._pending = {111: 3}
        sm.handle_pending = AsyncMock(return_value=False)
        update, ctx = make_update(chat_id=111, text="mirar")
        await handlers.on_message(update, ctx)
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_user_sees_presentation(self):
        sm = setup_handlers()
        sm._pending = {}
        sm.get_player_status = AsyncMock(return_value=None)
        update, ctx = make_update(chat_id=999, text="mirar")
        await handlers.on_message(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "/start" in reply

    @pytest.mark.asyncio
    async def test_pending_in_db_but_not_cache_gets_handled(self):
        sm = setup_handlers()
        sm._pending = {}
        sm.get_player_status = AsyncMock(return_value="pending")
        sm.handle_pending = AsyncMock(return_value=True)
        update, ctx = make_update(chat_id=111, text="mirar")
        await handlers.on_message(update, ctx)
        assert 111 in sm._pending
        update.message.reply_text.assert_called_once()


class TestOnActivate:
    @pytest.mark.asyncio
    async def test_non_admin_gets_unauthorized(self):
        sm = setup_handlers(admin_id=999)
        update, ctx = make_update(chat_id=111, args=["222"])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "autorizado" in reply.lower()

    @pytest.mark.asyncio
    async def test_missing_args_shows_usage(self):
        sm = setup_handlers(admin_id=999)
        update, ctx = make_update(chat_id=999, args=[])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "/activate" in reply

    @pytest.mark.asyncio
    async def test_non_integer_uid_shows_error(self):
        sm = setup_handlers(admin_id=999)
        update, ctx = make_update(chat_id=999, args=["abc"])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "número" in reply

    @pytest.mark.asyncio
    async def test_valid_activate_confirms_to_admin(self):
        sm = setup_handlers(admin_id=999)
        sm.activate = AsyncMock(return_value="Ana")
        update, ctx = make_update(chat_id=999, args=["111"])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "Ana" in reply

    @pytest.mark.asyncio
    async def test_unknown_uid_shows_error(self):
        sm = setup_handlers(admin_id=999)
        sm.activate = AsyncMock(
            side_effect=ValueError("UID no encontrado o ya activo.")
        )
        update, ctx = make_update(chat_id=999, args=["000"])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "encontrado" in reply
