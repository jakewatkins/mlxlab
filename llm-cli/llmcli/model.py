"""
MLX model loading and inference
"""

import re
from typing import List, Dict, Any, Generator, Optional
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
            result = mlx_lm.load(self.model_path)  # type: ignore
            
            # Handle different return formats (2 or 3 tuple)
            if len(result) == 2:
                self.model, self.tokenizer = result
            else:
                self.model, self.tokenizer, _ = result
                
        except Exception as e:
            raise ModelError(
                f"Failed to load model '{self.model_path}': {e}"
            )
    
    def generate(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Generate response from messages with streaming
        
        Args:
            messages: Conversation history in chat format
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
                verbose=False
            )
            
            # mlx_lm.generate returns the full text
            # Yield it character by character for streaming
            for char in response:
                yield char
                
        except Exception as e:
            raise ModelError(f"Generation failed: {e}")
    
    def detect_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect tool calls in model output
        
        Looks for format:
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
        
        # Look for <tool_call> XML tags with JSON inside
        # Use non-greedy match to handle nested JSON objects
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        matches = re.finditer(xml_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Extract the JSON content and parse it
                json_content = match.group(1)
                # Handle multi-line JSON by finding matching braces
                brace_count = 0
                end_pos = 0
                for i, char in enumerate(json_content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > 0:
                    json_str = json_content[:end_pos]
                else:
                    json_str = json_content
                    
                tool_data = json.loads(json_str)
                if "name" in tool_data and "arguments" in tool_data:
                    tool_calls.append(tool_data)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
