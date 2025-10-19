# **PIESPLANOS - AI-Enhanced GUMSHOE Detective Text Adventure**

## **Project Type**
Investigation/Mystery text adventure game inspired by the GUMSHOE RPG system, combining classic parser-based gameplay with AI-enhanced natural language processing for immersive detective fiction experience.

## **Technology Stack**
- **Language**: Python 3.11.0rc1 (in `.venv`)
- **AI Integration**: Anthropic Claude API (primary), OpenAI API (secondary)
- **LangChain**: Command interpretation and NPC dialogue generation
- **Persistence**: SQLite database for save games
- **UI**: Pygame/Pygame-GUI for visual interface (planned)
- **Data**: YAML for game content definition
- **Testing**: pytest, mypy for type checking

## **Core Architecture**

### **Main Components**
1. **GameEngine** (`engine.py`) - Main orchestrator
   - Manages game state (menu, playing, paused, ended)
   - Loads YAML content (locations, items, NPCs, clues)
   - Processes natural language commands via AI
   - Routes actions to specialized handlers
   - Coordinates save/load operations

2. **Models** (`models/models.py`)
   - **Player**: Stats, inventory, investigation progress, session management
   - **Location**: Rooms/areas with exits, items, NPCs, descriptions
   - **Item**: Interactive objects, clues, examination states
   - **NPC**: Personality-driven characters with mood states and conversation history
   - **Investigation**: Case management, clue tracking, progress calculation

3. **AI Enhancer** (`models/ai_enhancer.py`)
   - **ClaudeEnhancer**: Primary AI implementation using Anthropic Claude
   - Interprets natural language commands → structured actions (JSON)
   - Enhances descriptions with atmospheric noir/detective fiction styling
   - Generates personality-based NPC responses
   - Manages conversation history and summarization

4. **Game Context** (`models/game_context.py`)
   - Caches current game state (location, items, NPCs, exits, progress)
   - Provides structured context for AI API calls
   - Invalidates when game state changes

5. **Persistence** (`utils/utils.py`)
   - SQLite-based save/load system
   - Player state serialization
   - NPC conversation history storage

## **Game Flow**

### **Command Processing Pipeline**
```
Player Input (natural language)
    ↓
GameContext builds current state
    ↓
AI interprets command → structured action
    ↓
Resolve string references to game objects
    ↓
Route to action handler
    ↓
Execute game logic
    ↓
AI-enhanced response returned
```

### **Supported Actions**
- **examine**: Investigate objects/locations (✅ implemented)
- **talk/say/ask**: Converse with NPCs (⚠️ placeholder)
- **move**: Navigate between locations (⚠️ placeholder)
- **inventory**: Check carried items (✅ basic implementation)
- **use**: Item interactions (planned)
- **take/drop**: Inventory management (planned)

## **Content Structure**

### **YAML Data Files** (`game_data/files/`)
- `locations.yaml` - Rooms with descriptions, exits, items, NPCs
- `items.yaml` - Interactive objects with properties
- `npcs.yaml` - Characters with personalities and clues
- `clues.yaml` - Investigation evidence and revelations
- `connectors.yaml` - Doors/barriers between locations

### **Game Scenarios** (`game_cards.yaml`)
- Multiple cases/investigations
- Currently: "The Invisible Cadaver" (jazz club murder) and "The Missing Book"

## **Current Implementation Status**

### **✅ Completed**
- Core class architecture with dataclasses
- AI command interpretation system (natural language → actions)
- YAML content loading and parsing
- GameContext caching system
- AI-enhanced examination system
- Basic inventory display
- SQLite persistence schema
- NPC personality and mood system design

### **⚠️ Partially Implemented**
- **Movement handler**: Returns placeholder, needs full navigation logic
- **Conversation handler**: Returns placeholder, needs NPC dialogue integration
- **Persistence load**: Save works, load needs object reconstruction
- **Item interactions**: Examination works, usage mechanics incomplete
- **Clue discovery**: Data structures exist, trigger mechanics missing

### **❌ Missing/Needed**
1. **Critical gameplay mechanics**:
   - Complete movement with exit validation
   - NPC conversation with AI-generated responses
   - Item take/drop/use mechanics
   - Clue revelation triggers
   - Win/lose conditions

2. **Save/load completion**:
   - Object reconstruction from JSON in load_player()
   - Save state validation

3. **Game polish**:
   - Skill check system
   - Time/consequence mechanics
   - GUI implementation (currently CLI only)

## **Key Design Principles**

1. **Conservative AI Enhancement**: AI adds atmosphere but respects predefined game boundaries and mechanics
2. **Persistent NPC Memory**: Conversations saved per player, maintaining continuity
3. **Investigation-First**: Focus on clue discovery and deduction over combat/stats
4. **Modular Content**: Easy to add new cases, locations, NPCs via YAML
5. **Natural Language Interface**: Players use conversational commands instead of strict parser syntax

## **Development Context**

### **Git Status**
- Modified: `engine.py`, `models/models.py`
- Untracked: `command_graph.md`, `documentation/`, `models/game_context.py`, `test_game_context.py`
- Main branch, no remote set

### **Working in Virtual Environment**
- Always prefix Python commands with: `source .venv/bin/activate &&`
- Python version in venv: 3.11.0rc1
- All dependencies installed (see `requirements.txt`)

## **Common Operations**

### **Running the Game**
```bash
source .venv/bin/activate && python engine.py
```

### **Testing**
```bash
source .venv/bin/activate && pytest test_game_context.py
```

### **Type Checking**
```bash
source .venv/bin/activate && mypy models/
```

## **Important Notes for AI Agents**

1. **Always use the venv**: Prefix commands with `source .venv/bin/activate &&`

2. **Known Issues**:
   - Type annotation bug in `Location.base_description` (may be incorrect type)
   - Movement and conversation handlers need implementation
   - Load game functionality incomplete

3. **AI API Keys**: Stored in `.env` file (not tracked in git)

4. **Context Management**:
   - GameContext caches state for performance
   - Must invalidate after state-changing operations
   - Used for all AI API calls

5. **Game Content**:
   - Located in `game_data/files/`
   - Defined in YAML format
   - Loaded at game start via `load_game_content()`

6. **Development Philosophy**:
   - This is defensive security work (game development)
   - AI is used for enhancement, not core game logic
   - Focus on creating immersive detective fiction experience

## **Priority Development Areas**

1. **Immediate**: Complete movement and conversation handlers
2. **Short-term**: Implement item interaction and clue discovery
3. **Medium-term**: GUI development with Pygame
4. **Long-term**: Additional game scenarios and content expansion
