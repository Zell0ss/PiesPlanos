# Bot Lovecraft Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Telegram bot interface to Pies Planos with full session persistence via MariaDB.

**Architecture:** A `bot/` layer sits on top of the existing `GameEngine` without modifying the 4-stage pipeline. Each Telegram user gets their own `GameEngine` instance managed by `SessionManager`. Game state is persisted as a delta (diff from YAML baseline) in MariaDB, auto-saved after every command.

**Tech Stack:** python-telegram-bot v20+ (async), aiomysql (async MariaDB), PyYAML (already present), python-dotenv (already present), dataclasses (stdlib).

**Spec:** `docs/superpowers/specs/2026-03-11-bot-lovecraft-design.md`

---

## File Map

### New files
| File | Responsibility |
|---|---|
| `bot/__init__.py` | Package marker |
| `bot/lovecraft.py` | Entry point: build `Application`, register handlers, start polling |
| `bot/handlers.py` | `on_start()`, `on_message()` — Telegram routing, calls SessionManager |
| `bot/session_manager.py` | `SessionManager`: `{chat_id: GameEngine}` dict, lazy TTL eviction, MariaDB restore |
| `bot/db.py` | Async MariaDB helpers: schema init, player CRUD, state CRUD, NPC conversation CRUD |
| `bot/portrait_service.py` | `get_portrait(npc_id, portrait_root) -> Path | None` |
| `tests/test_engine_delta.py` | Tests for `extract_delta()` / `apply_delta()` |
| `tests/bot/test_db.py` | Tests for `bot/db.py` (mocked connection) |
| `tests/bot/test_session_manager.py` | Tests for `SessionManager` (mocked DB + engine) |
| `tests/bot/test_portrait_service.py` | Tests for `portrait_service` |

### Modified files
| File | Change |
|---|---|
| `src/engine.py` | Add `extract_delta()` and `apply_delta()` methods |
| `game_data/files/npcs.yaml` | Add optional `portrait:` field to NPC entries |
| `requirements.txt` | Add `python-telegram-bot>=20.0`, `aiomysql>=0.2.0` |
| `.gitignore` | Add `bot_config.yaml` |
| `.env.example` | Add `TELEGRAM_TOKEN`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |

### NOT modified
- `src/engine.py` command pipeline — zero changes to process_command / handlers
- Any YAML game content files (except npcs.yaml portrait field)

---

## Chunk 1: GameEngine Delta Methods

**Scope:** Add `extract_delta()` and `apply_delta()` to `GameEngine`. This chunk is entirely self-contained — no bot code, no DB. After this chunk, the engine can serialize and restore its own state.

**Key facts about the data model:**
- `engine.current_player.current_location` is a **string** (location id), not a Location object
- `engine.current_player.inventory` is a `List[Item]` — serialize as list of `item.id`
- `engine.locations[id].visited` is a `bool` on each Location
- `engine.items[id].flags` and `door.flags` are `set[GameFlag]` — serialize each as `flag.name`
- `engine.game_flags` is `dict[str, bool]` — JSON-safe as-is
- `engine.current_player.current_investigation.discovered_clues` is `Dict[str, ClueData]` — serialize as `list(keys())`
- `engine.current_player.current_investigation.clue_connections` is `List[dict]` — already JSON-safe
- `engine.npcs[id].conversation_history` is `List[ConversationEntry]` — use `dataclasses.asdict()`
- `engine.door_registry` holds Door objects; their IDs can be found by iterating `door_registry._doors` (check actual attr name)

### Task 1: Write failing tests for `extract_delta()`

**Files:**
- Create: `tests/test_engine_delta.py`

- [ ] Create `tests/test_engine_delta.py`:

```python
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

        engine.apply_delta({"current_location": "jazz_club", "inventory": [],
                            "visited": [], "object_flags": {}, "engine_flags": {},
                            "discovered_clues": [], "clue_connections": [],
                            "npc_conversations": {}})
        assert engine.current_player.current_location == "jazz_club"

    def test_restores_inventory(self):
        engine = make_playing_engine()
        engine.current_player.inventory = []

        engine.apply_delta({"current_location": "jazz_street",
                            "inventory": ["old_lighter"],
                            "visited": [], "object_flags": {}, "engine_flags": {},
                            "discovered_clues": [], "clue_connections": [],
                            "npc_conversations": {}})
        assert len(engine.current_player.inventory) == 1
        assert engine.current_player.inventory[0].id == "old_lighter"

    def test_restores_visited(self):
        engine = make_playing_engine()
        engine.locations["jazz_street"].visited = False

        engine.apply_delta({"current_location": "jazz_street",
                            "inventory": [], "visited": ["jazz_street"],
                            "object_flags": {}, "engine_flags": {},
                            "discovered_clues": [], "clue_connections": [],
                            "npc_conversations": {}})
        assert engine.locations["jazz_street"].visited is True

    def test_restores_object_flags(self):
        engine = make_playing_engine()
        engine.items["old_lighter"].flags = set()

        engine.apply_delta({"current_location": "jazz_street", "inventory": [],
                            "visited": [], "object_flags": {"old_lighter": ["TAKEABLE"]},
                            "engine_flags": {}, "discovered_clues": [],
                            "clue_connections": [], "npc_conversations": {}})
        assert GameFlag.TAKEABLE in engine.items["old_lighter"].flags

    def test_restores_engine_flags(self):
        engine = make_playing_engine()
        engine.apply_delta({"current_location": "jazz_street", "inventory": [],
                            "visited": [], "object_flags": {}, "engine_flags": {"fog": True},
                            "discovered_clues": [], "clue_connections": [],
                            "npc_conversations": {}})
        assert engine.game_flags == {"fog": True}

    def test_restores_discovered_clues(self):
        engine = make_playing_engine()
        clue = ClueData(id="cl1", title="Blood Stain", description="blood")
        engine.clues = {"cl1": clue}

        engine.apply_delta({"current_location": "jazz_street", "inventory": [],
                            "visited": [], "object_flags": {}, "engine_flags": {},
                            "discovered_clues": ["cl1"], "clue_connections": [],
                            "npc_conversations": {}})
        assert "cl1" in engine.current_player.current_investigation.discovered_clues

    def test_restores_npc_conversations(self):
        engine = make_playing_engine()
        npc = models.NPC.__new__(models.NPC)
        npc.id = "jack"
        npc.conversation_history = []
        engine.npcs = {"jack": npc}

        engine.apply_delta({"current_location": "jazz_street", "inventory": [],
                            "visited": [], "object_flags": {}, "engine_flags": {},
                            "discovered_clues": [], "clue_connections": [],
                            "npc_conversations": {"jack": [
                                {"timestamp": "2026-01-01T00:00:00",
                                 "player_input": "hello",
                                 "npc_response": "hi",
                                 "mood_state": "neutral",
                                 "clues_revealed": []}
                            ]}})
        assert len(npc.conversation_history) == 1
        assert isinstance(npc.conversation_history[0], ConversationEntry)
        assert npc.conversation_history[0].player_input == "hello"
```

- [ ] Run tests to confirm they all fail (methods don't exist yet):

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/test_engine_delta.py -v 2>&1 | head -30
```

Expected: `AttributeError: 'GameEngine' object has no attribute 'extract_delta'`

### Task 2: Implement `extract_delta()` and `apply_delta()`

**Files:**
- Modify: `src/engine.py`

- [ ] Read `src/engine.py` to find the right insertion point (after `start_new_game`, before `process_command`)

- [ ] Add `extract_delta()` to `GameEngine`:

```python
def extract_delta(self) -> dict:
    """Compute current game state as a JSON-serializable delta.

    Returns only what differs from the YAML baseline, not the full object graph.
    """
    import dataclasses

    player = self.current_player
    investigation = player.current_investigation

    # Visited location ids
    visited = [loc_id for loc_id, loc in self.locations.items() if loc.visited]

    # Per-object flag snapshots (all objects, not just diffs — cheap and safe)
    object_flags: dict = {}
    for obj_id, obj in self.items.items():
        if obj.flags:
            object_flags[obj_id] = [f.name for f in obj.flags]
    # Also capture door flags
    for door_id, door in getattr(self.door_registry, "_doors", {}).items():
        if door.flags:
            object_flags[door_id] = [f.name for f in door.flags]

    # NPC conversation history
    npc_conversations: dict = {}
    for npc_id, npc in self.npcs.items():
        if npc.conversation_history:
            npc_conversations[npc_id] = [
                dataclasses.asdict(entry) for entry in npc.conversation_history
            ]

    return {
        "current_location": player.current_location,
        "inventory": [item.id for item in player.inventory],
        "visited": visited,
        "object_flags": object_flags,
        "engine_flags": dict(self.game_flags),
        "discovered_clues": list(investigation.discovered_clues.keys()),
        "clue_connections": list(investigation.clue_connections),
        "npc_conversations": npc_conversations,
    }
```

- [ ] Add `apply_delta()` to `GameEngine`:

```python
def apply_delta(self, delta: dict) -> None:
    """Overlay a saved delta onto the already-loaded YAML baseline.

    Must be called AFTER start_new_game() — requires self.items, self.locations,
    self.npcs, self.clues, and self.current_player to already be initialized.
    """
    from src.models.core_data import ConversationEntry, GameFlag

    player = self.current_player
    investigation = player.current_investigation

    # Location
    player.current_location = delta.get("current_location", player.current_location)

    # Inventory: reconstruct Item objects from ids
    inv_ids = delta.get("inventory", [])
    player.inventory = [self.items[item_id] for item_id in inv_ids if item_id in self.items]

    # Visited flags
    for loc_id in delta.get("visited", []):
        if loc_id in self.locations:
            self.locations[loc_id].visited = True

    # Object flags (items + doors)
    all_objects = dict(self.items)
    for door_id, door in getattr(self.door_registry, "_doors", {}).items():
        all_objects[door_id] = door
    for obj_id, flag_names in delta.get("object_flags", {}).items():
        if obj_id in all_objects:
            all_objects[obj_id].flags = {GameFlag[name] for name in flag_names}

    # Engine-level condition flags
    self.game_flags.update(delta.get("engine_flags", {}))

    # Discovered clues: reconstruct {id: ClueData} from clue registry
    for clue_id in delta.get("discovered_clues", []):
        if clue_id in self.clues:
            investigation.discovered_clues[clue_id] = self.clues[clue_id]

    # Clue connections (plain dicts, restore verbatim)
    investigation.clue_connections = list(delta.get("clue_connections", []))
    investigation._update_progress()

    # NPC conversation history
    for npc_id, history_rows in delta.get("npc_conversations", {}).items():
        if npc_id in self.npcs:
            self.npcs[npc_id].conversation_history = [
                ConversationEntry(**row) for row in history_rows
            ]
```

- [ ] Run tests:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/test_engine_delta.py -v
```

Expected: all green.

- [ ] Run full suite to check for regressions:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: same passing count as before (currently 75 tests).

- [ ] Commit:

```bash
cd /data/PiesPlanos && git add src/engine.py tests/test_engine_delta.py
git commit -m "feat(engine): add extract_delta() and apply_delta() for bot persistence"
```

---

## Chunk 2: Bot Persistence Layer (MariaDB)

**Scope:** `bot/db.py` — async MariaDB functions for schema creation and all CRUD operations the bot needs. No Telegram code yet; purely testable data layer.

**Prerequisites:** MariaDB running on `localhost:3306`. Database `piesplanos` and user `piesplanos_bot` must be created manually by the operator before running the bot (document in README). The schema is created automatically by `db.init_db()` on first run.

**Connection pattern:** Each async function receives a connection pool (`aiomysql.Pool`) as first argument. The pool is created once at bot startup in `lovecraft.py`.

### Task 3: Install new dependencies

- [ ] Install packages:

```bash
cd /data/PiesPlanos && source .venv/bin/activate
pip install "python-telegram-bot>=20.0" "aiomysql>=0.2.0" "pytest-asyncio>=0.23"
pip freeze > requirements.txt
```

- [ ] Create `pytest.ini` with asyncio config (required for `@pytest.mark.asyncio` to work):

```ini
[pytest]
asyncio_mode = auto
```

- [ ] Verify:

```bash
python -c "import telegram; import aiomysql; print('OK')"
```

- [ ] Add `bot_config.yaml` to `.gitignore`:

```bash
echo "bot_config.yaml" >> .gitignore
```

- [ ] Update `.env.example` — add the bot-specific variables:

```
TELEGRAM_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_PORT=3306
DB_USER=piesplanos_bot
DB_PASSWORD=your_password_here
DB_NAME=piesplanos
```

- [ ] Commit:

```bash
git add requirements.txt .gitignore .env.example
git commit -m "chore: add python-telegram-bot and aiomysql dependencies"
```

### Task 4: Write failing tests for `bot/db.py`

**Files:**
- Create: `tests/bot/__init__.py`
- Create: `tests/bot/test_db.py`

- [ ] Create `tests/bot/__init__.py` (empty)

- [ ] Create `tests/bot/test_db.py`:

```python
"""Tests for bot/db.py using mocked aiomysql connections."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# We'll mock at the aiomysql level — no real DB required
from bot.db import (
    init_db,
    get_player,
    upsert_player,
    get_player_state,
    upsert_player_state,
    get_npc_conversations,
    upsert_npc_conversation,
)


def make_mock_pool(fetchone_result=None, fetchall_result=None):
    """Build a mock aiomysql pool that returns preset query results."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=fetchone_result)
    cursor.fetchall = AsyncMock(return_value=fetchall_result or [])
    cursor.execute = AsyncMock()
    cursor.lastrowid = 1
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=False)

    conn = AsyncMock()
    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=conn)
    return pool, conn, cursor


@pytest.mark.asyncio
async def test_get_player_returns_none_when_missing():
    pool, conn, cursor = make_mock_pool(fetchone_result=None)
    result = await get_player(pool, telegram_id=12345)
    assert result is None


@pytest.mark.asyncio
async def test_get_player_returns_dict_when_found():
    row = (12345, "Lola", "The Invisible Cadaver", "2026-01-01", "2026-01-02")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player(pool, telegram_id=12345)
    assert result is not None
    assert result["telegram_id"] == 12345
    assert result["player_name"] == "Lola"
    assert result["case_id"] == "The Invisible Cadaver"


@pytest.mark.asyncio
async def test_upsert_player_calls_execute():
    pool, conn, cursor = make_mock_pool()
    await upsert_player(pool, telegram_id=12345, player_name="Lola",
                        case_id="The Invisible Cadaver")
    cursor.execute.assert_called_once()
    call_sql = cursor.execute.call_args[0][0]
    assert "INSERT" in call_sql or "REPLACE" in call_sql


@pytest.mark.asyncio
async def test_get_player_state_returns_none_when_missing():
    pool, conn, cursor = make_mock_pool(fetchone_result=None)
    result = await get_player_state(pool, telegram_id=12345)
    assert result is None


@pytest.mark.asyncio
async def test_get_player_state_deserializes_json():
    inv_json = json.dumps(["old_lighter"])
    visited_json = json.dumps(["jazz_street"])
    row = (12345, "jazz_street", inv_json, visited_json, "{}", "{}", "[]", "[]", "2026-01-01")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player_state(pool, telegram_id=12345)
    assert result["inventory"] == ["old_lighter"]
    assert result["visited"] == ["jazz_street"]


@pytest.mark.asyncio
async def test_upsert_player_state_serializes_json():
    pool, conn, cursor = make_mock_pool()
    delta = {
        "current_location": "jazz_street",
        "inventory": ["old_lighter"],
        "visited": ["jazz_street"],
        "object_flags": {},
        "engine_flags": {},
        "discovered_clues": [],
        "clue_connections": [],
    }
    await upsert_player_state(pool, telegram_id=12345, delta=delta)
    cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_npc_conversations_returns_empty_dict_when_none():
    pool, conn, cursor = make_mock_pool(fetchall_result=[])
    result = await get_npc_conversations(pool, telegram_id=12345)
    assert result == {}


@pytest.mark.asyncio
async def test_get_npc_conversations_deserializes_history():
    history_json = json.dumps([{"timestamp": "t", "player_input": "hi",
                                "npc_response": "hello", "mood_state": "neutral",
                                "clues_revealed": []}])
    rows = [("jack", history_json)]
    pool, conn, cursor = make_mock_pool(fetchall_result=rows)
    result = await get_npc_conversations(pool, telegram_id=12345)
    assert "jack" in result
    assert result["jack"][0]["player_input"] == "hi"


@pytest.mark.asyncio
async def test_upsert_npc_conversation():
    pool, conn, cursor = make_mock_pool()
    history = [{"timestamp": "t", "player_input": "hi",
                "npc_response": "hello", "mood_state": "neutral", "clues_revealed": []}]
    await upsert_npc_conversation(pool, telegram_id=12345, npc_id="jack", history=history)
    cursor.execute.assert_called_once()
```

- [ ] Run tests to confirm they fail (module doesn't exist yet):

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/bot/test_db.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'bot'`

### Task 5: Implement `bot/db.py`

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/db.py`

- [ ] Create `bot/__init__.py` (empty)

- [ ] Create `bot/db.py`:

```python
"""Async MariaDB persistence layer for Bot Lovecraft.

All functions accept an aiomysql.Pool as first argument.
Schema is created by init_db() on bot startup.
"""
import json
from typing import Optional

import aiomysql


# ── Schema ─────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    telegram_id   BIGINT PRIMARY KEY,
    player_name   VARCHAR(100) NOT NULL,
    case_id       VARCHAR(50)  NOT NULL,
    created_at    DATETIME DEFAULT NOW(),
    last_active   DATETIME DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_state (
    telegram_id      BIGINT PRIMARY KEY,
    current_location VARCHAR(50) NOT NULL,
    inventory        JSON,
    visited          JSON,
    object_flags     JSON,
    engine_flags     JSON,
    discovered_clues JSON,
    clue_connections JSON,
    updated_at       DATETIME DEFAULT NOW(),
    FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
);

CREATE TABLE IF NOT EXISTS npc_conversations (
    telegram_id BIGINT,
    npc_id      VARCHAR(50),
    history     JSON,
    updated_at  DATETIME DEFAULT NOW(),
    PRIMARY KEY (telegram_id, npc_id)
);
"""


async def init_db(pool: aiomysql.Pool) -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    async with pool.acquire() as conn:
        for statement in _SCHEMA_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                async with conn.cursor() as cursor:
                    await cursor.execute(stmt)
        await conn.commit()


# ── Players ────────────────────────────────────────────────────────────────

async def get_player(pool: aiomysql.Pool, telegram_id: int) -> Optional[dict]:
    """Return player row as dict, or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id, player_name, case_id, created_at, last_active "
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
        "created_at": row[3],
        "last_active": row[4],
    }


async def upsert_player(
    pool: aiomysql.Pool,
    telegram_id: int,
    player_name: str,
    case_id: str,
) -> None:
    """Insert or update player record, refreshing last_active."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO players (telegram_id, player_name, case_id) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE player_name = VALUES(player_name), "
                "last_active = NOW()",
                (telegram_id, player_name, case_id),
            )
        await conn.commit()


async def touch_player(pool: aiomysql.Pool, telegram_id: int) -> None:
    """Update last_active timestamp for a player."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE players SET last_active = NOW() WHERE telegram_id = %s",
                (telegram_id,),
            )
        await conn.commit()


# ── Player State ───────────────────────────────────────────────────────────

async def get_player_state(pool: aiomysql.Pool, telegram_id: int) -> Optional[dict]:
    """Return deserialized player state delta, or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id, current_location, inventory, visited, "
                "object_flags, engine_flags, discovered_clues, clue_connections, updated_at "
                "FROM player_state WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "current_location": row[1],
        "inventory": json.loads(row[2]) if row[2] else [],
        "visited": json.loads(row[3]) if row[3] else [],
        "object_flags": json.loads(row[4]) if row[4] else {},
        "engine_flags": json.loads(row[5]) if row[5] else {},
        "discovered_clues": json.loads(row[6]) if row[6] else [],
        "clue_connections": json.loads(row[7]) if row[7] else [],
    }


async def upsert_player_state(
    pool: aiomysql.Pool,
    telegram_id: int,
    delta: dict,
) -> None:
    """Persist a delta dict to player_state. Creates or replaces the row."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "REPLACE INTO player_state "
                "(telegram_id, current_location, inventory, visited, "
                "object_flags, engine_flags, discovered_clues, clue_connections) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    telegram_id,
                    delta["current_location"],
                    json.dumps(delta.get("inventory", [])),
                    json.dumps(delta.get("visited", [])),
                    json.dumps(delta.get("object_flags", {})),
                    json.dumps(delta.get("engine_flags", {})),
                    json.dumps(delta.get("discovered_clues", [])),
                    json.dumps(delta.get("clue_connections", [])),
                ),
            )
        await conn.commit()


# ── NPC Conversations ──────────────────────────────────────────────────────

async def get_npc_conversations(
    pool: aiomysql.Pool,
    telegram_id: int,
) -> dict:
    """Return {npc_id: list[entry_dict]} for all NPCs for a player."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT npc_id, history FROM npc_conversations WHERE telegram_id = %s",
                (telegram_id,),
            )
            rows = await cursor.fetchall()
    return {
        row[0]: json.loads(row[1]) if row[1] else []
        for row in rows
    }


async def upsert_npc_conversation(
    pool: aiomysql.Pool,
    telegram_id: int,
    npc_id: str,
    history: list,
) -> None:
    """Persist NPC conversation history. Creates or replaces the row."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "REPLACE INTO npc_conversations (telegram_id, npc_id, history) "
                "VALUES (%s, %s, %s)",
                (telegram_id, npc_id, json.dumps(history)),
            )
        await conn.commit()
```

- [ ] Run the DB tests:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/bot/test_db.py -v
```

Expected: all green.

- [ ] Commit:

```bash
git add bot/__init__.py bot/db.py tests/bot/__init__.py tests/bot/test_db.py requirements.txt
git commit -m "feat(bot): add async MariaDB persistence layer (bot/db.py)"
```

---

## Chunk 3: SessionManager

**Scope:** `bot/session_manager.py` — manages `{chat_id: GameEngine}` dict with lazy TTL eviction, handles session creation (new player) and restore (returning player), and auto-saves after every command.

### Task 6: Write failing tests for `SessionManager`

**Files:**
- Create: `tests/bot/test_session_manager.py`

- [ ] Create `tests/bot/test_session_manager.py`:

```python
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
```

- [ ] Run to confirm failure:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/bot/test_session_manager.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'bot.session_manager'`

### Task 7: Implement `bot/session_manager.py`

**Files:**
- Create: `bot/session_manager.py`

- [ ] Create `bot/session_manager.py`:

```python
"""SessionManager: per-user GameEngine instances with lazy TTL eviction.

Usage:
    manager = SessionManager(pool, game_cards, ttl_minutes=30)
    engine = await manager.get_or_create(chat_id, player_name, case_id)
    await manager.save(chat_id, engine)
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from src.engine import GameEngine
from src.models.ai_enhancer import ClaudeEnhancer
import bot.db as db


class SessionManager:
    def __init__(self, pool, game_cards: list, ttl_minutes: int = 30):
        self._pool = pool
        self._game_cards = {card["name"]: card for card in game_cards}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict = {}  # {chat_id: {"engine": GameEngine, "last_active": datetime}}

    async def get_or_create(
        self,
        chat_id: int,
        player_name: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> GameEngine:
        """Return an active GameEngine for chat_id.

        - If session is live and within TTL: return it directly.
        - If expired or missing: restore from DB (or start fresh for new players).
        """
        # Check in-memory session
        session = self._sessions.get(chat_id)
        if session and (datetime.now() - session["last_active"]) < self._ttl:
            session["last_active"] = datetime.now()
            return session["engine"]

        # Session expired or missing — restore from DB
        engine = await self._restore_or_create(chat_id, player_name, case_id)
        self._sessions[chat_id] = {"engine": engine, "last_active": datetime.now()}
        return engine

    async def save(self, chat_id: int, engine: GameEngine) -> None:
        """Persist current engine state as a delta. Called after every command."""
        delta = engine.extract_delta()
        npc_conversations = delta.pop("npc_conversations", {})

        await db.upsert_player_state(self._pool, telegram_id=chat_id, delta=delta)
        for npc_id, history in npc_conversations.items():
            await db.upsert_npc_conversation(
                self._pool, telegram_id=chat_id, npc_id=npc_id, history=history
            )
        await db.touch_player(self._pool, telegram_id=chat_id)

    # ── Private ────────────────────────────────────────────────────────────

    async def _restore_or_create(
        self,
        chat_id: int,
        player_name: Optional[str],
        case_id: Optional[str],
    ) -> GameEngine:
        player_row = await db.get_player(self._pool, telegram_id=chat_id)

        engine = GameEngine()

        if player_row is None:
            # Brand-new player
            card = self._game_cards.get(case_id)
            if card is None:
                raise ValueError(f"Unknown case_id: {case_id!r}")
            engine.start_new_game(player_name, case_id, game_data=card)
            await db.upsert_player(
                self._pool, telegram_id=chat_id,
                player_name=player_name, case_id=case_id
            )
        else:
            # Returning player — restore state
            pname = player_row["player_name"]
            pcaseid = player_row["case_id"]
            card = self._game_cards.get(pcaseid)
            if card is None:
                raise ValueError(f"Unknown case_id in DB: {pcaseid!r}")
            engine.start_new_game(pname, pcaseid, game_data=card)

            state = await db.get_player_state(self._pool, telegram_id=chat_id)
            npc_convs = await db.get_npc_conversations(self._pool, telegram_id=chat_id)

            if state:
                state["npc_conversations"] = npc_convs
                engine.apply_delta(state)

        return engine
```

- [ ] Run SessionManager tests:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/bot/test_session_manager.py -v
```

Expected: all green.

- [ ] Commit:

```bash
git add bot/session_manager.py tests/bot/test_session_manager.py
git commit -m "feat(bot): add SessionManager with lazy TTL eviction and delta restore"
```

---

## Chunk 4: Portrait Service

**Scope:** `bot/portrait_service.py` — stateless helper that resolves NPC portrait paths. Simple enough to need only 1 task.

### Task 8: Portrait service (test + implement together)

**Files:**
- Create: `bot/portrait_service.py`
- Create: `tests/bot/test_portrait_service.py`

- [ ] Create `tests/bot/test_portrait_service.py`:

```python
"""Tests for bot/portrait_service.py."""
from pathlib import Path
import pytest

from bot.portrait_service import get_portrait


def test_returns_path_when_file_exists(tmp_path):
    portrait_root = tmp_path
    (portrait_root / "jack_napier.jpg").write_bytes(b"fake-image")
    result = get_portrait("jack_napier", npc_portrait_filename="jack_napier.jpg",
                          portrait_root=portrait_root)
    assert result is not None
    assert result.exists()


def test_returns_none_when_file_missing(tmp_path):
    result = get_portrait("jack_napier", npc_portrait_filename="jack_napier.jpg",
                          portrait_root=tmp_path)
    assert result is None


def test_returns_none_when_npc_has_no_portrait(tmp_path):
    result = get_portrait("jack_napier", npc_portrait_filename=None,
                          portrait_root=tmp_path)
    assert result is None
```

- [ ] Create `bot/portrait_service.py`:

```python
"""Portrait service: resolve NPC portrait file paths.

Phase 1: static per-NPC images from game_data/images/npcs/
Phase 2 (future): room + portrait composite — add a compose_portrait() here.
"""
from pathlib import Path
from typing import Optional


def get_portrait(
    npc_id: str,
    npc_portrait_filename: Optional[str],
    portrait_root: Path,
) -> Optional[Path]:
    """Return the portrait file Path for an NPC, or None if unavailable.

    Args:
        npc_id: NPC identifier (used for logging only).
        npc_portrait_filename: value of the `portrait:` field in npcs.yaml, or None.
        portrait_root: directory where portrait images are stored.

    Returns:
        Path to the image file if it exists, else None.
    """
    if not npc_portrait_filename:
        return None
    path = Path(portrait_root) / npc_portrait_filename
    return path if path.exists() else None
```

- [ ] Run portrait tests:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/bot/test_portrait_service.py -v
```

Expected: all green.

- [ ] Commit:

```bash
git add bot/portrait_service.py tests/bot/test_portrait_service.py
git commit -m "feat(bot): add portrait_service for NPC portrait resolution"
```

---

## Chunk 5: Telegram Handlers + Entry Point + YAML

**Scope:** The actual Telegram bot — `handlers.py`, `lovecraft.py`, and wiring it all together. Also update `npcs.yaml` to add the `portrait:` field. No automated tests for Telegram handlers (the async mock complexity is not worth it for v1) — manual test documented instead.

### Task 9: Add `portrait` field to `NPC` dataclass, then update `npcs.yaml`

**IMPORTANT ORDER:** The dataclass must be updated BEFORE the YAML file. `engine.py` line 129 does `models.NPC(**npc)` — any unknown key in the YAML dict causes `TypeError` on engine startup.

**Files:**
- Modify: `src/models/models.py` (NPC dataclass)
- Modify: `game_data/files/npcs.yaml`

- [ ] Read `src/models/models.py`, find the `NPC` dataclass, and add `portrait` as an optional field:

```python
@dataclass
class NPC(GameObject):
    ...
    portrait: Optional[str] = None   # filename in game_data/images/npcs/, or None
    ...
```

Add it after the existing fields with default `None` so it is always optional. Use `Optional[str]` (already imported in models.py via `from typing import Optional`).

- [ ] Run existing tests to confirm nothing broke:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: same count as before (no regressions).

- [ ] Read `game_data/files/npcs.yaml` to find the Jack Napier entry, then add `portrait:` field:

```yaml
- id: jack_napier_barman
  name: Jack Napier
  portrait: "jack_napier.jpg"   # optional; file must be in game_data/images/npcs/
  base_description: ...
```

(Only add the `portrait:` field — do not change anything else in the file.)

- [ ] Commit:

```bash
git add src/models/models.py game_data/files/npcs.yaml
git commit -m "feat(game): add optional portrait field to NPC dataclass and Jack Napier"
```

### Task 10: Implement `bot/handlers.py`

**Files:**
- Create: `bot/handlers.py`

- [ ] Create `bot/handlers.py`:

```python
"""Telegram message handlers for Bot Lovecraft.

Routes:
  /start  → on_start()    — register player, start new game
  <text>  → on_message()  → SessionManager → GameEngine → response
"""
import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.portrait_service import get_portrait

logger = logging.getLogger(__name__)

# These are set by lovecraft.py at startup
session_manager = None
portrait_root: Path = Path("game_data/images/npcs")
DEFAULT_CASE_ID = "The Invisible Cadaver"


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register player and initialise a new game session."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"

    await update.message.reply_text(
        f"Bienvenido/a, {player_name}. El caso te espera.\n\n"
        "Escribe cualquier cosa para comenzar a investigar."
    )

    await session_manager.get_or_create(
        chat_id=chat_id,
        player_name=player_name,
        case_id=DEFAULT_CASE_ID,
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a player text command."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"
    text = update.message.text

    try:
        engine = await session_manager.get_or_create(
            chat_id=chat_id,
            player_name=player_name,
            case_id=DEFAULT_CASE_ID,
        )
    except Exception as e:
        logger.error("Session error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error iniciando sesión. Intenta /start.")
        return

    # Run sync GameEngine in a thread (GameEngine is not async)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, engine.process_command, text)
    except Exception as e:
        logger.error("Engine error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error procesando comando.")
        return

    # Send portrait if this is NPC dialogue and NPC has a portrait
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

    # Auto-save delta
    try:
        await session_manager.save(chat_id=chat_id, engine=engine)
    except Exception as e:
        logger.error("Save error for chat_id=%s: %s", chat_id, e)
        # Don't crash the bot on save failure; player already got their response


def _extract_npc_portrait(engine, response: str) -> dict | None:
    """Check if response came from NPC dialogue and return portrait info.

    Returns {"npc_id": str, "filename": str} or None.
    This is a best-effort heuristic: check if current location has an NPC
    whose name appears in the response.
    """
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

- [ ] Commit:

```bash
git add bot/handlers.py
git commit -m "feat(bot): add Telegram message handlers"
```

### Task 11: Implement `bot/lovecraft.py` entry point

**Files:**
- Create: `bot/lovecraft.py`

- [ ] Create `bot/lovecraft.py`:

```python
"""Bot Lovecraft — entry point.

Usage:
    source .venv/bin/activate
    export TELEGRAM_TOKEN=... DB_HOST=... DB_USER=... DB_PASSWORD=... DB_NAME=...
    python -m bot.lovecraft

Or use a bot_config.yaml (not committed) and run:
    python -m bot.lovecraft --config bot_config.yaml
"""
import asyncio
import logging
import os
from pathlib import Path

import aiomysql
import yaml
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import bot.handlers as handlers
from bot.db import init_db
from bot.session_manager import SessionManager

logger = logging.getLogger(__name__)


def load_game_cards(cards_path: str = "game_cards.yaml") -> list:
    with open(cards_path) as f:
        return yaml.safe_load(f)


async def main(config: dict) -> None:
    db_config = config["db"]
    pool = await aiomysql.create_pool(
        host=db_config["host"],
        port=db_config.get("port", 3306),
        user=db_config["user"],
        password=db_config["password"],
        db=db_config["database"],
        autocommit=False,
    )
    await init_db(pool)
    logger.info("MariaDB connection pool ready.")

    game_cards = load_game_cards()
    handlers.session_manager = SessionManager(
        pool=pool,
        game_cards=game_cards,
        ttl_minutes=config.get("session_ttl_minutes", 30),
    )
    handlers.portrait_root = Path(config.get("portrait_path", "game_data/images/npcs"))

    app = Application.builder().token(config["telegram_token"]).build()
    app.add_handler(CommandHandler("start", handlers.on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_message))

    logger.info("Bot Lovecraft starting...")
    await app.run_polling()


def build_config() -> dict:
    """Build config from environment variables (primary) or bot_config.yaml (fallback)."""
    load_dotenv()

    config_path = Path("bot_config.yaml")
    base: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            base = yaml.safe_load(f) or {}

    # Environment variables override file values
    token = os.environ.get("TELEGRAM_TOKEN") or base.get("telegram_token")
    db_password = os.environ.get("DB_PASSWORD") or base.get("db", {}).get("password")
    db_user = os.environ.get("DB_USER") or base.get("db", {}).get("user")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN not set in environment or bot_config.yaml")
    if not db_password:
        raise RuntimeError("DB_PASSWORD not set (set env var DB_PASSWORD)")
    if not db_user:
        raise RuntimeError("DB_USER not set (set env var DB_USER or add to bot_config.yaml)")

    config = {
        "telegram_token": token,
        "session_ttl_minutes": int(os.environ.get("SESSION_TTL_MINUTES",
                                                    base.get("session_ttl_minutes", 30))),
        "portrait_path": os.environ.get("PORTRAIT_PATH",
                                         base.get("portrait_path", "game_data/images/npcs")),
        "db": {
            "host": os.environ.get("DB_HOST", base.get("db", {}).get("host", "localhost")),
            "port": int(os.environ.get("DB_PORT", base.get("db", {}).get("port", 3306))),
            "user": db_user,
            "password": db_password,
            "database": os.environ.get("DB_NAME", base.get("db", {}).get("database", "piesplanos")),
        },
    }
    return config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(build_config()))
```

- [ ] Commit:

```bash
git add bot/lovecraft.py
git commit -m "feat(bot): add lovecraft.py entry point with config loading"
```

### Task 12: Run full test suite

- [ ] Run all tests:

```bash
cd /data/PiesPlanos && source .venv/bin/activate && PYTHONPATH=/data/PiesPlanos pytest tests/ -v --tb=short
```

Expected: all existing tests still pass, new bot tests pass.

- [ ] Commit any fixes needed, then tag the milestone:

```bash
git tag bot-v1-skeleton
```

---

## Manual Test Checklist (no real Telegram required)

These are smoke tests to run locally before connecting a real bot token.

- [ ] **Test delta round-trip:**
  ```python
  # In Python REPL with PYTHONPATH set
  from src.engine import GameEngine
  import yaml
  with open("game_cards.yaml") as f: cards = yaml.safe_load(f)
  e = GameEngine()
  e.start_new_game("Lola", "The Invisible Cadaver", game_data=cards[0])
  delta = e.extract_delta()
  print(delta["current_location"])  # should be "jazz_street"
  e2 = GameEngine()
  e2.start_new_game("Lola", "The Invisible Cadaver", game_data=cards[0])
  e2.apply_delta(delta)
  print(e2.current_player.current_location)  # should match delta
  ```

- [ ] **Test SessionManager with real DB** (requires MariaDB up with `piesplanos` db):
  ```bash
  python -c "
  import asyncio, aiomysql, yaml
  from bot.db import init_db
  from bot.session_manager import SessionManager
  async def test():
      pool = await aiomysql.create_pool(host='localhost', port=3306,
          user='piesplanos_bot', password='your_pw', db='piesplanos')
      await init_db(pool)
      with open('game_cards.yaml') as f: cards = yaml.safe_load(f)
      sm = SessionManager(pool, cards)
      engine = await sm.get_or_create(99999, 'TestUser', 'The Invisible Cadaver')
      r = engine.process_command('mirar alrededor')
      print('Response:', r[:80])
      await sm.save(99999, engine)
      print('Saved OK')
      pool.close()
  asyncio.run(test())
  "
  ```

- [ ] **Start bot with real token:**
  ```bash
  cd /data/PiesPlanos   # REQUIRED: GameEngine loads YAML with relative paths
  export TELEGRAM_TOKEN=your_token
  export DB_PASSWORD=your_pw
  python -m bot.lovecraft
  ```
  Send `/start` in Telegram, then a text command. Confirm response arrives and DB row is created.

  > **Note:** The bot **must** be launched from `/data/PiesPlanos` as working directory. `GameEngine` uses relative paths like `game_data/files/` when loading YAML content. If launched from any other directory, all game content will silently fail to load.

---

## DB Setup (one-time operator task)

Run these in MariaDB as root before starting the bot:

```sql
CREATE DATABASE piesplanos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'piesplanos_bot'@'localhost' IDENTIFIED BY 'choose_strong_password';
GRANT ALL PRIVILEGES ON piesplanos.* TO 'piesplanos_bot'@'localhost';
FLUSH PRIVILEGES;
```

Tables are created automatically by `init_db()` on first run.
