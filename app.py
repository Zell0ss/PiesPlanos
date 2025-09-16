
# ==============================================================================
# Example Usage and Testing
# ==============================================================================
# %%
from engine import GameEngine
import yaml

def main(game_name:str = "The Invisible Cadaver"):
    """Example usage of the game engine"""
    print("AI-Enhanced Investigation Game - Core Architecture")
    print("=" * 50)

    # LOad the game card
    with open("/data/PiesPlanos/game_cards.yaml", "r") as file:
        game_cards = yaml.safe_load(file)

    # Initialize game engine
    engine = GameEngine()

    # Start a new game
    for card in game_cards:
        if card["name"] == game_name:
            engine.start_new_game("Detective Smith", "case_001", card)
            print(f"Starting new game: {card['name']}")
            break

    # Process some example commands
    commands = [
        "look around",
        "examine the desk",
        "talk to the librarian", 
        "check inventory",
        "go north"
    ]
    
    for command in commands:
        print(f"\n> {command}")
        response = engine.process_command(command)
        print(response)
    
    # Save the game
    if engine.save_game():
        print("\nGame saved successfully!")
    else:
        print("\nFailed to save game.")

if __name__ == "__main__":
    main()
# %%
