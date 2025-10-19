# Setup Guide

## First Time Setup

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
```

### 2. Activate Virtual Environment
```bash
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Create a `.env` file in the project root with your API keys:

```bash
# .env file
ANTHROPIC_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional
```

**Get API Keys:**
- Claude (Anthropic): https://console.anthropic.com/
- OpenAI (optional): https://platform.openai.com/

### 5. Verify Setup
```bash
# Run tests to verify everything works
pytest tests/

# Or run the test app
export PYTHONPATH=/data/PiesPlanos
python tests/test_app.py
```

## Running the Game

### Option 1: Use the Launcher Script (Easiest)
```bash
./play.sh
```

### Option 2: Run Manually
```bash
source .venv/bin/activate
export PYTHONPATH=/data/PiesPlanos
python main.py
```

## Troubleshooting

### "Module not found" errors
Make sure you've set the PYTHONPATH:
```bash
export PYTHONPATH=/data/PiesPlanos
```

Or add it to your shell profile to make it permanent.

### "API key required" errors
Make sure your `.env` file exists and contains valid API keys.

### Import errors
1. Verify virtual environment is activated: `which python` should show `.venv/bin/python`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check that all `__init__.py` files exist in `src/` subdirectories

## Development

### Running Tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Code Formatting
```bash
black .
ruff check .
```

### Project Structure
```
PiesPlanos/
├── main.py              # Interactive game launcher
├── play.sh              # Convenience launcher script
├── src/                 # Source code
│   ├── engine.py        # Main game engine
│   ├── models/          # Game models and AI
│   ├── chains/          # LangChain agents
│   └── utils/           # Utility functions
├── tests/               # Test files
├── game_data/           # Game content (YAML)
├── docs/                # Documentation
└── .env                 # API keys (create this!)
```

## Need Help?

Check the main README.md for more information, or refer to AGENT.md for development guidelines.
