
# ==============================================================================
# Example Usage and Testing
# ==============================================================================
from engine import GameEngine

def main():
    """Example usage of the game engine"""
    print("AI-Enhanced Investigation Game - Core Architecture")
    print("=" * 50)
    
    # Initialize game engine
    engine = GameEngine()
    
    # Start a new game
    engine.start_new_game("Detective Smith", "case_001")
    
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