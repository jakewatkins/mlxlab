"""Model loading utilities for LLM Chat."""

import sys
from typing import Tuple, Any


class ModelLoader:
    """Handles loading and managing MLX language models."""
    
    def __init__(self, model_name: str):
        """
        Initialize the model loader.
        
        Args:
            model_name: Hugging Face model identifier
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
    
    def load(self) -> Tuple[Any, Any]:
        """
        Load the model and tokenizer from Hugging Face.
        
        Returns:
            Tuple of (model, tokenizer)
            
        Raises:
            Exception: If model loading fails
        """
        try:
            import mlx_lm
            
            print(f"Loading model {self.model_name}...")
            
            # Load model and tokenizer using mlx_lm
            self.model, self.tokenizer = mlx_lm.load(self.model_name)
            
            print("Model loaded successfully!\n")
            return self.model, self.tokenizer
            
        except ImportError as e:
            print(f"Error: MLX libraries not found. Please install with: pip install mlx mlx-lm")
            sys.exit(1)
        except Exception as e:
            error_msg = str(e)
            
            # Handle common errors
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"Error: Model '{self.model_name}' not found on Hugging Face.")
                print("Please check the model name and try again.")
            elif "memory" in error_msg.lower() or "out of memory" in error_msg.lower():
                print(f"Error: Insufficient memory to load model '{self.model_name}'.")
                print("Try using a smaller model or quantized version.")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                print(f"Error: Network error while downloading model.")
                print("Please check your internet connection and try again.")
            else:
                print(f"Error loading model: {error_msg}")
            
            sys.exit(1)
    
    def cleanup(self):
        """Clean up model resources."""
        self.model = None
        self.tokenizer = None
