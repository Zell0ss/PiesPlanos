# Pies Planos - Quick Start Guide

Get playing in 5 minutes.

---

## Step 1: Clone and Enter Directory

```bash
git clone <repository-url>
cd PiesPlanos
```

**Expected**: You're in the project root with `main.py` visible.

---

## Step 2: Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Expected**: Virtual environment created and activated. Prompt shows `(.venv)`.

---

## Step 3: Configure API Key

```bash
cp .env.example .env
```

Edit `.env` and add your Claude API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
LOG_LEVEL=NONE
```

**Expected**: `.env` file exists with your API key.

---

## Step 4: Launch the Game

```bash
./play.sh
```

Or manually:
```bash
export PYTHONPATH=/data/PiesPlanos
python main.py
```

**Expected**: Game banner appears, prompts for game selection.

---

## Step 5: Play!

1. Select a case (e.g., "The Invisible Cadaver")
2. Enter your detective name
3. Start investigating with natural language commands:

```
> look around
> examine the piano
> talk to the barman
> go to the backstage
```

**Expected**: AI-enhanced descriptions of the noir detective world.

---

## Quick Reference

| Command | What it does |
|---------|--------------|
| `examine <object>` | Look at something closely |
| `talk to <person>` | Start conversation with NPC |
| `ask <person> about <topic>` | Ask specific questions |
| `go <direction/place>` | Move to another location |
| `inventory` | Check what you're carrying |
| `save` | Save your progress |
| `help` | Show all commands |
| `quit` | Exit game |

---

## Troubleshooting

### "Module not found" error
```bash
export PYTHONPATH=/data/PiesPlanos
```

### "API key" error
Check `.env` file has valid `ANTHROPIC_API_KEY`.

### Too much log output
Set `LOG_LEVEL=NONE` in `.env`.

---

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
- Check [BRIEFING.md](BRIEFING.md) for project overview
- Explore `game_data/files/` to see game content
- Run tests: `pytest tests/ -v`

---

*Happy investigating, detective.*
