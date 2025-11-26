# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Response Style Guidelines

When working with me on this project:
- **Always consider alternative approaches** - if you know a better way, suggest it clearly with pros/cons

- **Explain trade-offs** between different solutions before implementing

- **Ask clarifying questions** about my use case before committing to an approach if your uncertainty is significant

- **Present best practices** alongside my requested solution

- **Suggest simpler solutions** when appropriate

- **Direct and focused**: Provide technical solutions with clear reasoning. Less philosophical meandering, more actionable implementation.

- **Critical assumptions upfront**: Always list critical assumptions at the beginning or end that could drastically change the answer. If an assumption is wrong, the solution might be completely different.

- **Show thinking process**: Make your reasoning visible so I can follow your logic and catch if you're going down the wrong path.

- **Structured when needed**: Use clear formatting for complex technical explanations, but avoid over-formatting simple answers.

## Technical Context

**Current tech stack and interests:**
- Python development (APIs, data analysis, automation, AI integration)
- LangChain and ChromaDB for RAG systems
- MCP server development
- Local LLM deployment and optimization
- Database administration (SQL)
- SSH configuration and Linux system administration
- VSCode with Claude Code integration
- Project management and IT sourcing operations

**Work environment:**
- Managing IT sourcing across Spain, France, Portugal
- Focus on efficiency, risk reduction, strategic decision-making
- Background in Cloud Automation and RPA coordination

## Approach to Technical Questions

1. Lead with the solution or direct answer
2. Explain the reasoning clearly
3. List critical assumptions that could change the approach
4. Provide implementation details when relevant
5. Consider edge cases and potential issues

## Blurred Lines (Creative + Technical)

For questions that mix creative and technical aspects (e.g., "What's the best architecture for this text adventure game?"):
- Challenge the architecture approach itself (creative framing)
- Then provide clean technical implementation once direction is clear

## Language
- Spanish native, comfortable with English
- If uncertain about response, ask clarifying questions
- If critical assumptions were made that could drastically change the answer, mention them at the end


## Project Overview

This is a GUMSHOE-style detective text adventure game that uses AI (Claude/OpenAI) to enhance natural language command processing, generate atmospheric descriptions, and power intelligent NPC conversations. The game features investigation mechanics where players examine objects, talk to NPCs, and solve mysteries through conversational commands.

## Development Commands

### Setup
```bash
# First time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env file with API keys
# Required: ANTHROPIC_API_KEY
# Optional: OPENAI_API_KEY, LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|NONE)
```

### Running the Game
```bash
# Easiest way - use the launcher script
./play.sh

# Manual way
source .venv/bin/activate
export PYTHONPATH=/data/PiesPlanos
python main.py
```

### Testing
```bash
source .venv/bin/activate
pytest tests/ -v                  # Run all tests
pytest tests/test_app.py -v       # Run specific test file
```

### Code Quality
```bash
black .                           # Format code
ruff check .                      # Lint code
ruff check --fix .                # Fix linting issues
```

## Architecture

### Core Pipeline: Command Processing Flow

**CRITICAL**: All player commands MUST follow this four-stage pipeline:

1. **Interpret** (AI): Natural language → Structured JSON action
   - Input: Raw command like "examine the dusty desk"
   - Output: `{"action": "examine", "target": "desk", "confidence": 0.9}`

2. **Resolve** (GameEngine): String references → Game objects
   - Maps "desk" to actual Item/NPC/Location object using current context
   - Uses fuzzy matching for "the dusty desk" → `items["old_desk"]`

3. **Route** (GameEngine): Action type → Handler method
   - `"examine"` → `_handle_examine()`
   - `"talk"` → `_handle_talk()`
   - `"move"` → `_handle_move()`

4. **Execute** (Handler): Game logic + AI enhancement → Response
   - Performs deterministic game mechanics (clue discovery, state changes)
   - Enhances response with atmospheric AI-generated text
   - Returns final narrative output to player

**Never bypass this flow** - handling raw commands directly breaks natural language support and context management.

### Module Structure

```
src/
├── engine.py                     # Main game orchestrator (GameEngine class)
│                                 # - Command processing pipeline
│                                 # - YAML content loading
│                                 # - Game state management
│
├── models/
│   ├── models.py                 # Core game entities:
│   │                             #   Player, Item, NPC, Location, Investigation
│   ├── core_data.py              # Data structures:
│   │                             #   ClueData, ConversationEntry, Exit
│   ├── ai_enhancer.py            # AI integration layer:
│   │                             #   AIEnhancer (interface)
│   │                             #   ClaudeEnhancer (primary implementation)
│   │                             #   MockAIEnhancer (testing)
│   └── game_context.py           # Context building for AI calls
│
├── chains/
│   ├── command_chains.py         # LangChain specialized chains
│   └── agent.py                  # AI agent setup (legacy/experimental)
│
└── utils/
    ├── utils.py                  # PersistenceManager (SQLite save/load)
    └── logging_config.py         # Logging configuration
```

### AI Enhancement Boundaries

**CRITICAL RULE**: AI enhances atmosphere but NEVER alters game mechanics.

AI **CAN**:
- Rephrase descriptions with atmospheric details
- Add sensory information (smells, sounds, lighting)
- Match noir/detective fiction tone
- Generate personality-based NPC dialogue

AI **CANNOT**:
- Decide if clues are discovered (determined by YAML + game logic)
- Change item properties or NPC knowledge
- Invent new exits or locations
- Alter game state or mechanics

**Example**:
- YAML: `"You see an oak desk"`
- AI Enhancement: `"The oak desk looms in the shadows, its surface cluttered with yellowed papers"`
- Desk properties (clues, fixed status, etc.) come from YAML, NOT from AI

Use `ai_enhancer.enhance_description()` for atmospheric text only.

### Content Authority: YAML Files

All game content lives in `game_data/files/`:
- `locations.yaml` - Rooms, areas, descriptions, exits
- `items.yaml` - Objects, clues, properties
- `npcs.yaml` - Characters, personalities, conversation prompts
- `clues.yaml` - Investigation clues and connections
- `connectors.yaml` - (Purpose TBD)

**Never hardcode game content in Python** - add/modify YAML files instead.

### Database Persistence

SQLite database (`game_saves.db`) stores:
- **player_saves**: Player state (serialized as JSON)
- **npc_conversations**: Conversation history by player/NPC pair

Database structure is defined in `src/utils/utils.py`.

**Note**: Save functionality works, but load functionality needs completion (object reconstruction from JSON).

## Project-Specific Rules

### Virtual Environment
Always use `.venv/bin/python` and `.venv/bin/pip`. Never use system Python.

### Python Path
Set `PYTHONPATH=/data/PiesPlanos` when running commands to enable absolute imports.

### Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO              # DEBUG|INFO|WARNING|ERROR|NONE
                            # Default: INFO
                            # For development: DEBUG
                            # For playing: NONE
```

Load with: `from dotenv import load_dotenv; load_dotenv()`

### Dependencies
After installing new packages:
```bash
pip install package-name
pip freeze > requirements.txt
```

### Testing Without API Calls
Use `MockAIEnhancer` instead of `ClaudeEnhancer` in tests to avoid API costs and enable deterministic testing.

### Code Quality Standards

**Testing Requirements:**
- Write tests for new functions in `tests/` directory
- Run tests before committing: `pytest tests/`
- Aim for >80% code coverage
- Mirror `src/` structure in `tests/` directory

**Documentation:**
- Add docstrings to all functions and classes (Google style)
- Update README.md when adding new features
- Keep inline comments minimal and meaningful

**Error Handling:**
- Use specific exceptions, not bare `except:`
- Log errors with context
- Fail fast: validate inputs early
- Include helpful error messages

**Performance Considerations:**
- Profile before optimizing: `python -m cProfile`
- Use list comprehensions over loops when appropriate
- Close files and connections properly (use context managers)
- Consider generators for large datasets

## Known Issues & Implementation Status

### Completed
- Core class architecture (Player, Item, NPC, Location, Investigation)
- AI command interpretation (natural language → structured actions)
- YAML content loading system
- Context building for AI enhancement
- `_handle_examine()` - fully implemented with AI enhancement
- `_handle_inventory()` - basic functionality
- Database schema and save functionality

### Incomplete/Placeholder
- `_handle_move()` - returns placeholder text (needs exit validation, location transitions)
- `_handle_talk()` / `_handle_say()` - returns placeholder text (needs NPC dialogue integration)
- Item take/drop mechanics
- Clue discovery triggers and integration
- Load game functionality (needs object reconstruction from JSON)
- `Location.base_description` has wrong type annotation (currently `StopAsyncIteration` instead of `str`)

## Code Style

- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 88 characters (Black default)
- Docstrings: Google style
- Run `black .` and `ruff check .` before committing

## Git Practices

### Before Committing
1. Run tests: `pytest tests/`
2. Format code: `black . && ruff check --fix .`
3. Check git status: `git status`
4. Write meaningful commit messages in Semantic Commit Messages format

### Semantic Commit Messages
- `feat: add conversation system`
- `fix: resolve inventory command crash`
- `docs: update README with new commands`
- `refactor: simplify AI context building`

### .gitignore Must Include
- `.venv/`
- `__pycache__/`
- `*.pyc`
- `*.pyo`
- `.pytest_cache/`
- `.coverage`
- `*.egg-info/`
- `.claude`
- `.env`

### Security Reminders
- Never commit secrets, API keys, or passwords
- Use environment variables for sensitive data
- Validate all user inputs
- Keep dependencies updated: `pip list --outdated`

## Working with Packages

### When Installing Packages
1. Check if already installed: `pip list | grep package-name`
2. Install in .venv: `.venv/bin/pip install package-name`
3. Update requirements: `pip freeze > requirements.txt`
4. Verify installation: `python -c "import package"`

### When Making Changes
1. **Ask about alternatives** if there might be a better approach
2. **Explain trade-offs** between different solutions
3. **Show examples** of the proposed changes
4. **Run tests** after modifications

## Troubleshooting

### Module not found errors
```bash
# Verify PYTHONPATH is set
export PYTHONPATH=/data/PiesPlanos

# Verify virtual environment is active
which python  # Should show .venv/bin/python

# Check if package installed
pip list | grep package-name

# Reinstall if needed
pip install package-name
```

### API key errors
Ensure `.env` file exists with valid API keys.

### Import errors
1. Verify file structure matches imports
2. Check for circular imports
3. Ensure `__init__.py` files exist in all `src/` subdirectories

### Debugging Checklist
1. Check the full error traceback
2. Verify Python version: `python --version`
3. Check if .venv is activated: `which python`
4. List installed packages: `pip list`

---

**Remember**: Always prefer explicit over implicit, simple over complex, and readable over clever.
