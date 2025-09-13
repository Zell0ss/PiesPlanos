from models.core_data import ConversationEntry
from abc import ABC, abstractmethod
from typing import Dict, List, Any
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
    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, like: float, afraid: float) -> str:
        """Generate NPC response based on personality and history"""
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
    
    def generate_npc_response(self, npc_data: Dict, conversation_history: List, player_input: str, like: float, afraid: float) -> str:
        return f"{npc_data.get('name', 'Someone')} responds thoughtfully to your question."
    
    def summarize_conversation(self, conversation_history: List[ConversationEntry]) -> str:
        return f"Summary of {len(conversation_history)} conversation exchanges."