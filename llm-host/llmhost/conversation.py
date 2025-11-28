"""
Conversation history management
"""

from typing import List, Dict, Any, Optional


class ConversationHistory:
    """Manages the conversation history with proper message formatting"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self._tool_call_counter = 0
    
    def add_system_message(self, content: str):
        """Add system prompt to history"""
        self.messages.append({
            "role": "system",
            "content": content
        })
    
    def add_user_message(self, content: str):
        """Add user input to history"""
        self.messages.append({
            "role": "user",
            "content": content
        })
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        """
        Add LLM response to history
        
        Args:
            content: The text content of the response
            tool_calls: Optional list of tool calls made by the assistant
        """
        message: Dict[str, Any] = {
            "role": "assistant",
            "content": content
        }
        
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        self.messages.append(message)
    
    def add_tool_call(self, name: str, args: Dict[str, Any]) -> str:
        """
        Add tool call to history (as part of assistant message)
        
        Args:
            name: Tool name
            args: Tool arguments
            
        Returns:
            call_id: Unique identifier for this tool call
        """
        self._tool_call_counter += 1
        call_id = f"call_{self._tool_call_counter}"
        
        # Tool calls are typically part of the assistant message
        # We'll handle this differently - the assistant message will include tool_calls
        return call_id
    
    def add_tool_result(self, tool_call_id: str, name: str, result: str):
        """
        Add tool result to history
        
        Args:
            tool_call_id: ID of the tool call this result corresponds to
            name: Tool name
            result: Tool result as string
        """
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": result
        })
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Return full conversation history"""
        return self.messages.copy()
    
    def clear(self):
        """Reset conversation history"""
        self.messages = []
        self._tool_call_counter = 0
    
    def __len__(self) -> int:
        """Return number of messages in history"""
        return len(self.messages)
