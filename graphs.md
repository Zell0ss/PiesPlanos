# Architecture and Design Diagrams

## Architecture/Component Diagram

```mermaid
graph TB
    subgraph "Game Engine Layer"
        GE[GameEngine]
        PC[Process Command]
        GS[Game State Manager]
    end

    subgraph "AI Enhancement Layer"
        AIE[AIEnhancer Interface]
        CE[ClaudeEnhancer]
        OE[OpenAIEnhancer]
        ME[MockEnhancer]
    end

    subgraph "Model Layer"
        Player[Player]
        Location[Location]
        Item[Item]
        NPC[NPC]
        Investigation[Investigation]
        ClueData[ClueData]
        ConversationEntry[ConversationEntry]
        Exit[Exit]
    end

    subgraph "Persistence Layer"
        PM[PersistenceManager]
        DB[(SQLite Database)]
    end

    subgraph "Chain Layer"
        LC[LookerChain]
        TC[TalkerChain]
        AC[ActionChain]
    end

    subgraph "External Data"
        YAML[YAML Content Files]
    end

    GE --> AIE
    GE --> PM
    GE --> Player
    GE --> Location
    GE --> Item
    GE --> NPC
    GE --> YAML

    AIE <|-- CE
    AIE <|-- OE
    AIE <|-- ME

    CE --> LC
    CE --> TC
    CE --> AC

    Player --> Investigation
    Player --> Item
    Location --> Item
    Location --> NPC
    Location --> Exit
    Investigation --> ClueData
    NPC --> ConversationEntry
    NPC --> ClueData
    Item --> ClueData

    PM --> DB
    Player --> PM

    style GE fill:#4CAF50
    style AIE fill:#2196F3
    style PM fill:#FF9800
    style Player fill:#9C27B0
```

## Call Flow/Sequence Diagram - Command Processing

```mermaid
sequenceDiagram
    participant U as User
    participant GE as GameEngine
    participant AIE as ClaudeEnhancer
    participant L as Location
    participant I as Item
    participant N as NPC
    participant PM as PersistenceManager

    U->>GE: process_command("examine desk")
    GE->>GE: _get_context()
    GE->>L: Get current location
    L-->>GE: Location data
    GE->>AIE: interpret_command(command, context)
    AIE->>AIE: Parse natural language
    AIE-->>GE: {action: "examine", target: "desk"}

    alt Target is Item
        GE->>I: Get item details
        I-->>GE: Item data
        GE->>AIE: enhance_examine(item, context)
        AIE-->>GE: Enhanced description
    else Target is NPC
        GE->>N: Get NPC details
        N-->>GE: NPC data
        GE->>AIE: enhance_description(npc, context)
        AIE-->>GE: Enhanced description
    else Target is Location
        GE->>L: Get location details
        L-->>GE: Location data
        GE->>AIE: enhance_description(location, context)
        AIE-->>GE: Enhanced description
    end

    GE->>PM: save_player(current_player)
    PM-->>GE: Success
    GE-->>U: Response text
```

## Call Flow/Sequence Diagram - NPC Conversation

```mermaid
sequenceDiagram
    participant U as User
    participant GE as GameEngine
    participant AIE as ClaudeEnhancer
    participant N as NPC
    participant CE as ConversationEntry
    participant C as ClueData

    U->>GE: process_command("ask bartender about murder")
    GE->>AIE: interpret_command(command, context)
    AIE-->>GE: {action: "ask", target: "bartender", message: "about murder"}

    GE->>N: Get NPC data
    N-->>GE: NPC personality, mood, history

    GE->>AIE: generate_npc_response(npc_data, history, input, must_include)
    AIE->>AIE: Analyze personality & mood
    AIE->>AIE: Review conversation history
    AIE->>AIE: Generate contextual response
    AIE-->>GE: NPC response text

    GE->>N: answer_conversation(player_input, response)
    N->>CE: Create new ConversationEntry
    N->>N: Update relationship_level
    N->>N: Update current_mood

    opt Clue Revealed
        N->>C: reveal_clue(clue_id)
        C-->>N: ClueData
        N-->>GE: Clue revealed
    end

    GE-->>U: NPC response with clue
```

## Call Flow/Sequence Diagram - Game Initialization

```mermaid
sequenceDiagram
    participant U as User
    participant GE as GameEngine
    participant YAML as YAML Files
    participant P as Player
    participant I as Investigation
    participant L as Location

    U->>GE: start_new_game(player_name, case_id, game_data)

    GE->>P: Create new Player
    P-->>GE: Player instance

    GE->>YAML: load_game_content(content_path)
    YAML-->>GE: clues.yaml
    YAML-->>GE: items.yaml
    YAML-->>GE: npcs.yaml
    YAML-->>GE: locations.yaml

    GE->>GE: Parse YAML into objects
    GE->>GE: Store in dictionaries

    GE->>I: Create Investigation(case_id, name, description)
    I-->>GE: Investigation instance

    GE->>P: Set current_investigation
    GE->>P: Set current_location

    GE->>L: Get initial location
    L-->>GE: Starting location data

    GE->>GE: game_state = "playing"
    GE-->>U: Game ready
```

## Class Diagram

```mermaid
classDiagram
    class GameEngine {
        -ClaudeEnhancer ai_enhancer
        -PersistenceManager persistence
        -Player current_player
        -Dict~str,Location~ locations
        -Dict~str,ClueData~ clues
        -Dict~str,Item~ items
        -Dict~str,NPC~ npcs
        -str game_state
        +__init__()
        +load_game_content(content_path)
        +start_new_game(player_name, case_id, game_data)
        +process_command(command) str
        +save_game() bool
        +load_game(player_id) bool
        -_get_context() Dict
        -_handle_examine(interpretation) str
        -_handle_talk(interpretation) str
        -_handle_say(interpretation) str
        -_handle_move(interpretation) str
        -_handle_inventory() str
    }

    class AIEnhancer {
        <<interface>>
        +enhance_description(base_description, context) str
        +enhance_usage(object, action, target, result) str
        +interpret_command(command, context) Dict
        +generate_npc_response(npc_data, history, input, must_include) str
        +summarize_conversation(history) str
    }

    class ClaudeEnhancer {
        -str api_key
        -ChatAnthropic llm
        -str model_name
        +__init__(api_key, model, max_tokens)
        +enhance_examine(target, context) str
        +enhance_description(base_description, context) str
        +enhance_usage(object_name, action, target, result) str
        +interpret_command(command, context) Dict
        +generate_npc_response(npc_data, history, input, must_include) str
        +summarize_conversation(history) str
        -_safe_invoke(messages, log_context) str
    }

    class Player {
        +str id
        +str name
        +str current_location
        +List~Item~ inventory
        +Dict~str,int~ investigation_skills
        +Investigation current_investigation
        +str session_start_time
        +int total_play_time
        +add_item(item)
        +remove_item(item_id) Item
        +has_item(item_id) bool
    }

    class Location {
        +str id
        +str name
        +str base_description
        +List~str~ items
        +List~str~ npcs
        +str illustration_path
        +bool visited
        +bool investigation_complete
        +List~Exit~ exits
        +add_exit(exit)
        +remove_exit(exit)
        +add_item(item)
        +remove_item(item_id) Item
        +add_npc(npc)
        +get_description(ai_enhancer, context) str
    }

    class Item {
        +str id
        +str name
        +str base_description
        +Dict~str,Any~ properties
        +List~ClueData~ clues
        +bool examined
        +bool fixed
        +str reason_fixed
        +examine(ai_enhancer, context) str
        +use(ai_enhancer, action, target) str
        +get_available_clues() List~ClueData~
        +reveal_clue(clue_id) ClueData
    }

    class NPC {
        +str id
        +str name
        +str base_description
        +Dict~str,Any~ personality
        +List~ClueData~ clues
        +List~ConversationEntry~ conversation_history
        +str current_mood
        +int relationship_level
        +str conversation_prompt
        +answer_conversation(ai_enhancer, player_input, context) str
        +add_conversation(player_input, response, clues_revealed)
        +get_available_clues() List~ClueData~
        +reveal_clue(clue_id) ClueData
        -_summarize_old_conversations()
    }

    class Investigation {
        +str case_id
        +str title
        +str description
        +Dict~str,ClueData~ discovered_clues
        +List~Dict~ clue_connections
        +int progress_percentage
        +List~str~ key_breakthroughs
        +add_clue(clue)
        +connect_clues(clue_id1, clue_id2, connection_type)
        +get_progress_summary() str
        -_update_progress()
    }

    class ClueData {
        +str id
        +str title
        +str description
        +bool revealed
        +List~str~ connections
    }

    class ConversationEntry {
        +str timestamp
        +str player_input
        +str npc_response
        +str mood_state
        +List~str~ clues_revealed
    }

    class Exit {
        +str destination
        +str item
    }

    class PersistenceManager {
        -str db_path
        +__init__(db_path)
        +save_player(player) bool
        +load_player(player_id) Player
        -_init_database()
    }

    GameEngine --> AIEnhancer
    GameEngine --> PersistenceManager
    GameEngine --> Player
    GameEngine --> Location
    GameEngine --> Item
    GameEngine --> NPC
    AIEnhancer <|-- ClaudeEnhancer
    Player --> Investigation
    Player --> Item
    Location --> Exit
    Location --> Item
    Location --> NPC
    NPC --> ConversationEntry
    NPC --> ClueData
    Item --> ClueData
    Investigation --> ClueData
```

## Module Dependency Graph

```mermaid
graph LR
    subgraph "Application Entry"
        APP[test_app.py]
    end

    subgraph "Core Engine"
        ENGINE[engine.py]
    end

    subgraph "Models Package"
        MODELS[models/models.py]
        CORE[models/core_data.py]
        AI[models/ai_enhancer.py]
    end

    subgraph "Utilities"
        UTILS[utils/utils.py]
    end

    subgraph "Chains"
        CHAINS[chains/command_chains.py]
        AGENT[chains/agent.py]
    end

    subgraph "External Dependencies"
        LANGCHAIN[langchain]
        ANTHROPIC[langchain_anthropic]
        OPENAI[langchain_openai]
        SQLITE[sqlite3]
        YAML_LIB[yaml]
    end

    APP --> ENGINE

    ENGINE --> MODELS
    ENGINE --> CORE
    ENGINE --> AI
    ENGINE --> UTILS
    ENGINE --> YAML_LIB

    MODELS --> CORE
    MODELS --> AI

    AI --> CORE
    AI --> LANGCHAIN
    AI --> ANTHROPIC
    AI --> OPENAI

    CHAINS --> LANGCHAIN

    UTILS --> MODELS
    UTILS --> SQLITE

    style ENGINE fill:#4CAF50
    style MODELS fill:#2196F3
    style AI fill:#FF9800
    style UTILS fill:#9C27B0
    style CHAINS fill:#E91E63
```

## Data Flow Diagram - Command to Response

```mermaid
graph TD
    START[User Input Command]

    START --> VALIDATE{Game State<br/>Playing?}
    VALIDATE -->|No| ERROR1[Return Error Message]
    VALIDATE -->|Yes| CONTEXT[Build Context]

    CONTEXT --> LOCATION[Get Current Location]
    CONTEXT --> ITEMS[Get Location Items]
    CONTEXT --> INVENTORY[Get Player Inventory]
    CONTEXT --> PROGRESS[Get Investigation Progress]

    LOCATION --> AI_INTERPRET[AI: Interpret Command]
    ITEMS --> AI_INTERPRET
    INVENTORY --> AI_INTERPRET
    PROGRESS --> AI_INTERPRET

    AI_INTERPRET --> RESOLVE[Resolve Targets<br/>to Real Objects]

    RESOLVE --> ROUTE{Route by<br/>Action Type}

    ROUTE -->|examine| EXAMINE[Handle Examine]
    ROUTE -->|talk/say/ask| TALK[Handle Talk]
    ROUTE -->|move| MOVE[Handle Move]
    ROUTE -->|inventory| INV[Handle Inventory]
    ROUTE -->|unknown| ERROR2[Return Unknown Command]

    EXAMINE --> AI_ENHANCE[AI: Enhance Description]
    TALK --> AI_NPC[AI: Generate NPC Response]
    MOVE --> UPDATE_LOC[Update Location]
    INV --> LIST_ITEMS[List Inventory Items]

    AI_ENHANCE --> RESPONSE[Game Response]
    AI_NPC --> RESPONSE
    UPDATE_LOC --> RESPONSE
    LIST_ITEMS --> RESPONSE
    ERROR2 --> RESPONSE
    ERROR1 --> RESPONSE

    RESPONSE --> SAVE[Auto-save Player State]
    SAVE --> END[Display to User]

    style START fill:#4CAF50
    style AI_INTERPRET fill:#FF9800
    style AI_ENHANCE fill:#FF9800
    style AI_NPC fill:#FF9800
    style RESPONSE fill:#2196F3
    style END fill:#4CAF50
```

## State Diagram - Game States

```mermaid
stateDiagram-v2
    [*] --> Menu: Application Start

    Menu --> Playing: start_new_game()
    Menu --> Playing: load_game()

    Playing --> Playing: process_command()
    Playing --> Paused: pause_game()
    Playing --> Ended: complete_investigation()
    Playing --> Menu: quit_to_menu()

    Paused --> Playing: resume_game()
    Paused --> Menu: quit_to_menu()

    Ended --> Menu: return_to_menu()
    Ended --> [*]: exit()

    Menu --> [*]: exit()

    state Playing {
        [*] --> Exploring
        Exploring --> Examining: examine command
        Exploring --> Talking: talk/say/ask command
        Exploring --> Moving: move command
        Exploring --> Managing: inventory command

        Examining --> Exploring: command complete
        Talking --> Exploring: conversation ends
        Moving --> Exploring: location changed
        Managing --> Exploring: action complete

        Talking --> ClueDiscovered: NPC reveals clue
        Examining --> ClueDiscovered: Item reveals clue
        ClueDiscovered --> Exploring: clue added
    }
```

## Entity-Relationship Diagram - Data Model

```mermaid
erDiagram
    Player ||--o{ Item : "has in inventory"
    Player ||--|| Investigation : "currently investigating"
    Player ||--|| Location : "currently at"

    Location ||--o{ Item : "contains"
    Location ||--o{ NPC : "contains"
    Location ||--o{ Exit : "has exits"

    Exit }o--|| Location : "leads to"
    Exit }o--|| Item : "through (door/gate)"

    Item ||--o{ ClueData : "reveals"
    NPC ||--o{ ClueData : "knows"
    NPC ||--o{ ConversationEntry : "has history"

    Investigation ||--o{ ClueData : "discovered"
    Investigation ||--o{ ClueConnection : "connected"

    ClueData ||--o{ ClueConnection : "related to"

    Player {
        string id PK
        string name
        string current_location FK
        json inventory
        json investigation_skills
        string session_start_time
        int total_play_time
    }

    Location {
        string id PK
        string name
        string base_description
        string illustration_path
        bool visited
        bool investigation_complete
    }

    Item {
        string id PK
        string name
        string base_description
        json properties
        bool examined
        bool fixed
        string reason_fixed
    }

    NPC {
        string id PK
        string name
        string base_description
        json personality
        string current_mood
        int relationship_level
        string conversation_prompt
    }

    Investigation {
        string case_id PK
        string title
        string description
        int progress_percentage
        json key_breakthroughs
    }

    ClueData {
        string id PK
        string title
        string description
        bool revealed
        json connections
    }

    ConversationEntry {
        string timestamp PK
        string player_input
        string npc_response
        string mood_state
        json clues_revealed
    }

    Exit {
        string destination FK
        string item FK
    }

    ClueConnection {
        string clue1 FK
        string clue2 FK
        string type
        string discovered_at
    }
```
