# Pies Planos - Project Briefing

> **Purpose**: Knowledge transfer between Claude Code and Claude Web, executive summary for developers.
>
> **Audience**: Claude AI (both instances) and developer

---

## What is this project

A GUMSHOE-style detective text adventure game that uses Claude AI to:
1. Interpret natural language commands into structured game actions
2. Enhance descriptions with noir atmosphere without changing game mechanics
3. Generate personality-driven NPC dialogue with conversation memory

The player investigates crimes by examining scenes, interrogating NPCs, and connecting clues.

---

## How it works (data flow)

```
1. INPUT: Player types natural language command ("examine the dusty desk")
2. INTERPRET: Claude converts to JSON {"action": "examine", "target": "desk"}
3. RESOLVE: GameEngine maps "desk" → Item object via fuzzy matching
4. ROUTE: Action type → Handler method (_handle_examine)
5. EXECUTE: Game logic + AI enhancement → Response
6. OUTPUT: Atmospheric narrative displayed to player
```

**The Four-Stage Pipeline** is critical. All commands flow through:
- **Interpret** (AI): Natural language → Structured JSON
- **Resolve** (Engine): String references → Game objects
- **Route** (Engine): Action type → Handler method
- **Execute** (Handler): Game logic + AI narrative → Response

**AI Boundary Rule**: AI enhances atmosphere but NEVER alters game mechanics. Clue discovery, item properties, and state changes are determined by YAML and game logic only.

---

## Tech Stack

- **Language**: Python 3.11
- **AI Integration**:
  - LangChain 0.3.27 - Chain orchestration
  - langchain-anthropic 0.3.20 - Claude API wrapper
  - anthropic SDK - Direct API access
- **Database**: SQLite - Player saves, NPC conversation history
- **Game Content**: YAML files (locations, items, NPCs, clues)
- **Utilities**: fuzzywuzzy (string matching), colorama (terminal), tenacity (retries)
- **Infrastructure**: Local execution, requires Claude API key

---

## CLI Commands

| Command | What it does | Example |
|---------|--------------|---------|
| `./play.sh` | Launch game with auto-setup | `./play.sh` |
| `python main.py` | Launch game (manual) | Requires PYTHONPATH set |
| `pytest tests/ -v` | Run test suite | All tests with verbose output |
| `black . && ruff check .` | Code formatting + linting | Pre-commit check |

---

## Project Structure

```
PiesPlanos/
├── main.py                    # Entry point, game loop
├── src/
│   ├── engine.py              # GameEngine: command pipeline orchestrator
│   ├── models/
│   │   ├── models.py          # GameObject, Player, Item, Door, NPC, Location, Investigation
│   │   ├── core_data.py       # GameFlag enum, Exit, ClueData, ConversationEntry
│   │   ├── global_registry.py # Global + local-global object visibility
│   │   ├── door_registry.py   # Shared door objects (visible from 2 rooms)
│   │   ├── ai_enhancer.py     # ClaudeEnhancer, MockAIEnhancer
│   │   └── game_context.py    # Context builder for AI calls
│   ├── chains/
│   │   └── command_chains.py  # LangChain command interpretation
│   └── utils/
│       └── utils.py           # PersistenceManager (SQLite)
├── game_data/
│   ├── files/                 # YAML: locations, items, npcs, clues, doors, globals
│   └── handlers/              # Python hooks per location (on_enter, on_look, etc.)
└── tests/                     # Pytest test suite
```

**Key Modules**:
- **engine.py**: Orchestrates the 4-stage pipeline, loads YAML + registries + handlers
- **models.py**: Core entities — all inherit `GameObject`, share flag/synonym/children system
- **global_registry.py** + **door_registry.py**: Visibility system for ambient objects and doors
- **ai_enhancer.py**: Abstract interface + Claude implementation for all AI calls

---

## Critical Design Decisions

### 1. Four-Stage Command Pipeline

**Why**: Separates concerns cleanly - AI handles language, engine handles game logic.

**Alternatives discarded**: Direct AI game control (unpredictable), keyword parsing (poor UX).

**Trade-off**: More complexity in routing, but deterministic game behavior.

### 2. AI Enhancement Boundaries

**Why**: Game integrity - AI must never decide clue discovery or change state.

**Alternatives discarded**: Full AI control (breaks game balance), no AI (poor atmosphere).

**Trade-off**: System prompts must be carefully crafted to enforce boundaries.

### 3. YAML Content Authority

**Why**: Game content lives in data files, not Python code. Easy to add scenarios.

**Alternatives discarded**: Hardcoded content (inflexible), database (overkill).

**Trade-off**: YAML must be loaded and validated on startup.

### 4. SQLite Persistence

**Why**: Simple, no server needed, supports multiple players.

**Alternatives discarded**: JSON files (concurrent issues), PostgreSQL (overkill).

**Trade-off**: Object reconstruction from JSON not yet implemented for load.

---

## Data Models

### Primary Entities

- **GameObject** (base): id, name, description, synonyms, flags (GameFlag set), children, parent_id
- **Item(GameObject)**: properties, clues — flags replace old `fixed: bool`
- **Door(GameObject)**: connects two locations, optional key/condition, shared via local_globals
- **NPC**: personality, clues, conversation_history, mood
- **Location(GameObject)**: exits, local_globals, npcs, visited; lifecycle hooks (on_enter, on_look, on_before/after_command)
- **Investigation**: case_id, discovered_clues, connections, progress

### Key Relationships
- Player has one current_location (Location)
- Location contains items (Item[]) and npcs (NPC[])
- Items and NPCs can have clues (ClueData[])
- Investigation tracks all discovered clues

---

## Configuration

### Required Environment Variables
- `ANTHROPIC_API_KEY`: Claude API key (sk-ant-...)

### Optional Environment Variables
- `OPENAI_API_KEY`: For OpenAI fallback (sk-...)
- `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR|NONE (default: INFO)

### Configuration Files
- `.env`: API keys and settings (not committed)
- `game_cards.yaml`: Available game scenarios
- `game_data/files/*.yaml`: Game content

---

## Current Status

**Version**: 0.2.0 (Development)

### Implemented
- Hybrid object model: `GameObject` base, `GameFlag` enum, `Door`, `GlobalRegistry`, `DoorRegistry`
- Location lifecycle hooks (`on_enter`, `on_look`, `on_before/after_command`)
- Handler files per location (`game_data/handlers/`) auto-loaded at startup
- Named exit navigation with aliases — no compass-only movement
- Shared door objects visible from two rooms via `local_globals`
- 6-step object resolver: inventory → room children → NPCs → GlobalRegistry → DoorRegistry → open containers
- `_handle_examine()` with AI enhancement
- `_handle_move()` with exit resolution, door lock checks, hook firing, visited tracking
- `_handle_inventory()` basic functionality
- AI command interpretation (natural language → structured actions)
- Database save functionality
- Configurable logging

### Incomplete/Placeholder
- `_handle_talk()` / `_handle_say()` — placeholder (NPC dialogue not integrated)
- Item take/drop mechanics
- Clue discovery triggers
- Load game (save works; load needs object reconstruction from JSON)

---

## Typical Use Cases

### Case 1: Investigate a Scene

**Goal**: Player examines objects to find clues

**Flow**:
1. Player types `examine the desk`
2. AI interprets → `{"action": "examine", "target": "desk"}`
3. Engine finds `office_desk` Item
4. Handler calls `item.examine(ai_enhancer, context)`
5. Returns atmospheric description + any clues

### Case 2: Interrogate NPC

**Goal**: Player questions NPC to reveal information

**Flow**:
1. Player types `ask jack about the victim`
2. AI interprets → `{"action": "ask", "target": "jack", "message": "about the victim"}`
3. Engine finds `jack_napier_barman` NPC
4. Handler calls `npc.answer_conversation()` (placeholder)
5. Returns personality-driven dialogue + revealed clues

---

## Limitations

- **NPC dialogue not integrated**: `_handle_talk()` is placeholder
- **No item pickup**: Take/drop mechanics missing
- **Single-player**: No concurrent multiplayer support
- **Load broken**: Save works, but load can't reconstruct objects

## Non-Intuitive Behaviors

- **Context caching**: GameContext is lazy-loaded and cached; call `_invalidate_context()` after state changes
- **Clue revelation**: Clues exist in data but discovery triggers aren't implemented
- **Fixed items**: Use `GameFlag.FIXED` (not `fixed: bool`) — set in YAML `flags:` list

---

## Notes for Claude Web

**Architectural discussions should consider**:
- The 4-stage pipeline is non-negotiable - don't propose bypassing it
- AI boundaries exist for game integrity - atmosphere yes, mechanics no
- YAML is the source of truth for game content

**Pending decisions**:
- How to implement clue discovery triggers (skill checks? automatic?)
- NPC conversation persistence model
- Item usage mechanics

**Areas for improvement**:
- Complete the handler methods (_handle_move, _handle_talk)
- Implement load game functionality
- Add clue connection logic to Investigation

---

## Notes for Claude Code

**Conventions**:
- Always use `.venv/bin/python`
- Set `PYTHONPATH=/data/PiesPlanos`
- Use `MockAIEnhancer` in tests to avoid API costs
- Commit message format: `feat:`, `fix:`, `docs:`, `refactor:`

**Areas requiring attention**:
- `src/utils/utils.py` - `load_player()` returns None (load not implemented)
- `src/engine.py` - `_handle_talk()` / `_handle_say()` still placeholder

**When contributing**:
- Follow the 4-stage pipeline for new commands
- Add handler methods to engine.py
- Create tests with MockAIEnhancer
- Never hardcode game content - use YAML
- New location logic goes in `game_data/handlers/<location_id>.py`

---

*Last updated: March 2026*
*Generated from: main branch*
