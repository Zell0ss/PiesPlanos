# Player Activation System — Design Spec

**Date:** 2026-03-16
**Project:** PiesPlanos / Bot Lovecraft
**Status:** Approved for implementation

---

## Problem

The bot currently allows any Telegram user to play immediately, with no access control. Every message from any unknown user triggers a full GameEngine + Claude API call, exposing unbounded API costs and enabling trivial abuse.

---

## Goal

Implement a lightweight invitation-based access control system where:
- Only explicitly activated users can play
- The admin (single operator) activates users via a Telegram command
- Unactivated users are handled gracefully without any AI calls
- Malicious or impatient spammers are silently ignored after 3 warnings

---

## Data Model

### DB schema changes (`bot/db.py`)

Two new columns added to `players` at table creation time (no migration needed — tables don't exist yet):

```sql
CREATE TABLE IF NOT EXISTS players (
    telegram_id   BIGINT PRIMARY KEY,
    player_name   VARCHAR(100) NOT NULL,
    case_id       VARCHAR(50) NOT NULL,
    status        ENUM('pending', 'active') NOT NULL DEFAULT 'pending',
    pending_attempts INT NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT NOW(),
    last_active   DATETIME DEFAULT NOW()
);
```

### In-memory cache (`SessionManager`)

```python
self._pending: dict[int, int]   # {chat_id: attempt_count}
self._admin_id: int             # from ADMIN_TELEGRAM_ID env var
self._pending_limit: int = 3    # max replies to pending users
```

`_pending` is populated at startup by `load_pending()` querying all `status='pending'` rows. Attempt counts are NOT persisted — they reset on restart. This is intentional: the limit is a soft deterrent, not a hard security measure.

---

## DB Changes (`bot/db.py`)

### Updated functions

**`get_player(pool, telegram_id)`** — must return all columns including `status`. Update the SELECT to `SELECT telegram_id, player_name, case_id, status, pending_attempts, created_at, last_active` and the dict construction to include `"status": row[3]`.

**`upsert_player(pool, telegram_id, player_name, case_id, status='pending')`** — gains `status` parameter. The INSERT sets `status` to the supplied value. The `ON DUPLICATE KEY UPDATE` clause must **NOT** update `status` — only `player_name` and `last_active`. This prevents re-doing `/start` from downgrading an active user back to pending.

```sql
INSERT INTO players (telegram_id, player_name, case_id, status, created_at, last_active)
VALUES (%s, %s, %s, %s, NOW(), NOW())
ON DUPLICATE KEY UPDATE player_name = VALUES(player_name), last_active = NOW()
-- status is intentionally omitted from UPDATE
```

### New functions

| Function | Purpose |
|---|---|
| `activate_player(pool, telegram_id) -> str` | UPDATE status='active', returns player_name (or raises ValueError if not found/already active) |
| `get_pending_players(pool) -> list[int]` | SELECT telegram_id FROM players WHERE status='pending' |

---

## SessionManager Changes (`bot/session_manager.py`)

### Constructor

```python
def __init__(self, pool, game_cards, ttl_minutes=30, admin_id=None, pending_limit=3):
    ...
    self._admin_id = admin_id
    self._pending: dict[int, int] = {}
    self._pending_limit = pending_limit
```

### New methods

**`async load_pending(self)`** — no `pool` parameter; uses `self._pool`
Called once at startup from `post_init` after `init_db`. Calls `db.get_pending_players(self._pool)` and populates `self._pending` with `{chat_id: 0}` for each result.

**`async def handle_pending(self, chat_id: int) -> bool`**
Increments `_pending[chat_id]`. Returns `True` if bot should reply (attempt ≤ `_pending_limit`), `False` for silence.

**`async activate(chat_id, bot) -> str`**
Uses `self._pool` internally (no `pool` parameter). Steps:
1. Calls `db.activate_player(self._pool, chat_id)` — raises `ValueError("UID no encontrado o ya activo.")` if not found/already active
2. Removes `chat_id` from `self._pending` (if present)
3. Sends `"¡Tu acceso ha sido activado! Escribe /start para comenzar."` via `await bot.send_message(chat_id, ...)`
4. Returns player name (for admin confirmation message)

---

## Handler Changes (`bot/handlers.py`)

### `on_start` — updated

**Remove the existing `has_session()` call from `on_message` entirely** — it is replaced by the new guard sequence below.

```
if chat_id == admin_id:
    await db.upsert_player(pool, chat_id, player_name, DEFAULT_CASE_ID, status='active')
    → welcome message + game initialised (same as current on_start)
else if player exists and status='active':
    → reinitialise session silently, send "Bienvenido/a de nuevo, [nombre]. Escribe *mirar* para continuar."
else:
    await db.upsert_player(pool, chat_id, player_name, DEFAULT_CASE_ID, status='pending')
    session_manager._pending.setdefault(chat_id, 0)
    → pending message with UID
```

Pending message template:
> *"Bienvenido/a, [nombre]. Este bot es de acceso restringido.*
> *Tu ID de Telegram es: `[chat_id]`*
> *Compártelo con el administrador para que te active."*

### `on_message` — updated guard sequence

The existing `has_session()` check is **removed entirely** and replaced by this sequence. All pending/activation logic is routed through `SessionManager` methods — `handlers.py` does NOT import `bot.db` directly.

```
1. text in ("ayuda", "help", "?", "comandos") → _AYUDA, return

2. chat_id in session_manager._pending (memory hit):
       should_reply = await session_manager.handle_pending(chat_id)
       if should_reply: send pending message with UID
       return

3. status = await session_manager.get_player_status(chat_id)
   # get_player_status: new SessionManager method that calls db.get_player()
   # and returns the status string, or None if no DB row.
   if status == 'pending':
       session_manager._pending.setdefault(chat_id, 0)  # initialize to 0 (counts as before first attempt)
       should_reply = await session_manager.handle_pending(chat_id)  # now attempt 1
       if should_reply: send pending message with UID
       return
   if status is None:
       send _PRESENTATION, return

4. → normal game flow (status='active' guaranteed here)
```

**`async def get_player_status(self, chat_id: int) -> Optional[str]`** — new `SessionManager` method. Calls `db.get_player(self._pool, chat_id)` and returns `row["status"]` or `None` if no row. Keeps DB access inside `SessionManager`.

**Initialization in step 3:** `_pending[chat_id]` is initialized to `0` via `setdefault`, then `handle_pending` increments to `1`. This means the first interception after a restart counts as attempt 1 — consistent with the `load_pending` behavior where all users start at `0`.

**Note on "already active" error:** `activate_player` raises `ValueError("UID no encontrado o ya activo.")` for both unknown UIDs and already-active users. This is intentional — the merged message is acceptable UX for an admin-only command on a small user base.

### `on_activate` — new handler (admin only)

Command: `/activate <telegram_uid>`

```
1. if sender != admin_id → "No autorizado.", return
2. if not context.args → "Uso: /activate <telegram_uid>", return
3. try:
       uid = int(context.args[0])
   except ValueError:
       reply "UID debe ser un número entero.", return
4. try:
       name = await session_manager.activate(uid, context.bot)
       reply "✅ [name] activado."
   except ValueError as e:
       reply str(e)  # "UID no encontrado o ya activo."
```

---

## lovecraft.py Changes

- Read `ADMIN_TELEGRAM_ID` from env (raise RuntimeError if missing)
- Pass `admin_id=admin_id` to `SessionManager` constructor
- Call `await session_manager.load_pending()` inside `post_init` after `init_db` (no args — uses `self._pool`)
- Register `CommandHandler("activate", handlers.on_activate)`
- Expose `admin_id` to handlers module: `handlers.admin_id = admin_id`

---

## User Journeys

### New user (no access)
```
User: /start
Bot:  "Bienvenido/a, Ana. Este bot es de acceso restringido.
       Tu ID de Telegram es: 987654321
       Compártelo con el administrador para que te active."

User: mirar
Bot:  [same pending message — attempt 1]

User: examinar barra
Bot:  [same pending message — attempt 2]

User: hola
Bot:  [same pending message — attempt 3]

User: algo más
Bot:  [silencio]  ← attempt 4+, no response
```

### Admin activates user
```
Admin: /activate 987654321
Bot→Admin: "✅ Ana activado."
Bot→Ana:   "¡Tu acceso ha sido activado! Escribe /start para comenzar."
```

### Admin tries to activate unknown UID
```
Admin: /activate 000000
Bot:   "UID no encontrado o ya activo."
```

### Non-admin tries to activate
```
User: /activate 123
Bot:  "No autorizado."
```

---

## Configuration

New required env var: `ADMIN_TELEGRAM_ID` (integer). Bot raises `RuntimeError` at startup if missing.

`.env.example` addition:
```
ADMIN_TELEGRAM_ID=your_telegram_id_here
```

---

## What This Does NOT Do

- No invite codes, no registration links
- No ban/deactivate command (out of scope for now)
- No multi-admin support
- No per-user rate limiting beyond the 3-attempt soft limit
- Admin account is not persisted as special in DB — identity is purely config-based

---

## Critical Assumptions

1. `ADMIN_TELEGRAM_ID` is always the same person across restarts
2. Pending attempt counter resetting on restart is acceptable (soft limit)
3. The bot serves a small, known audience — no need for automated invite flows
4. A user who does `/start` twice while pending gets a second pending record upserted (idempotent — same row, same UID shown)
