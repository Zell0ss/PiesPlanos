# Project: AI-Enhanced Detective Text Adventure Game

## Overview
this project is an AI-enhanced Investigation/Mystery text adventure game inspired by the GUMSHOE RPG system. The game combines classic parser-based gameplay with AI-enhanced natural language processing for immersive detective fiction experience.

# Claude Code Behavior Guidelines

## Response Style
- When I ask how to do something, **always consider alternative approaches** 
  If you know a better way, suggest it clearly with pros/cons
- Explain trade-offs between different solutions before implementing
- Ask clarifying questions about my use case before committing to one approach if your uncertainty is significant
- Present best practices alongside my requested solution

## Examples
- If I ask about config in settings.local.json, mention if AGENT.md would be better
- If I ask about one tool, suggest others if more appropriate
- If there's a simpler solution, present it first

# Claude Code Instructions for This Project

## Python Environment

### Virtual Environment (CRITICAL)
- **ALWAYS** use `.venv/bin/python` and `.venv/bin/pip`
- Activate before running commands: `source .venv/bin/activate`
- Never use system Python for this project

### Dependency Management
- All dependencies must be in `requirements.txt`
- After installing new packages, run: `pip freeze > requirements.txt`
- Check if package exists before installing

## Code Quality Standards

### Testing
- Write tests for new functions in `tests/` directory
- Run tests before committing: `pytest tests/`
- Aim for >80% code coverage

### Code Style
- Follow PEP 8 style guide
- Use type hints for function signatures
- Maximum line length: 88 characters (Black formatter default)
- Run `black .` and `ruff check .` before committing

### Documentation
- Add docstrings to all functions and classes (Google style)
- Update README.md when adding new features
- Keep inline comments minimal and meaningful

## File Organization
```
project/
├── .venv/          # Virtual environment (never commit)
├── src/            # Source code
├── tests/          # Test files (mirror src/ structure)
├── docs/           # Documentation
├── .gitignore      # Include .venv, __pycache__, *.pyc
└── requirements.txt
```

## Git Practices

### Before Committing
1. Run tests: `pytest`
2. Format code: `black . && ruff check --fix .`
3. Check git status: `git status`
4. Write meaningful commit messages in Semantic Commit Messages format

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

## Error Handling

- Use specific exceptions, not bare `except:`
- Log errors with context
- Fail fast: validate inputs early
- Include helpful error messages

## Security

- Never commit secrets, API keys, or passwords
- Use environment variables for sensitive data: `python-dotenv`
- Validate all user inputs
- Keep dependencies updated: `pip list --outdated`

## Performance Considerations

- Profile before optimizing: `python -m cProfile`
- Use list comprehensions over loops when appropriate
- Close files and connections properly (use context managers)
- Consider generators for large datasets

## Claude-Specific Instructions

### When Making Changes
1. **Ask about alternatives** if there might be a better approach
2. **Explain trade-offs** between different solutions
3. **Show examples** of the proposed changes
4. **Run tests** after modifications

### When Installing Packages
1. Check if already installed: `pip list | grep package-name`
2. Install in .venv: `.venv/bin/pip install package`
3. Update requirements: `pip freeze > requirements.txt`
4. Verify installation: `python -c "import package"`

### When Debugging
1. Check the full error traceback
2. Verify Python version: `python --version`
3. Check if .venv is activated: `which python`
4. List installed packages: `pip list`

## Project-Specific Rules

### 1. Virtual Environment Protocol
Always activate the virtual environment before running Python commands.

### 2. AI Enhancement Boundaries
AI enhances atmosphere but never alters game mechanics or predefined content.

**Rules:**
- Use ai_enhancer.enhance_description() for atmospheric text only
- Never let AI decide: clue discovery, item properties, NPC knowledge, exit availability
- AI can: rephrase descriptions, add sensory details, match noir/detective tone
- Game logic stays deterministic; AI adds immersion layer
- **Example**: AI enhances "You see a desk" → "The oak desk looms in the shadows, its surface cluttered with papers", but desk properties come from YAML

### 3. YAML Content Authority
All game content definitions live in YAML files - never hardcode in Python. If a new one or modification is needed, add it to its YAML.

### 4. Command Interpretation Flow
All player commands must follow the interpret → resolve → route → execute pipeline.

**Pipeline:**
1. **Interpret**: AI converts natural language to structured action JSON
2. **Resolve**: Map string references ("the desk") to actual game objects using context
3. **Route**: Direct to appropriate handler based on action type
4. **Execute**: Handler performs game logic and returns AI-enhanced response

Never bypass this flow - don't handle raw commands directly. This ensures:
- Consistent natural language support
- Proper object resolution
- Centralized context management
- AI enhancement opportunities


### API Keys and Environment Variables
- Use `.env` file (never commit it!)
- Load with: `from dotenv import load_dotenv; load_dotenv()`
- Access with: `os.getenv('API_KEY')`

**Required Environment Variables:**
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key (optional)

**Optional Environment Variables:**
- `LOG_LEVEL` - Controls logging verbosity (DEBUG, INFO, WARNING, ERROR, NONE)
  - Default: INFO
  - Recommended for playing: NONE (cleanest experience)
  - Recommended for development: DEBUG

### Database
- there is a local database to save game state. Its structure is described in `utils/utils.py`

### External Services
- we are using API connection to LLM services. They are described in `models/ai_enhancer.py`

## Common Commands Reference
```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Development
python src/main.py
pytest tests/
black .
ruff check .

# Dependencies
pip install package-name
pip freeze > requirements.txt
pip list --outdated
```

## Troubleshooting

### "Module not found" error
1. Check if .venv is activated: `which python`
2. Check if package installed: `pip list | grep package`
3. Reinstall if needed: `pip install package-name`

### Import errors
1. Verify file structure matches imports
2. Check for circular imports
3. Ensure `__init__.py` exists in packages

---

**Remember**: Always prefer explicit over implicit, simple over complex, and readable over clever.