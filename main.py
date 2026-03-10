#!/usr/bin/env python3
"""
AI-Enhanced Detective Text Adventure Game
Interactive game launcher and main game loop
"""

import sys
import yaml
from pathlib import Path
from src.engine import GameEngine
from src.utils.logging_config import configure_logging

# Configure logging at startup based on LOG_LEVEL environment variable
configure_logging()


def clear_screen():
    """Clear the terminal screen"""
    print("\n" * 2)


def print_banner():
    """Print game banner"""
    print("=" * 70)
    print("   🔍  AI-ENHANCED DETECTIVE TEXT ADVENTURE  🔍")
    print("=" * 70)
    print()


def select_game() -> dict:
    """Let player select which game/case to investigate"""
    game_cards_path = Path(__file__).parent / "game_cards.yaml"

    try:
        with open(game_cards_path, "r") as file:
            game_cards = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"ERROR: Could not find game_cards.yaml at {game_cards_path}")
        sys.exit(1)

    print("Available Cases:")
    print("-" * 70)
    for idx, card in enumerate(game_cards, 1):
        print(f"{idx}. {card['name']}")
        print(f"   {card['description']}")
        print()

    while True:
        try:
            choice = input("Select a case number (or 'q' to quit): ").strip()
            if choice.lower() == "q":
                print("\nGoodbye, detective!")
                sys.exit(0)

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(game_cards):
                return game_cards[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(game_cards)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")


def get_player_name() -> str:
    """Get the player's detective name"""
    print()
    while True:
        name = input("Enter your detective name: ").strip()
        if name:
            return name
        print("Please enter a valid name.")


def show_help():
    """Display help information"""
    print("\n" + "=" * 70)
    print("GAME COMMANDS")
    print("=" * 70)
    print(
        """
Common Actions:
  - examine <object/person/location>  : Look at something closely
  - talk to <person>                  : Start a conversation
  - ask <person> about <topic>        : Ask specific questions
  - say <message> to <person>         : Say something to someone
  - go <direction/exit>               : Move to a new location
  - use <item> on <target>            : Use an item
  - check inventory / inventory       : See what you're carrying
  - look around                       : Examine your surroundings
  - help                              : Show this help message
  - save                              : Save your game
  - quit / exit                       : Exit the game

Tips:
  - You can use natural language! Try "look at the desk" or "examine door"
  - NPCs remember your conversations
  - Pay attention to details - clues are everywhere
  - In GUMSHOE style, you'll find clues automatically when you look
"""
    )
    print("=" * 70 + "\n")


def game_loop(engine: GameEngine):
    """Main interactive game loop"""
    print("\n" + "=" * 70)
    print("The investigation begins...")
    print("=" * 70)
    print("\nType 'help' for commands, 'save' to save, or 'quit' to exit.\n")

    # Show initial location
    response = engine.process_command("look around")
    print(response)
    print()

    while engine.game_state == "playing":
        try:
            # Get player input
            command = input("> ").strip()

            if not command:
                continue

            # Handle meta commands
            command_lower = command.lower()

            if command_lower in ["quit", "exit", "q"]:
                save = input("\nSave game before quitting? (y/n): ").strip().lower()
                if save == "y":
                    if engine.save_game():
                        print("✓ Game saved successfully!")
                    else:
                        print("✗ Failed to save game.")
                print("\nThanks for playing, detective!")
                break

            elif command_lower == "save":
                if engine.save_game():
                    print("✓ Game saved successfully!")
                else:
                    print("✗ Failed to save game.")
                continue

            elif command_lower in ["help", "?"]:
                show_help()
                continue

            # Process game command
            response = engine.process_command(command)
            print()
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGame interrupted!")
            save = input("Save game before quitting? (y/n): ").strip().lower()
            if save == "y":
                if engine.save_game():
                    print("✓ Game saved successfully!")
            print("\nThanks for playing, detective!")
            break

        except Exception as e:
            print(f"\n✗ An error occurred: {e}")
            print("The game will continue. Please try a different command.\n")


def main():
    """Main entry point for the game"""
    try:
        # Show banner
        print_banner()

        # Select game/case
        game_card = select_game()

        # Get player name
        player_name = get_player_name()

        # Initialize game engine
        print("\n⚙️  Initializing game engine...")
        engine = GameEngine()

        # Start new game
        case_id = game_card["name"].lower().replace(" ", "_")
        engine.start_new_game(player_name, case_id, game_card)

        print(f"✓ Game loaded: {game_card['name']}")

        # Start game loop
        game_loop(engine)

    except KeyboardInterrupt:
        print("\n\nGame interrupted! Goodbye, detective!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
