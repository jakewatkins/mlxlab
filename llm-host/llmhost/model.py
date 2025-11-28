"""
MLX model loading and inference
"""

import re
from typing import List, Dict, Any, Generator, Optional, Tuple, Union
import mlx_lm  # type: ignore
from mlx_lm.sample_utils import make_sampler  # type: ignore


class ModelError(Exception):
    """Raised when model loading or inference fails"""
    pass


class MLXModel:
    """Wrapper for MLX model loading and generation"""
    
    def __init__(self, model_path: str):
        """
        Initialize model wrapper
        
        Args:
            model_path: HuggingFace model path (e.g., 'ibm-granite/granite-4.0-1b')
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
    
    def load(self):
        """
        Load model from HuggingFace
        
        MLX will show its own loading indicator and use its built-in cache
        
        Raises:
            ModelError: If model loading fails
        """
        try:
            # mlx_lm.load handles downloading, caching, and loading
            # It shows a progress indicator automatically
            result = mlx_lm.load(self.model_path)  # type: ignore
            
            # Handle different return formats (2 or 3 tuple)
            if len(result) == 2:
                self.model, self.tokenizer = result
            else:
                self.model, self.tokenizer, _ = result
                
        except Exception as e:
            raise ModelError(
                f"Error: Model '{self.model_path}' not found or not accessible: {e}"
            )
    
    def generate(
        self, 
        messages: List[Dict[str, Any]], 
        stream: bool = True,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Generate response from messages with streaming
        
        Args:
            messages: Conversation history in chat format
            stream: Whether to stream tokens (always True for this app)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Yields:
            Generated tokens one at a time
            
        Raises:
            ModelError: If generation fails
        """
        if self.model is None or self.tokenizer is None:
            raise ModelError("Model not loaded. Call load() first.")
        
        try:
            # Apply chat template to format messages
            if hasattr(self.tokenizer, 'apply_chat_template'):
                prompt = self.tokenizer.apply_chat_template(  # type: ignore
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                # Fallback: basic formatting if no chat template
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            
            # Create a sampler with the temperature setting
            sampler = make_sampler(
                temp=temperature,
                top_p=1.0,
                min_p=0.0,
                min_tokens_to_keep=1
            )
            
            # Use mlx_lm.generate for streaming
            response = mlx_lm.generate(  # type: ignore
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                sampler=sampler,
                verbose=False  # We handle our own output
            )
            
            # mlx_lm.generate returns the full text, but we want streaming
            # We'll yield it character by character for the typewriter effect
            for char in response:
                yield char
                
        except Exception as e:
            raise ModelError(f"Error during generation: {e}")
    
    def detect_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect tool calls in model output
        
        This parser looks for our specified format:
        <tool_call>
        {"name": "tool_name", "arguments": {"param1": "value1"}}
        </tool_call>
        
        Args:
            text: Generated text to parse
            
        Returns:
            List of tool calls with name and arguments
        """
        tool_calls = []
        import json
        
        # Pattern 1: Look for <tool_call> XML tags with JSON inside
        xml_pattern = r'<tool_call>\s*(\{[^}]+\})\s*</tool_call>'
        matches = re.finditer(xml_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Parse the JSON inside the tool_call tags
                tool_data = json.loads(match.group(1))
                if "name" in tool_data and "arguments" in tool_data:
                    tool_calls.append(tool_data)
            except json.JSONDecodeError:
                # Skip invalid JSON and continue
                continue
        
        # Pattern 2: Fallback - look for standalone JSON tool calls (no XML tags)
        if not tool_calls:
            json_pattern = r'\{[^{}]*"name"\s*:\s*"([^"]+)"[^{}]*"arguments"\s*:\s*(\{[^{}]*\})[^{}]*\}'
            matches = re.finditer(json_pattern, text)
            
            for match in matches:
                tool_name = match.group(1)
                try:
                    arguments = json.loads(match.group(2))
                    tool_calls.append({
                        "name": tool_name,
                        "arguments": arguments
                    })
                except json.JSONDecodeError:
                    continue
        
        return tool_calls
    
    def get_chat_template(self) -> Optional[str]:
        """Get the model's chat template if available"""
        if self.tokenizer and hasattr(self.tokenizer, 'chat_template'):
            template = getattr(self.tokenizer, 'chat_template', None)
            if isinstance(template, str):
                return template
        return None
