# Pies Planos - GUMSHOE-style Detective Text Adventure

> A noir detective text adventure game using AI (Claude) to enhance natural language command processing, generate atmospheric descriptions, and power intelligent NPC conversations.

## Quick Start

```bash
./play.sh
```

Or manually:
```bash
source .venv/bin/activate
export PYTHONPATH=/data/PiesPlanos
python main.py
```

## Features

- **Natural Language Commands** - Type `examine the dusty desk` instead of `EXAMINE DESK`
- **AI-Enhanced Descriptions** - Claude adds noir atmosphere while respecting game mechanics
- **Intelligent NPCs** - Characters with personalities, moods, and conversation memory
- **Investigation Mechanics** - GUMSHOE-style clue discovery and case progression
- **Persistent Saves** - SQLite database stores player progress and NPC conversations
- **Modular Content** - YAML-based game data for easy scenario creation

## Game Commands

| Command | Example | Description |
|---------|---------|-------------|
| `examine <target>` | `examine the desk` | Look at objects, NPCs, locations |
| `talk to <person>` | `talk to the barman` | Start NPC conversation |
| `ask <person> about <topic>` | `ask jack about the victim` | Ask specific questions |
| `go <direction/exit>` | `go north`, `enter the club` | Move between locations |
| `inventory` | `check inventory` | Show carried items |
| `look around` | `look around` | Survey current location |
| `save` | `save` | Save game progress |
| `help` | `help` | Show in-game help |
| `quit` | `quit` | Exit game |

## Requirements

- Python 3.11+
- Anthropic API key (Claude)
- Optional: OpenAI API key

## Installation

```bash
# Clone and setup
git clone <repo-url>
cd PiesPlanos

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
```

## Configuration

Set `LOG_LEVEL` in `.env` to control output verbosity:

| Level | Use Case |
|-------|----------|
| `NONE` | Clean gameplay (recommended for playing) |
| `ERROR` | Errors only |
| `WARNING` | Warnings and errors |
| `INFO` | API calls and info (default) |
| `DEBUG` | Full debug output (development) |

## Project Structure

```
PiesPlanos/
├── main.py              # Game launcher
├── play.sh              # Quick start script
├── src/
│   ├── engine.py        # Command processing pipeline
│   ├── models/          # GameObject, Item, Door, NPC, Location, registries
│   ├── chains/          # LangChain AI integration
│   └── utils/           # Persistence, logging
├── game_data/
│   ├── files/           # YAML game content
│   └── handlers/        # Python location hooks
└── tests/               # Pytest test suite
```

## Documentation

- [BRIEFING.md](docs/BRIEFING.md) - Executive summary for developers and AI
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical architecture and design decisions
- [QUICKSTART.md](docs/QUICKSTART.md) - 5-step getting started guide
- [CLAUDE.md](CLAUDE.md) - AI assistant instructions

## Tech Stack

- **Python 3.11+** - Core language
- **LangChain + Claude API** - AI command interpretation and enhancement
- **YAML** - Game content definition
- **SQLite** - Save game persistence
- **Pytest** - Testing framework

## License

[Add license here]

---

*A detective noir adventure where every conversation matters and clues hide in the shadows.*
