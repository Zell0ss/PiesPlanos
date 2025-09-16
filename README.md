# Gumsoe-style rpg investigation game
## Project Overview
A Python-based text adventure game inspired by Gumshoe investigation RPG system. The game combines classic text adventure mechanics with AI-enhanced descriptions and persistent NPC interactions.

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