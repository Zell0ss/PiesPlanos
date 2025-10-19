from src.models.core_data import ConversationEntry
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from langchain_community.callbacks.manager import get_openai_callback
import json
import logging

# Configure logging for API usage tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
# ==============================================================================
# AI Enhancement Interface
# ==============================================================================

class AIEnhancer(ABC):
    """
    Abstract interface for AI enhancement services. 
    All methods should be defined on the implementation and as such are marked with @abstractmethod. 
    
    The AI will help with
    - enhancing the descriptions of items and locations
    - interpret the commands given by the player in natural language in an ai-agent fashion
    - generate NPC responses based on personality, previous interactions, likability and afraidness
    - summarize long conversations
    """
    
    @abstractmethod
    def enhance_description(self, base_description: str, context: Dict[str, Any]) -> str:
        """Enhance a base description with AI while respecting boundaries"""
        pass
    
    @abstractmethod
    def enhance_usage(self, object: str, action: str, target: str, result: Dict[str, Any]) -> str:
        """Enhance the description with AI of the result of an action while respecting boundaries"""
        pass
    
    @abstractmethod
    def interpret_command(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret player command with AI assistance"""
        pass
    
    @abstractmethod
    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, must_include: str) -> str:
        """Generate NPC response based on personality, current_mood, relationship_level and history"""
        pass
    
    @abstractmethod
    def summarize_conversation(self, conversation_history: List[ConversationEntry]) -> str:
        """Create summary of long conversation for context management"""
        pass

class MockAIEnhancer(AIEnhancer):
    """Mock implementation for testing without API calls"""
    
    def enhance_description(self, base_description: str, context: Dict[str, Any]) -> str:
        return f"{base_description} [AI: The atmosphere feels tense and mysterious.]"
    
    def enhance_usage(self,object: str, action: str, target: str, result: Dict[str, Any]) -> str:
        return f"Your {action} off {object} with {target} accomplishes {result} [AI: You are amazed at your dexterity.]"
    
    def interpret_command(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "examine", "target": "room", "confidence": 0.8}
    
    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, must_include: str) -> str:
        return f"{npc_data.get('name', 'Someone')} —{must_include}— responds thoughtfully to your question."
    
    def summarize_conversation(self, conversation_history: List[ConversationEntry]) -> str:
        return f"Summary of {len(conversation_history)} conversation exchanges."



class ClaudeEnhancer(AIEnhancer):
    """Claude implementation using LangChain"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307", max_tokens: int = 500):
        """
        Initialize Claude enhancer
        
        Args:
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
            model: Model to use (claude-3-haiku-20240307, claude-3-sonnet-20240229, etc.)
            max_tokens: Maximum tokens per response
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter.")
        
        self.llm = ChatAnthropic(
            model=model,
            max_tokens=max_tokens,
            temperature=0.7,
            anthropic_api_key=self.api_key
        )
        self.model_name = model or os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')
        
    def _safe_invoke(self, messages: List, log_context: str = "request") -> str:
        """Safely invoke Claude with error handling"""
        try:
            response = self.llm.invoke(messages)
            logger.info(f"Claude {log_context}: Request completed successfully")
            return response.content
        except Exception as e:
            logger.error(f"Claude API error in {log_context}: {e}")
            return f"[AI unavailable: {str(e)}]"
    
    def enhance_examine(self, target, context: Dict[str, Any]) -> str:
        """Enhance a base description with atmospheric details"""
        messages = [
            SystemMessage(content="""You are enhancing descriptions for a GUMSHOE mystery game. 
                Add atmospheric details, sensory elements, and mood without changing core facts.
                Keep the tone noir/detective fiction. Be concise but evocative (1-2 additional sentences max).
                Never contradict the base description or add new interactive elements."""
            ),
            HumanMessage(content=f"""
                Target: {target.name}
                Base description: {target.base_description}
                
                Game context:
                - Location: {context.get('location', 'unknown/not important')}
                - Player mood: {context.get('player_mood', 'neutral')}
                
                Enhance this description:"""
            )
        ]
        
        return self._safe_invoke(messages, "description enhancement")


    def enhance_description(self, base_description: str, context: Dict[str, Any]) -> str:
        """Enhance a base description with atmospheric details"""
        messages = [
            SystemMessage(content="""You are enhancing descriptions for a GUMSHOE mystery game. 
                Add atmospheric details, sensory elements, and mood without changing core facts.
                Keep the tone noir/detective fiction. Be concise but evocative (1-2 additional sentences max).
                Never contradict the base description or add new interactive elements."""
            ),
            HumanMessage(content=f"""
                Base description: {base_description}
                
                Game context:
                - Location: {context.get('location', 'unknown')}
                - Time of day: {context.get('time', 'unknown')}  
                - Player mood: {context.get('player_mood', 'neutral')}
                - Current clues found: {context.get('clues_found', [])}
                
                Enhance this description:"""
            )
        ]
        
        return self._safe_invoke(messages, "description enhancement")
    
    def enhance_usage(self, object_name: str, action: str, target: str, result: Dict[str, Any]) -> str:
        """Enhance the description of action results"""
        messages = [
            SystemMessage(content="""You are describing the results of player actions in a GUMSHOE mystery game.
                Make the action feel impactful and descriptive while staying true to the actual result.
                Focus on how the action unfolds, what the player notices, and the immediate consequences.
                Keep it concise (1-2 sentences) and maintain noir atmosphere."""
            ),
            HumanMessage(content=f"""
                Action: {action}
                Object used: {object_name}
                Target: {target}
                
                Actual result: {result.get('description', 'Action completed')}
                Success: {result.get('success', True)}
                
                Enhance this action description:"""
            )
        ]
        
        return self._safe_invoke(messages, "action enhancement")
    
    def interpret_command(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret natural language commands into game actions"""
        available_actions = context.get('available_actions', ['examine', 'use', 'talk', 'go', 'say', 'ask', 'inventory'])
        available_objects = context.get('items', [])
        available_exits = context.get('exits', [])
        available_people = context.get('people', [])
        location = context.get('location').name

        messages = [
            SystemMessage(content=f"""
                You are interpreting player commands for a GUMSHOE mystery game.
                Convert natural language into structured game actions.
                          
                To do that you will be given the context the player is in, the available actions and the command given by the player.
                
                ## instructions:
                - Not all the actions can be done with any target, only the ones that make sense.
                - The exits are defined by the destination which is the location name they go to and the item which is the door/exit that leads there.
                - Actions like "use" can have two targets: the object you use (target) and the object/person that receives the action (recipient)
                - Actions like "go" can have a direction (target)
                - Actions like "talk" should have a person as a target and no recipient
                - Actions like "ask" or "say" should have a person as a target, no recipient and a message
                - Actions like "inventory" should have NO target and NO recipient (commands like "check inventory", "show inventory", "what am I carrying")
                - Not all actions should have a recipient, only the ones that make sense.
                - Anything can be looked at: locations, objects, exits, people.
                - Always include the complete name of the target. If the name is "20th street cafe and bar" do not shorten to "20th street" or "cafe and bar": use always "20th street cafe and bar".
                - if you cannot interpret the command, or the interpretations doesnt have any sense
                return ONLY a JSON object with:
                    - "action": "unknown"
                    - "target": "unknown"
                    - "recipient": "unknown"
                    - "confidence": 0
                          
                ## context:
                - Location the player is in: {location}
                - Available objects in scene: {available_objects}  
                - Available exits of the location the player is in: {available_exits}.
                - Available people: {available_people}
                - Available actions: {available_actions}
                
                ## response
                Return ONLY a JSON object with:
                - "action": one of the available actions
                - "target": the location/object/person/direction. You must not shorten the name of the target.
                - "recipient": optional recipient of the action (if applicable)
                - "message": optional message for actions like "ask" or "say"
                - "confidence": float 0-1 indicating the certainty of your response 
                - "alternative": optional alternative interpretation
                
                Remember: your output must be always a json object. Do not include any explanations
                """
            ),
            HumanMessage(content=f"Player command: '{command}'")
        ]
        
        try:
            response = self._safe_invoke(messages, "command interpretation")
            # Try to parse JSON, fallback to simple interpretation
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback interpretation
                return {
                    "action": "examine", 
                    "target": "room",
                    "confidence": 0.5,
                    "note": "Failed to parse AI response"
                }
        except Exception as e:
            return {"action": "examine", "target": "room", "confidence": 0.1, "error": str(e)}
    
    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, must_include: str) -> str:
        """Generate contextual NPC responses"""
        # Summarize recent conversation for context
        recent_context = ""
        if conversation_history:
            recent_context = " Recent exchanges: " + "; ".join([
                f"Player: {entry.player_input[:50]}... NPC: {entry.npc_response[:50]}..."
                for entry in conversation_history[-3:]
            ])
        
        messages = [
            SystemMessage(content=f"""You are playing an NPC in a GUMSHOE mystery game.
            
                Character: {npc_data.get('name', 'Unknown')}
                Personality: {npc_data.get('personality', 'neutral')}
                Current mood: {npc_data.get('current_mood', 'neutral')}
                Relationship with player: {npc_data.get('relationship_level', 'stranger')}
                Knowledge: {npc_data.get('knowledge', 'basic')}
                
                IMPORTANT: You must naturally include this information in your response: "{must_include}"
                
                Stay in character. Be consistent with previous interactions.
                In GUMSHOE, NPCs give clues if approached with the right investigative skill.
                Keep responses conversational and realistic (1-3 sentences)."""
            ),
            HumanMessage(content=f"""
                {recent_context}
                
                Player says: "{player_input}"
                
                Respond as this NPC:"""
            )
        ]
        
        return self._safe_invoke(messages, "NPC response")
    
    def summarize_conversation(self, conversation_history: List[ConversationEntry]) -> str:
        """Summarize long conversations for context management"""
        if not conversation_history:
            return "No conversation history."
        
        conversation_text = "\n".join([
            f"Player: {entry.player_input}\nNPC: {entry.npc_response}"
            for entry in conversation_history
        ])
        
        messages = [
            SystemMessage(content="""Summarize this conversation between a player and NPC in a mystery game.
            Focus on: key information revealed, relationship changes, important clues discovered, 
            and the current state of their interaction. Be concise but capture essential details."""),
            HumanMessage(content=f"Conversation to summarize:\n{conversation_text}")
        ]
        
        return self._safe_invoke(messages, "conversation summary")




class OpenAISimpleAIEnhancer(AIEnhancer):
    """OpenAI implementation using langchain-openai"""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model
        )

    def enhance_description(self, base_description: str, context: Dict[str, Any]) -> str:
        prompt = f"Enhance this description while maintaining the original tone and style. Base description: {base_description}. Context: {context}"
        response = self.llm.invoke(prompt)
        return response.content

    def enhance_usage(self, object: str, action: str, target: str, result: Dict[str, Any]) -> str:
        prompt = f"Describe the result of using {object} to {action} on {target}. Result: {result}. Make it vivid but concise."
        response = self.llm.invoke(prompt)
        return response.content

    def interpret_command(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"Parse this game command into action and target. Command: '{command}'. Context: {context}. Return as JSON with action, target, and confidence fields."
        response = self.llm.invoke(prompt)
        # Note: In a real implementation, you'd want to parse the JSON response
        # For now, returning a basic structure
        return {"action": "examine", "target": command.split()[-1] if command.split() else "room", "confidence": 0.8}

    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, must_include: str) -> str:
        prompt = f"Generate an NPC response for {npc_data.get('name', 'NPC')} with personality: {npc_data.get('personality', 'neutral')}. Player said: '{player_input}'. Must include: '{must_include}'. History: {conversation_history[-3:] if conversation_history else 'None'}"
        response = self.llm.invoke(prompt)
        return response.content

    def summarize_conversation(self, conversation_history: List[ConversationEntry]) -> str:
        conversations_text = "\n".join([f"{entry.speaker}: {entry.text}" for entry in conversation_history])
        prompt = f"Summarize this conversation concisely:\n{conversations_text}"
        response = self.llm.invoke(prompt)
        return response.content