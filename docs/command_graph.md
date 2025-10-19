# Command Processing Flow

This document describes the flow of command processing in the PiesPlanos text adventure game engine.

## Example: "examine desk"

The following Mermaid sequence diagram illustrates how the command "examine desk" flows through the system:

```mermaid
sequenceDiagram
    actor Player
    participant Engine as GameEngine
    participant AIEnhancer as ClaudeEnhancer
    participant Claude as Claude API
    participant Context as Game Context

    Player->>Engine: "examine desk"

    Note over Engine: Check game state
    Engine->>Engine: Verify game is "playing"

    Note over Engine: Build context
    Engine->>Context: Get current location
    Context-->>Engine: Location object
    Engine->>Context: Get available items
    Context-->>Engine: Items dict (including "desk")
    Engine->>Context: Get exits
    Context-->>Engine: Exits dict
    Engine->>Context: Get inventory
    Context-->>Engine: Player inventory list

    Note over Engine: Interpret command with AI
    Engine->>AIEnhancer: interpret_command("examine desk", context)
    AIEnhancer->>Claude: SystemMessage + HumanMessage<br/>(command + context)
    Note over Claude: Parse command into structured action<br/>considering available objects,<br/>people, and exits
    Claude-->>AIEnhancer: JSON: {action: "examine",<br/>target: "desk",<br/>confidence: 0.95}
    AIEnhancer-->>Engine: interpretation dict

    Note over Engine: Resolve target reference
    Engine->>Engine: Match "desk" to actual Item object
    Engine->>Engine: interpretation["target"] = Item("desk")

    Note over Engine: Route to handler
    Engine->>Engine: action == "examine"<br/>→ _handle_examine()

    Note over Engine: Handle examine action
    Engine->>Engine: _get_context() for enhanced description
    Engine->>AIEnhancer: enhance_examine(Item("desk"), context)
    AIEnhancer->>Claude: SystemMessage + HumanMessage<br/>(target description + context)
    Note over Claude: Enhance base description<br/>with atmospheric details,<br/>mood, and sensory elements
    Claude-->>AIEnhancer: Enhanced description text
    AIEnhancer-->>Engine: "The desk is made of dark oak...<br/>A thin layer of dust..."

    Engine-->>Player: Enhanced description displayed
```

## Command Processing Steps

1. **Input Reception** (`engine.py:88-91`)
   - Player enters command
   - GameEngine validates game state is "playing"

2. **Context Building** (`engine.py:93-97`)
   - Retrieves current location
   - Gathers available items in location
   - Collects exit information
   - Gets player inventory
   - Packages context via `_get_context()`

3. **AI Command Interpretation** (`models/ai_enhancer.py:182-250`)
   - `ClaudeEnhancer.interpret_command()` is called
   - Sends command + context to Claude API
   - Claude parses natural language into structured action
   - Returns JSON with: action, target, recipient (optional), message (optional), confidence

4. **Target Resolution** (`engine.py:104-121`)
   - Maps string target names to actual game objects
   - Checks items, exits, NPCs, and location
   - Updates interpretation dict with object references

5. **Action Routing** (`engine.py:123-137`)
   - Routes to appropriate handler based on action type
   - Supported actions: examine, say, ask, talk, move, inventory

6. **Examine Handler** (`engine.py:139-144`)
   - Calls `ai_enhancer.enhance_examine()` with target and context
   - AI enhances base description with atmospheric details
   - Returns enhanced description to player

## Key Components

- **GameEngine** (`engine.py`): Main orchestrator
- **ClaudeEnhancer** (`models/ai_enhancer.py`): AI enhancement service
- **Context**: Location, items, exits, inventory, investigation progress
- **Item/Location/NPC Objects** (`models/models.py`): Game entities with base descriptions

## AI Enhancement Points

1. **Command Interpretation**: Natural language → structured action
2. **Description Enhancement**: Base description → atmospheric narrative
3. **NPC Responses**: Personality-driven dialogue generation
4. **Action Results**: Enhanced action outcome descriptions
