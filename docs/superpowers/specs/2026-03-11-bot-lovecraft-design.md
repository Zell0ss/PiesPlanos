# Bot Lovecraft — Design Spec

**Date:** 2026-03-11
**Status:** Approved
**Scope:** Telegram bot interface for the Pies Planos detective text adventure game

---

## Overview

Bot Lovecraft is a Telegram bot layer that sits on top of the existing Pies Planos game engine. It exposes the game via Telegram messages with persistent sessions stored in MariaDB. The core 4-stage command pipeline (Interpret → Resolve → Route → Execute) is untouched.

---

## 1. Architecture

### Layer Diagram

```
Telegram
   ↓
bot/handlers.py         ← Telegram routing (on_message, on_start)
   ↓
SessionManager          ← {chat_id: GameEngine}, 30-min TTL
   ↓
GameEngine              ← Existing engine, one instance per user
   ↓
Response + optional NPC portrait → Telegram
```

### Key Decisions

- **Same repo (monorepo):** `bot/` is a new top-level directory in PiesPlanos.
- **GameEngine per user:** No shared state. Each `chat_id` gets its own `GameEngine` instance.
- **No changes to the 4-stage pipeline.** The bot layer is additive only.

---

## 2. SessionManager + Async Bridge

### The Sync/Async Problem

`python-telegram-bot` v20+ is fully async. `GameEngine` is synchronous. Bridge via thread executor:

```python
response = await asyncio.get_running_loop().run_in_executor(
    None, engine.process_command, command
)
```

(`asyncio.get_running_loop()` — not `get_event_loop()`, which is deprecated in Python 3.10+.)

### Message Flow (per incoming Telegram message)

1. Telegram message arrives → `handlers.py`
2. `SessionManager.get_or_create(chat_id)` → returns `GameEngine`
   - If new session: restore from MariaDB (see below)
   - If existing in-memory session: use directly
3. `run_in_executor(engine.process_command, text)` → response string
4. If response is NPC dialogue and NPC has a portrait: `portrait_service` sends photo first
5. `bot.send_message(chat_id, text=response)`
6. Auto-save delta to MariaDB: `engine.extract_delta()` → write to DB

**Known gap:** No typing indicator or timeout guard on the executor call. With slow AI API calls, users may wait silently up to Telegram's 30-second webhook limit. Deferred to post-v1.

### Session Restore Sequence

`start_new_game()` actual signature:
```python
def start_new_game(self, player_name: str, case_id: str, game_data: dict = None)
```

`game_data` is a required dict loaded from `game_cards.yaml`. Example entry:
```yaml
- name: The Invisible Cadaver
  description: "A dead body appears in the middle of a Jazz club..."
  content_path: /data/PiesPlanos/game_data
  init_location: jazz_street
```

On `get_or_create` for a returning user:
1. Load `players` row → get `player_name`, `case_id`
2. Load `game_cards.yaml`, find entry where name matches `case_id`
3. `engine.start_new_game(player_name, case_id, game_data=card_dict)` — loads YAML baseline
4. Load `player_state` row → build `delta` dict
5. Load all `npc_conversations` rows for this user
6. `engine.apply_delta(delta)` — overlays saved state onto the YAML baseline

`apply_delta()` is always called *after* `start_new_game()`, never instead of it.

### TTL and Memory Management

- **30-minute inactivity TTL.** Eviction is **lazy**: on each `get_or_create`, check `last_active`; if expired, drop the engine and run the restore sequence.
- State is always in MariaDB (saved after every command), so eviction is safe.
- Memory estimate: ~5 MB per active `GameEngine`; 5 concurrent users ≈ 25 MB.

### Persistence Authority

The existing `PersistenceManager` (SQLite, `game_saves.db`) is **bypassed** for bot sessions. `extract_delta()` and `apply_delta()` are the only persistence path in `bot/`. The SQLite system remains available for direct CLI play.

---

## 3. MariaDB Schema

### Tables

```sql
CREATE TABLE players (
    telegram_id   BIGINT PRIMARY KEY,
    player_name   VARCHAR(100) NOT NULL,
    case_id       VARCHAR(50)  NOT NULL,       -- matches game_cards.yaml `name` field
    created_at    DATETIME DEFAULT NOW(),
    last_active   DATETIME DEFAULT NOW()
);

CREATE TABLE player_state (
    telegram_id      BIGINT PRIMARY KEY,
    current_location VARCHAR(50) NOT NULL,
    inventory        JSON,   -- list[str]: item ids player has picked up
    visited          JSON,   -- list[str]: location ids player has visited
    object_flags     JSON,   -- {"item_id": ["OPEN", "LOCKED"]}: per-object GameFlag deltas
    engine_flags     JSON,   -- {"condition_name": true/false}: engine.game_flags (exit conditions)
    discovered_clues JSON,   -- list[str]: clue ids (keys of Investigation.discovered_clues)
    clue_connections JSON,   -- list of {"clue1": str, "clue2": str, "type": str, "discovered_at": str}
    updated_at       DATETIME DEFAULT NOW(),
    FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
);

CREATE TABLE npc_conversations (
    telegram_id BIGINT,
    npc_id      VARCHAR(50),
    history     JSON,        -- list of ConversationEntry dicts
    updated_at  DATETIME DEFAULT NOW(),
    PRIMARY KEY (telegram_id, npc_id)
);
```

### Delta Persistence Strategy

Only the diff from the YAML baseline is stored — not the full object graph.

| Field | Python source | Serialization |
|---|---|---|
| `current_location` | `engine.current_player.current_location` | string (location id) |
| `inventory` | `engine.current_player.inventory` (list of `Item`) | list of item id strings |
| `visited` | `location.visited` for each location | list of location id strings |
| `object_flags` | `item.flags` / `door.flags` where they differ from YAML | `{"item_id": ["FLAG_NAME", ...]}` using `GameFlag.name` |
| `engine_flags` | `engine.game_flags` | dict as-is (already `{str: bool}`) |
| `discovered_clues` | `engine.current_player.current_investigation.discovered_clues` | `list(discovered_clues.keys())` — dict keys only |
| `clue_connections` | `engine.current_player.current_investigation.clue_connections` | list verbatim (already JSON-safe dicts) |

**Two flag systems — important distinction:**
- `object_flags`: per-object `GameFlag` enum flags (e.g. `OPEN`, `LOCKED`) stored on `Item`/`Door`. Serialize as `GameFlag.name` strings; deserialize with `GameFlag[name]`.
- `engine_flags`: condition flags in `engine.game_flags` used for conditioned exits (e.g. blood trail visible). Already `dict[str, bool]` — JSON-serializable directly.

**`discovered_clues` is a `dict[str, ClueData]`** in `Investigation`. On extract: serialize as `list(keys)`. On restore via `apply_delta()`: reconstruct as `{clue_id: engine.clues[clue_id] for clue_id in saved_ids}` — look up `ClueData` objects from the YAML-loaded clue registry, not from JSON.

**`clue_connections` dict keys** (from `Investigation.connect_clues()`): `"clue1"`, `"clue2"`, `"type"`, `"discovered_at"`. Store verbatim; restore verbatim (plain dicts are sufficient — `_update_progress()` only calls `len(clue_connections)`).

**NPC conversation history** — `ConversationEntry` dataclass fields:
```python
timestamp: str
player_input: str
npc_response: str
mood_state: str
clues_revealed: List[str]
```
Serialize each as `dataclasses.asdict(entry)`. Restore via `ConversationEntry(**row)`. All fields are JSON-safe primitives — `**row` will work correctly.

### Two New GameEngine Methods (to be implemented)

These do not yet exist in `engine.py` and must be added as part of the bot implementation.

```python
def extract_delta(self) -> dict:
    """Compute what differs from YAML baseline. Returns JSON-serializable dict.

    Returns:
        {
            "current_location": str,
            "inventory": list[str],          # item ids
            "visited": list[str],            # location ids
            "object_flags": {"item_id": ["FLAG_NAME", ...]},
            "engine_flags": {"condition": bool, ...},
            "discovered_clues": list[str],   # clue ids (dict keys)
            "clue_connections": list[dict],  # verbatim connection dicts
            "npc_conversations": {"npc_id": [entry_dict, ...]}
        }
    """
    ...

def apply_delta(self, delta: dict) -> None:
    """Overlay delta onto already-loaded YAML baseline. Called after start_new_game().

    Mutates:
        - current_player.current_location
        - current_player.inventory (reconstruct Item references from item ids via self.items)
        - location.visited flags (set True for each id in delta["visited"])
        - item/door .flags (add GameFlag[name] for each flag in delta["object_flags"])
        - engine.game_flags (update from delta["engine_flags"])
        - current_investigation.discovered_clues (reconstruct {id: ClueData} from self.clues)
        - current_investigation.clue_connections (restore verbatim)
        - npc.conversation_history (reconstruct List[ConversationEntry] via ConversationEntry(**row))
    """
    ...
```

Full object graph serialization is **not in scope for v1** (future tech debt).

---

## 4. File Structure

```
PiesPlanos/
├── bot/
│   ├── __init__.py
│   ├── lovecraft.py          # Entry point: configures Application, registers handlers
│   ├── handlers.py           # on_message(), on_start() — Telegram routing logic
│   ├── session_manager.py    # SessionManager: {chat_id: GameEngine}, lazy TTL eviction
│   └── portrait_service.py   # Sends NPC portrait photo before dialogue text
├── game_data/
│   ├── portraits/            # NEW: static images per NPC
│   │   ├── jack_napier.jpg
│   │   └── ...
│   └── files/
│       └── npcs.yaml         # CHANGE: add optional `portrait: jack_napier.jpg` field
└── bot_config.yaml           # Token, DB credentials, TTL, portrait_path (NOT committed)
```

### bot_config.yaml (gitignored)

```yaml
telegram_token: "..."
session_ttl_minutes: 30
portrait_path: "game_data/portraits/"
db:
  host: localhost
  port: 3306
  user: piesplanos_bot
  database: piesplanos
```

`db.password` is **not in this file**. Load it from `DB_PASSWORD` in `.env`, consistent with the project's existing `python-dotenv` pattern:

```python
from dotenv import load_dotenv
load_dotenv()
db_password = os.environ["DB_PASSWORD"]
```

Add `bot_config.yaml` to `.gitignore`.

---

## 5. Portrait System

### npcs.yaml Change

Add an optional field to each NPC entry:

```yaml
jack_napier:
  name: "Jack Napier"
  portrait: "jack_napier.jpg"   # optional; omit if no portrait
  ...
```

### Portrait Flow

1. `portrait_service.get_portrait(npc_id)` → returns file path or `None`
2. If path exists:
   ```python
   with open(path, 'rb') as f:
       await bot.send_photo(chat_id, photo=f)
   await bot.send_message(chat_id, text=response)
   ```
3. If no portrait: send text only, no errors raised.

### Phase Roadmap

- **Phase 1 (v1):** Static per-NPC portrait images.
- **Phase 2 (future):** Room + portrait composite image. Leave a placeholder comment in `portrait_service.py` marking the extension point.

---

## 6. Non-Functional Requirements

| Requirement | Value |
|---|---|
| Python version | 3.11+ |
| Telegram library | python-telegram-bot v20+ |
| Database driver | aiomysql or PyMySQL |
| Interaction mode | Pure text (no inline buttons) |
| Save behavior | Auto-save after every command (no `/save` command needed) |
| Session persistence | Player state survives bot restarts |
| Codebase location | Same repo, `bot/` subdirectory |

---

## 7. Out of Scope (v1)

- Full object graph serialization / load (complex Python objects from JSON)
- Multi-case support per player (single active case only)
- Room + portrait composite images (Phase 2)
- Shared `GameContent` singleton (optimization for >50 concurrent users)
- Inline keyboard buttons or Telegram-specific UI affordances
- Typing indicator / timeout guard on AI calls (deferred to post-v1)
