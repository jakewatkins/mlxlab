"""
MLX model loading and inference
"""

import logging
from typing import List, Dict, Any
import mlx_lm  # type: ignore
from mlx_lm.sample_utils import make_sampler  # type: ignore


logger = logging.getLogger(__name__)


class ModelError(Exception):
    """Raised when model loading or inference fails"""
    pass


class MLXModel:
    """Wrapper for MLX model loading and generation"""
    
    def __init__(
        self,
        model_path: str,
        temperature: float = 0.7,
        top_p: float = 1.0,
        min_p: float = 0.0,
        min_tokens_to_keep: int = 1
    ):
        """
        Initialize model wrapper
        
        Args:
            model_path: HuggingFace model path
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            min_p: Minimum p sampling parameter
            min_tokens_to_keep: Minimum tokens to keep
        """
        self.model_path = model_path
        self.temperature = temperature
        self.top_p = top_p
        self.min_p = min_p
        self.min_tokens_to_keep = min_tokens_to_keep
        self.model = None
        self.tokenizer = None
    
    def load(self):
        """
        Load model from HuggingFace
        
        Raises:
            ModelError: If model loading fails
        """
        try:
            logger.info(f"Loading model: {self.model_path}")
            
            # mlx_lm.load handles downloading, caching, and loading
            result = mlx_lm.load(self.model_path)  # type: ignore
            
            # Handle different return formats (2 or 3 tuple)
            if len(result) == 2:
                self.model, self.tokenizer = result
            else:
                self.model, self.tokenizer, _ = result
            
            logger.info(f"Model loaded successfully: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model '{self.model_path}': {e}")
            raise ModelError(f"Failed to load model '{self.model_path}': {e}")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response from messages
        
        Args:
            messages: Conversation history in chat format
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
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
            
            logger.debug(f"Generating response with prompt length: {len(prompt)}")
            
            # Create a sampler with configured settings
            sampler = make_sampler(
                temp=self.temperature,
                top_p=self.top_p,
                min_p=self.min_p,
                min_tokens_to_keep=self.min_tokens_to_keep
            )
            
            # Use mlx_lm.generate
            response = mlx_lm.generate(  # type: ignore
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                sampler=sampler,
                verbose=False
            )
            
            logger.debug(f"Generated response length: {len(response)}")
            return response
                
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise ModelError(f"Error during generation: {e}")
    
    def unload(self):
        """Unload model to free resources"""
        logger.info("Unloading model")
        self.model = None
        self.tokenizer = None
