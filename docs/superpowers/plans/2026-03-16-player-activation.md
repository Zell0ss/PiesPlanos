# Player Activation System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add invitation-based access control so only admin-activated users can play, blocking all AI calls for unregistered users.

**Architecture:** Two new DB columns (`status`, `pending_attempts`) on `players`; a `_pending` in-memory cache in `SessionManager` for fast rejection; `on_start` creates `pending` records; `/activate` flips them to `active` and notifies the user.

**Tech Stack:** Python 3.11, aiomysql, python-telegram-bot v20+, pytest-asyncio (asyncio_mode=auto), MariaDB

---

## Chunk 1: DB Layer

### Task 1: Update `_SCHEMA_SQL` and `get_player`

**Files:**
- Modify: `bot/db.py`
- Modify: `tests/bot/test_db.py`

- [ ] **Step 1: Write failing tests for the updated `get_player` return shape**

Add to `tests/bot/test_db.py`:

```python
@pytest.mark.asyncio
async def test_get_player_returns_status_field():
    row = (12345, "Lola", "The Invisible Cadaver", "pending", 0, "2026-01-01", "2026-01-02")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player(pool, telegram_id=12345)
    assert result["status"] == "pending"
    assert result["pending_attempts"] == 0

@pytest.mark.asyncio
async def test_get_player_active_status():
    row = (12345, "Lola", "The Invisible Cadaver", "active", 0, "2026-01-01", "2026-01-02")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player(pool, telegram_id=12345)
    assert result["status"] == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /data/PiesPlanos && source .venv/bin/activate
pytest tests/bot/test_db.py::test_get_player_returns_status_field tests/bot/test_db.py::test_get_player_active_status -v
```
Expected: FAIL — `KeyError: 'status'`

- [ ] **Step 3: Update `_SCHEMA_SQL` and `get_player` in `bot/db.py`**

Replace the `players` CREATE TABLE block in `_SCHEMA_SQL`:
```python
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    telegram_id      BIGINT PRIMARY KEY,
    player_name      VARCHAR(100) NOT NULL,
    case_id          VARCHAR(50)  NOT NULL,
    status           ENUM('pending', 'active') NOT NULL DEFAULT 'pending',
    pending_attempts INT NOT NULL DEFAULT 0,
    created_at       DATETIME DEFAULT NOW(),
    last_active      DATETIME DEFAULT NOW()
);
# ... rest unchanged ...
```

Replace `get_player`:
```python
async def get_player(pool: aiomysql.Pool, telegram_id: int) -> Optional[dict]:
    """Return player row as dict, or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id, player_name, case_id, status, pending_attempts, "
                "created_at, last_active "
                "FROM players WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "telegram_id": row[0],
        "player_name": row[1],
        "case_id": row[2],
        "status": row[3],
        "pending_attempts": row[4],
        "created_at": row[5],
        "last_active": row[6],
    }
```

- [ ] **Step 4: Fix the existing `test_get_player_returns_dict_when_found` test**

The existing test uses a 5-element tuple — update it to 7 elements:
```python
async def test_get_player_returns_dict_when_found():
    row = (12345, "Lola", "The Invisible Cadaver", "active", 0, "2026-01-01", "2026-01-02")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player(pool, telegram_id=12345)
    assert result is not None
    assert result["telegram_id"] == 12345
    assert result["player_name"] == "Lola"
    assert result["case_id"] == "The Invisible Cadaver"
```

- [ ] **Step 5: Run all DB tests**

```bash
pytest tests/bot/test_db.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add bot/db.py tests/bot/test_db.py
git commit -m "feat(db): add status and pending_attempts columns to players schema"
```

---

### Task 2: Update `upsert_player` + add `activate_player` and `get_pending_players`

**Files:**
- Modify: `bot/db.py`
- Modify: `tests/bot/test_db.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/bot/test_db.py`:

```python
from bot.db import activate_player, get_pending_players

@pytest.mark.asyncio
async def test_upsert_player_passes_status_to_insert():
    pool, conn, cursor = make_mock_pool()
    await upsert_player(pool, telegram_id=99, player_name="Ana",
                        case_id="The Invisible Cadaver", status="active")
    sql = cursor.execute.call_args[0][0]
    params = cursor.execute.call_args[0][1]
    assert "active" in params  # status value passed

@pytest.mark.asyncio
async def test_upsert_player_default_status_is_pending():
    pool, conn, cursor = make_mock_pool()
    await upsert_player(pool, telegram_id=99, player_name="Ana",
                        case_id="The Invisible Cadaver")
    params = cursor.execute.call_args[0][1]
    assert "pending" in params

@pytest.mark.asyncio
async def test_upsert_player_on_duplicate_does_not_update_status():
    pool, conn, cursor = make_mock_pool()
    await upsert_player(pool, telegram_id=99, player_name="Ana",
                        case_id="The Invisible Cadaver", status="pending")
    sql = cursor.execute.call_args[0][0]
    # ON DUPLICATE KEY UPDATE must NOT include 'status'
    update_clause = sql.split("ON DUPLICATE KEY UPDATE")[1]
    assert "status" not in update_clause

@pytest.mark.asyncio
async def test_activate_player_calls_update():
    pool, conn, cursor = make_mock_pool(fetchone_result=(99, "Ana", "case1", "pending", 0, None, None))
    await activate_player(pool, telegram_id=99)
    # second call is the UPDATE
    assert cursor.execute.call_count == 2
    update_sql = cursor.execute.call_args_list[1][0][0]
    assert "UPDATE" in update_sql
    assert "active" in cursor.execute.call_args_list[1][0][1]

@pytest.mark.asyncio
async def test_activate_player_raises_if_not_found():
    pool, conn, cursor = make_mock_pool(fetchone_result=None)
    with pytest.raises(ValueError, match="UID no encontrado o ya activo"):
        await activate_player(pool, telegram_id=99)

@pytest.mark.asyncio
async def test_activate_player_raises_if_already_active():
    pool, conn, cursor = make_mock_pool(
        fetchone_result=(99, "Ana", "case1", "active", 0, None, None)
    )
    with pytest.raises(ValueError, match="UID no encontrado o ya activo"):
        await activate_player(pool, telegram_id=99)

@pytest.mark.asyncio
async def test_get_pending_players_returns_list():
    pool, conn, cursor = make_mock_pool(fetchall_result=[(111,), (222,)])
    result = await get_pending_players(pool)
    assert result == [111, 222]

@pytest.mark.asyncio
async def test_get_pending_players_empty():
    pool, conn, cursor = make_mock_pool(fetchall_result=[])
    result = await get_pending_players(pool)
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/bot/test_db.py -k "activate_player or pending_players or upsert_player" -v
```
Expected: FAIL — `ImportError` or assertion errors

- [ ] **Step 3: Implement changes in `bot/db.py`**

Update `upsert_player`:
```python
async def upsert_player(
    pool: aiomysql.Pool,
    telegram_id: int,
    player_name: str,
    case_id: str,
    status: str = "pending",
) -> None:
    """Insert or update player record. status only set on INSERT, never on UPDATE."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO players (telegram_id, player_name, case_id, status) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE player_name = VALUES(player_name), "
                "last_active = NOW()",
                (telegram_id, player_name, case_id, status),
            )
        await conn.commit()
```

Add `activate_player`:
```python
async def activate_player(pool: aiomysql.Pool, telegram_id: int) -> str:
    """Set player status to 'active'. Returns player_name.
    Raises ValueError if not found or already active.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT player_name, status FROM players WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = await cursor.fetchone()
        if row is None or row[1] == "active":
            raise ValueError("UID no encontrado o ya activo.")
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE players SET status = 'active' WHERE telegram_id = %s",
                (telegram_id,),
            )
        await conn.commit()
    return row[0]  # player_name
```

Add `get_pending_players`:
```python
async def get_pending_players(pool: aiomysql.Pool) -> list[int]:
    """Return list of telegram_ids with status='pending'."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id FROM players WHERE status = 'pending'"
            )
            rows = await cursor.fetchall()
    return [row[0] for row in rows]
```

- [ ] **Step 4: Run all DB tests**

```bash
pytest tests/bot/test_db.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add bot/db.py tests/bot/test_db.py
git commit -m "feat(db): add activate_player, get_pending_players; upsert_player gains status param"
```

---

## Chunk 2: SessionManager Layer

### Task 3: Add activation methods to `SessionManager`

**Files:**
- Modify: `bot/session_manager.py`
- Modify: `tests/bot/test_session_manager.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/bot/test_session_manager.py`:

```python
def make_manager_with_admin():
    pool = MagicMock()
    game_cards = [{"name": "The Invisible Cadaver", "description": "A body",
                   "content_path": "/data/PiesPlanos/game_data",
                   "init_location": "jazz_street"}]
    return SessionManager(pool=pool, game_cards=game_cards,
                          ttl_minutes=30, admin_id=815566372)


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/bot/test_session_manager.py::TestPendingCache -v
```
Expected: FAIL — `TypeError` (unexpected keyword `admin_id`) or `AttributeError`

- [ ] **Step 3: Implement changes in `bot/session_manager.py`**

Update the constructor:
```python
class SessionManager:
    def __init__(self, pool, game_cards: list, ttl_minutes: int = 30,
                 admin_id: int = None, pending_limit: int = 3):
        self._pool = pool
        self._game_cards = {card["name"]: card for card in game_cards}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict = {}
        self._admin_id = admin_id
        self._pending: dict[int, int] = {}
        self._pending_limit = pending_limit
```

Add new methods after `has_session`:
```python
    async def load_pending(self) -> None:
        """Populate _pending cache from DB. Call once at startup after init_db."""
        pending_ids = await db.get_pending_players(self._pool)
        self._pending = {chat_id: 0 for chat_id in pending_ids}

    async def handle_pending(self, chat_id: int) -> bool:
        """Increment attempt counter. Returns True if bot should reply, False for silence."""
        self._pending[chat_id] = self._pending.get(chat_id, 0) + 1
        return self._pending[chat_id] <= self._pending_limit

    async def get_player_status(self, chat_id: int) -> Optional[str]:
        """Return player status string ('pending'/'active') or None if no DB row."""
        row = await db.get_player(self._pool, telegram_id=chat_id)
        return row["status"] if row else None

    async def activate(self, chat_id: int, bot) -> str:
        """Activate a pending player. Notifies them via bot. Returns player_name.
        Raises ValueError if not found or already active.
        """
        name = await db.activate_player(self._pool, chat_id)
        self._pending.pop(chat_id, None)
        await bot.send_message(
            chat_id=chat_id,
            text="¡Tu acceso ha sido activado! Escribe /start para comenzar.",
        )
        return name
```

Also add `Optional` to imports if not present:
```python
from typing import Optional
```

- [ ] **Step 4: Run all SessionManager tests**

```bash
pytest tests/bot/test_session_manager.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add bot/session_manager.py tests/bot/test_session_manager.py
git commit -m "feat(session): add load_pending, handle_pending, get_player_status, activate"
```

---

## Chunk 3: Handlers + Wiring

### Task 4: Update handlers (`on_start`, `on_message`, `on_activate`)

**Files:**
- Modify: `bot/handlers.py`
- Create: `tests/bot/test_handlers_activation.py`

- [ ] **Step 1: Write failing tests**

Create `tests/bot/test_handlers_activation.py`:

```python
"""Tests for activation-related handler flows."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import bot.handlers as handlers


def make_update(chat_id: int, text: str = "", first_name: str = "Ana",
                args: list = None):
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
        with patch("bot.handlers.db.upsert_player", new_callable=AsyncMock) as mock_upsert, \
             patch("bot.handlers.db.get_player", new_callable=AsyncMock,
                   return_value=None):
            sm.get_or_create = AsyncMock()
            await handlers.on_start(update, ctx)
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args
        assert call_kwargs[1].get("status") == "active" or "active" in call_kwargs[0]

    @pytest.mark.asyncio
    async def test_new_user_start_shows_pending_message_with_uid(self):
        sm = setup_handlers()
        update, ctx = make_update(chat_id=111, first_name="Ana")
        with patch("bot.handlers.db.upsert_player", new_callable=AsyncMock), \
             patch("bot.handlers.db.get_player", new_callable=AsyncMock,
                   return_value=None):
            await handlers.on_start(update, ctx)
        reply_text = update.message.reply_text.call_args[0][0]
        assert "111" in reply_text  # UID in message

    @pytest.mark.asyncio
    async def test_existing_active_user_start_shows_welcome_back(self):
        sm = setup_handlers()
        sm.get_or_create = AsyncMock()
        update, ctx = make_update(chat_id=111, first_name="Ana")
        active_row = {"telegram_id": 111, "player_name": "Ana",
                      "case_id": "The Invisible Cadaver", "status": "active",
                      "pending_attempts": 0, "created_at": None, "last_active": None}
        with patch("bot.handlers.db.get_player", new_callable=AsyncMock,
                   return_value=active_row):
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
        sm.activate = AsyncMock(side_effect=ValueError("UID no encontrado o ya activo."))
        update, ctx = make_update(chat_id=999, args=["000"])
        await handlers.on_activate(update, ctx)
        reply = update.message.reply_text.call_args[0][0]
        assert "encontrado" in reply
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/bot/test_handlers_activation.py -v
```
Expected: FAIL — `AttributeError: module 'bot.handlers' has no attribute 'on_activate'`

- [ ] **Step 3: Rewrite `bot/handlers.py`**

Key changes:
1. Add `import bot.db as db` (needed for `on_start` to call `db.upsert_player` and `db.get_player`)
2. Add module-level `admin_id: int = None`
3. Add `_PENDING_MSG` template
4. Rewrite `on_start`
5. Rewrite `on_message` guard sequence (remove `has_session`)
6. Add `on_activate`

```python
"""Telegram message handlers for Bot Lovecraft.

Routes:
  /start      → on_start()    — register player, start new game
  /ayuda      → on_ayuda()    — show help
  /activate   → on_activate() — admin: activate a pending player
  <text>      → on_message()  → SessionManager → GameEngine → response
"""
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

import bot.db as db
from bot.portrait_service import get_portrait
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Set by lovecraft.py at startup
session_manager = None
portrait_root: Path = Path("game_data/images/npcs")
admin_id: int = None
DEFAULT_CASE_ID = "The Invisible Cadaver"

_PRESENTATION = (
    "🕵️ *Bot Lovecraft* — Detective noir de texto\n\n"
    "Eres un detective privado en el Chicago de los años 30.\n"
    "Un caso sin resolver. Una ciudad llena de sombras.\n\n"
    "Escribe */start* para comenzar la investigación.\n"
    "Escribe *ayuda* en cualquier momento para ver los comandos disponibles."
)

_AYUDA = (
    "*Comandos disponibles:*\n\n"
    "• *mirar* / *look* — examinar la habitación actual\n"
    "• *examinar <objeto>* — inspeccionar un objeto\n"
    "• *hablar con <personaje>* — iniciar conversación\n"
    "• *inventario* — ver lo que llevas\n"
    "• *ir <dirección/lugar>* — moverte a otro sitio\n"
    "• *coger <objeto>* — recoger un objeto\n\n"
    "Puedes escribir en español o inglés, en lenguaje natural.\n"
    "El detective interpreta tus palabras."
)

def _pending_message(chat_id: int, player_name: str) -> str:
    return (
        f"Bienvenido/a, {player_name}. Este bot es de acceso restringido.\n\n"
        f"Tu ID de Telegram es: `{chat_id}`\n"
        "Compártelo con el administrador para que te active."
    )


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register or present pending status."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"

    if chat_id == admin_id:
        # Admin is always active
        await db.upsert_player(
            session_manager._pool, chat_id, player_name,
            DEFAULT_CASE_ID, status="active"
        )
        await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
        await update.message.reply_text(
            f"Bienvenido/a, {player_name}. El caso te espera.\n\n"
            "Escribe *mirar* para comenzar a investigar.",
            parse_mode="Markdown",
        )
        return

    # Check if existing active player is re-starting
    player_row = await db.get_player(session_manager._pool, telegram_id=chat_id)
    if player_row and player_row["status"] == "active":
        await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
        await update.message.reply_text(
            f"Bienvenido/a de nuevo, {player_name}. Escribe *mirar* para continuar.",
            parse_mode="Markdown",
        )
        return

    # New or pending user
    await db.upsert_player(
        session_manager._pool, chat_id, player_name,
        DEFAULT_CASE_ID, status="pending"
    )
    session_manager._pending.setdefault(chat_id, 0)
    await update.message.reply_text(
        _pending_message(chat_id, player_name),
        parse_mode="Markdown",
    )


async def on_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ayuda command."""
    await update.message.reply_text(_AYUDA, parse_mode="Markdown")


async def on_activate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /activate <uid> — admin only."""
    chat_id = update.effective_chat.id

    if chat_id != admin_id:
        await update.message.reply_text("No autorizado.")
        return

    if not context.args:
        await update.message.reply_text("Uso: /activate <telegram_uid>")
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("UID debe ser un número entero.")
        return

    try:
        name = await session_manager.activate(uid, context.bot)
        await update.message.reply_text(f"✅ {name} activado.")
    except ValueError as e:
        await update.message.reply_text(str(e))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a player text command."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"
    text = update.message.text.strip()

    # 1. Help keywords — always respond, no auth required
    if text.lower() in ("ayuda", "help", "comandos", "?"):
        await update.message.reply_text(_AYUDA, parse_mode="Markdown")
        return

    # 2. Fast memory check: known pending user
    if chat_id in session_manager._pending:
        should_reply = await session_manager.handle_pending(chat_id)
        if should_reply:
            await update.message.reply_text(
                _pending_message(chat_id, player_name), parse_mode="Markdown"
            )
        return

    # 3. DB check for users not in memory
    status = await session_manager.get_player_status(chat_id)
    if status == "pending":
        session_manager._pending.setdefault(chat_id, 0)
        should_reply = await session_manager.handle_pending(chat_id)
        if should_reply:
            await update.message.reply_text(
                _pending_message(chat_id, player_name), parse_mode="Markdown"
            )
        return
    if status is None:
        await update.message.reply_text(_PRESENTATION, parse_mode="Markdown")
        return

    # 4. Active player — normal game flow
    try:
        engine = await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
    except Exception as e:
        logger.error("Session error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error iniciando sesión. Intenta /start.")
        return

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, engine.process_command, text)
    except Exception as e:
        logger.error("Engine error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error procesando comando.")
        return

    npc_portrait = _extract_npc_portrait(engine, response)
    if npc_portrait:
        portrait_path = get_portrait(
            npc_id=npc_portrait["npc_id"],
            npc_portrait_filename=npc_portrait["filename"],
            portrait_root=portrait_root,
        )
        if portrait_path:
            with open(portrait_path, "rb") as f:
                await update.message.reply_photo(photo=f)

    await update.message.reply_text(response)

    try:
        await session_manager.save(chat_id=chat_id, engine=engine)
    except Exception as e:
        logger.error("Save error for chat_id=%s: %s", chat_id, e)


def _extract_npc_portrait(engine, response: str) -> dict | None:
    """Check if response came from NPC dialogue and return portrait info."""
    if not engine.current_player or not engine.npcs:
        return None
    current_loc_id = engine.current_player.current_location
    current_loc = engine.locations.get(current_loc_id)
    if not current_loc:
        return None
    for npc_id in getattr(current_loc, "npcs", []):
        npc = engine.npcs.get(npc_id)
        if npc and npc.name in response:
            portrait_filename = getattr(npc, "portrait", None)
            if portrait_filename:
                return {"npc_id": npc_id, "filename": portrait_filename}
    return None
```

- [ ] **Step 4: Run handler tests**

```bash
pytest tests/bot/test_handlers_activation.py -v
```
Expected: all pass

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add bot/handlers.py tests/bot/test_handlers_activation.py
git commit -m "feat(handlers): add activation flow — on_start pending/active, on_activate admin command"
```

---

### Task 5: Wire up `lovecraft.py` + `.env.example`

**Files:**
- Modify: `bot/lovecraft.py`
- Modify: `.env.example`

- [ ] **Step 1: Update `bot/lovecraft.py`**

Changes needed:
1. Read `ADMIN_TELEGRAM_ID` from env (raise `RuntimeError` if missing)
2. Pass `admin_id` to `SessionManager`
3. Set `handlers.admin_id`
4. Call `await session_manager.load_pending()` after `init_db`
5. Register `/activate` command handler

```python
# In build_config(), add:
admin_telegram_id = os.environ.get("ADMIN_TELEGRAM_ID") or str(base.get("admin_telegram_id", ""))
if not admin_telegram_id:
    raise RuntimeError("ADMIN_TELEGRAM_ID not set in environment or bot_config.yaml")
config["admin_telegram_id"] = int(admin_telegram_id)

# In post_init(), replace SessionManager construction:
handlers.session_manager = SessionManager(
    pool=pool,
    game_cards=game_cards,
    ttl_minutes=config.get("session_ttl_minutes", 30),
    admin_id=config["admin_telegram_id"],
)
handlers.admin_id = config["admin_telegram_id"]
await session_manager.load_pending()  # note: use handlers.session_manager here

# In main(), add handler registration:
app.add_handler(CommandHandler("activate", handlers.on_activate))
```

- [ ] **Step 2: Add `ADMIN_TELEGRAM_ID` to `.env.example`**

```bash
echo "ADMIN_TELEGRAM_ID=your_telegram_id_here" >> /data/PiesPlanos/.env.example
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 4: Verify bot starts cleanly**

```bash
cd /data/PiesPlanos && make bot
```
Expected: bot starts, logs show "MariaDB connection pool ready" and "Bot Lovecraft starting"

- [ ] **Step 5: Commit**

```bash
git add bot/lovecraft.py .env.example
git commit -m "feat(bot): wire admin_id, load_pending, /activate command registration"
```

---

## Post-Implementation Manual Test

After all tasks pass, verify end-to-end manually in Telegram:

1. Send a message to the bot from an **unknown account** without `/start` → should see presentation
2. Send `/start` from unknown account → should see pending message with UID
3. Send `mirar` from unknown account → should see pending message (attempt 1)
4. Send 3 more messages → silenced after attempt 3
5. From admin account: `/activate <uid>` → user gets notification, admin sees "✅ [name] activado."
6. User sends `/start` → gets welcome message, game starts
7. User sends `mirar` → gets game response (AI-enhanced)
8. From admin: `/activate abc` → "UID debe ser un número entero."
9. From admin: `/activate 0` → "UID no encontrado o ya activo."
10. From non-admin: `/activate 999` → "No autorizado."
