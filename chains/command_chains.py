import os

from langchain.chains import LLMChain
from typing import List, Dict, Any, Optional
from langchain.prompts import (
    ChatPromptTemplate
)


MODEL = os.getenv("ANTHROPIC_MODEL")

class LookerChain:
    """Chain for handling look/examine commands"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
        You are describing what the player sees when they examine something in a game.
        
        Player wants to look at: {target}
        Current location: {location_name} - {location_description}
        Available items in location: {items}
        Available characters in location: {characters}
        Player inventory: {inventory}
        
        If the target is:
        - An item: Provide detailed description based on the item's properties
        - A character: Describe their appearance and current state
        - The location itself (or general "look"): Describe the overall scene
        - Something not present: Politely indicate it's not visible
        
        Keep descriptions immersive and game-appropriate. Be descriptive but concise.
        
        Response:
        """)
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def run(self, target: str, game_state: Dict[str, Any]) -> str:
        return self.chain.run(**game_state, target=target)

class TalkerChain:
    """Chain for handling dialogue with NPCs"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
        You are managing dialogue between the player and an NPC in a game.
        
        Player wants to talk to: {character_name}
        Player's question/statement: {player_dialogue}
        
        Character details: {character_info}
        Current location context: {location_name}
        Other characters present: {other_characters}
        
        Previous dialogue context: {dialogue_history}
        
        Generate the character's response based on:
        - Their personality and background
        - The current situation and location
        - Previous conversations
        - Any relevant game plot points
        
        Keep the response in character and advance the story naturally.
        
        Character response:
        """)
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def run(self, character_name: str, player_dialogue: str, game_state: Dict[str, Any]) -> str:
        # Find the character in current location
        characters = game_state.get('characters', [])
        character = next((c for c in characters if c.name.lower() == character_name.lower()), None)
        
        if not character:
            return f"There is no {character_name} here to talk to."
        
        character_info = f"Name: {character.name}, Description: {character.description}"
        other_characters = [c.name for c in characters if c.name != character.name]
        
        return self.chain.run(
            character_name=character_name,
            player_dialogue=player_dialogue,
            character_info=character_info,
            location_name=game_state.get('location_name', ''),
            other_characters=other_characters,
            dialogue_history=character.dialogue_context.get('history', [])
        )

class ActionChain:
    """Chain for handling general actions (take, use, etc.)"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
        You are processing a player action in a text adventure game.
        
        Player action: {action}
        Target: {target}
        Current location: {location_name}
        Available items: {items}
        Player inventory: {inventory}
        
        Determine if the action is possible and provide appropriate feedback:
        - If taking an item: Check if it exists and can be taken
        - If using an item: Describe the result based on context
        - If moving: Check available exits
        - If action is impossible: Explain why clearly
        
        Provide a clear, game-appropriate response about what happens.
        
        Result:
        """)
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def run(self, action: str, target: str, game_state: Dict[str, Any]) -> str:
        return self.chain.run(action=action, target=target, **game_state)
