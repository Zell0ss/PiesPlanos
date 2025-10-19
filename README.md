# Gumshoe-style RPG Investigation Game
## Project Overview
A Python-based text adventure game inspired by Gumshoe investigation RPG system. The game combines classic text adventure mechanics with AI-enhanced descriptions and persistent NPC interactions.

## 🎮 How to Play

### Quick Start
```bash
# Easy way - use the launcher script
./play.sh

# Or manually:
source .venv/bin/activate
export PYTHONPATH=/data/PiesPlanos
python main.py
```

### 🔧 Customizing Logging
Control how much information is displayed while playing by setting `LOG_LEVEL` in your `.env` file:
```bash
LOG_LEVEL=NONE    # Cleanest - no log messages (recommended for playing)
LOG_LEVEL=ERROR   # Only show errors
LOG_LEVEL=WARNING # Show warnings and errors
LOG_LEVEL=INFO    # Show API calls and info (default)
LOG_LEVEL=DEBUG   # Show everything (useful for debugging)
```

### Game Commands
The game uses natural language! You can type commands like:
- `examine the desk` - Look at objects, people, or locations
- `talk to the detective` - Start conversations with NPCs
- `ask librarian about the book` - Ask specific questions
- `look around` - Survey your surroundings
- `check inventory` - See what you're carrying
- `go north` or `enter the door` - Move between locations
- `help` - Show in-game help
- `save` - Save your progress
- `quit` - Exit the game

### Prerequisites
- Python 3.11+
- Virtual environment with dependencies installed (see `requirements.txt`)
- API key for Claude/OpenAI (set in `.env` file)

## Core Features
- Parser-based interface with AI-powered command interpretation
- Investigation/mystery focus (Gumshoe-style gameplay)
- AI-enhanced descriptions while respecting predefined parameters
- Persistent NPC memory across game sessions per player
- Simple GUI with room illustrations and NPC mood portraits
- Modular architecture for easy content extension

## Technical Stack
- Python with Tkinter for GUI
- Claude/OpenAI API for AI enhancement
- YAML for the game files that describe locations, NPCs, items,...
- JSON/SQLite for persistence between game sessions
- Modular class-based architecture

## Key Classes Architecture
- GameEngine: Main loop, command parsing, AI integration
- Player: Stats, inventory, investigation progress, session management
- Location: Description, connections, items, NPCs, illustrations
- NPC: Personality, clues, conversation history, mood states (5 portraits)
- Item: Description, properties, investigation value
- Investigation: Clue tracking, connections, case progress
- AIEnhancer: API calls, context management

## Design Principles
- Conservative AI enhancement (respects predefined boundaries)
- Full conversation history with AI summarization
- Multiple player support with separate save files (not at the same time!)
- Extensible content system for new adventures
- Investigation mechanics over combat/stats