# Tomorrow — PiesPlanos Session Handoff

> Last updated: 2026-03-13

---

## What was completed today

### Bot Lovecraft — Full skeleton implemented (Tasks 1–12)

- **Design spec** written and reviewed × 4: `docs/superpowers/specs/2026-03-11-bot-lovecraft-design.md`
- **Implementation plan** written and reviewed × 2: `docs/superpowers/plans/2026-03-12-bot-lovecraft.md`

#### New files created
| File | What it does |
|---|---|
| `bot/__init__.py` | Package marker |
| `bot/db.py` | MariaDB async CRUD (players, player_state, npc_conversations) |
| `bot/session_manager.py` | `{chat_id: GameEngine}` with lazy TTL eviction (30 min) |
| `bot/portrait_service.py` | Resolves NPC portrait path from `game_data/images/npcs/` |
| `bot/handlers.py` | Telegram `on_start`, `on_message` handlers (async/sync bridge) |
| `bot/lovecraft.py` | Entry point: env config, aiomysql pool, PTB Application |
| `tests/bot/test_db.py` | 18 DB tests |
| `tests/bot/test_session_manager.py` | SessionManager tests |
| `tests/bot/test_portrait_service.py` | Portrait resolution tests |
| `Makefile` | play, bot, test, lint, db-setup, clean targets |
| `pytest.ini` | `asyncio_mode = auto` for pytest-asyncio |

#### Engine changes
- `extract_delta()` / `apply_delta()` added to `GameEngine`
- `portrait: Optional[str] = None` added to `NPC` dataclass
- `tests/test_engine_delta.py` — 18 delta tests

#### YAML changes
- `npcs.yaml`: `jack_napier_barman` now has `portrait: "jack_napier.jpg"`

---

## Key decisions / patterns

- **Delta persistence**: only save what differs from YAML baseline (not full object graph)
- **Restore sequence**: ALWAYS `start_new_game()` THEN `apply_delta()` — never reverse
- **engine_flags replace not merge**: `self.game_flags = dict(delta[...])` — not `.update()`
- **GameFlag KeyError guard**: unknown stale flag names are silently skipped (not crash)
- **Async/sync bridge**: `run_in_executor(None, engine.process_command, text)` — sync engine in async bot
- **Portrait sent BEFORE text**: portrait image → dialogue text (order matters)
- **Auto-save after every command**: errors logged but non-fatal (game continues)
- **game_data as required param**: `start_new_game(player_name, case_id, game_data=card)` — card loaded from `game_data/files/game_cards.yaml`

---

## Next task to tackle

### Option A: Activate the bot (quick win)
1. Get a TELEGRAM_TOKEN from @BotFather and add to `.env`
2. Run `make db-setup` (creates MariaDB DB + user)
3. Run `make bot` — should start polling

### Option B: `_handle_talk()` / NPC dialogue (main feature gap)
The bot skeleton is complete, but talking to NPCs returns placeholder text.
- See `src/engine.py` → `_handle_talk()` (currently returns "placeholder")
- NPC conversation design is in `docs/superpowers/specs/2026-03-11-bot-lovecraft-design.md` (portrait + dialogue section)
- Will need: `AIEnhancer.generate_npc_dialogue()` + conversation history tracking

### Option C: Item take/drop
- `_handle_take()` / `_handle_drop()` stubs exist
- Need: inventory state, item availability checks, YAML `takeable:` flag

---

## Gotchas / blockers

- **Jack Napier portrait image missing**: `game_data/images/npcs/jack_napier.jpg` doesn't exist yet — bot will send text-only response for Jack (graceful degradation works, portrait just won't show)
- **DB not set up yet**: `make db-setup` must be run before `make bot` — needs MariaDB root access
- **TELEGRAM_TOKEN empty in .env**: bot won't start until this is filled
- **pytest-asyncio version**: requirements.txt has `pytest-asyncio==1.3.0` — the correct version for `asyncio_mode = auto` is `>=0.23` — verify if tests fail

---

## Test status at end of session

```
111 tests passing (engine + bot)
0 failures
```

Run with: `make test`
