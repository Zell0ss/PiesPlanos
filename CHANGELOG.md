# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-11

### Added
- **Hybrid object model**: `GameObject` base class inherited by `Item`, `Door`, `Location`
- **`GameFlag` enum** (15 flags): replaces `fixed: bool` and ad-hoc booleans
- **`Door` class**: single shared object visible from two locations via `local_globals`
- **`DoorRegistry`**: manages all door objects, lookup by id or synonym
- **`GlobalRegistry`**: global objects (visible everywhere) + local-globals (visible in declared rooms only)
- **Location lifecycle hooks**: `on_enter`, `on_look`, `on_before_command`, `on_after_command`
- **Handler files** (`game_data/handlers/*.py`): Python logic per location, auto-loaded at startup
- **Named exit navigation**: exits have `name` + `aliases`, no compass-only movement
- **6-step object resolver** (`_resolve_object`): inventory → room children → NPCs → GlobalRegistry → DoorRegistry → open containers
- `doors.yaml` — door definitions
- `globals.yaml` — global and local-global ambient objects
- `jazz_club.py` handler — activates blood trail on first visit

### Changed
- `_handle_move()`: rewritten with `find_exit()`, door lock checks, `on_enter` hook, `visited` tracking
- `_handle_examine()`: uses `_resolve_object()`, handles pre-resolved objects
- `locations.yaml`: migrated `items:` → `children:`, added `synonyms`, `local_globals`, `flags`
- `items.yaml`: removed door items (moved to `doors.yaml`), added `flags`, `synonyms`, `children`
- `process_command()`: removed legacy pre-resolution block — handlers own their resolution

### Fixed
- `Location.base_description` type annotation (`StopAsyncIteration` → `str`, via `GameObject` inheritance)
- `_handle_examine` crash when `process_command` pre-resolved target to an object
- `_handle_move` crash on conditioned exits (`game_state.get()` on a string)
- `location.visited` never set to `True` after entering
- Doors in `local_globals` not resolvable via object resolver

## [0.1.0] - 2026-01-XX

### Added
- Initial game engine with four-stage command pipeline (Interpret→Resolve→Route→Execute)
- Core game models (Player, Item, NPC, Location, Investigation)
- `ClaudeEnhancer` for AI-powered command interpretation and atmosphere
- `MockAIEnhancer` for testing without API calls
- YAML-based game content system
- SQLite persistence for player saves and NPC conversation history
- "The Invisible Cadaver" scenario: 5 locations, 18 items, 2 NPCs
- Natural language command processing
- AI-enhanced atmospheric descriptions
- `_handle_examine()` implementation
- `_handle_inventory()` implementation
- Configurable `LOG_LEVEL` (DEBUG|INFO|WARNING|ERROR|NONE)
- Interactive launcher script (`play.sh`)

### Incomplete
- `_handle_talk()` / `_handle_say()` — placeholder
- Item take/drop mechanics
- Load game functionality
- Clue discovery triggers

---

*For architecture details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).*
