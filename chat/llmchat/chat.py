"""Chat engine for interactive LLM conversations."""

import sys
from typing import Any, List, Dict


class ChatEngine:
    """Manages the interactive chat loop and response generation."""
    
    def __init__(self, model: Any, tokenizer: Any, model_name: str):
        """
        Initialize the chat engine.
        
        Args:
            model: The loaded MLX model
            tokenizer: The model's tokenizer
            model_name: Name of the model being used
        """
        self.model = model
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.conversation_history: List[Dict[str, str]] = []
        
        # Generation parameters
        self.max_tokens = 512
        self.temperature = 0.7
        self.top_p = 0.9
    
    def run(self):
        """Start the interactive chat loop."""
        try:
            while True:
                # Get user input
                try:
                    user_input = input("prompt -> ").strip()
                except EOFError:
                    # Handle Ctrl+D
                    print("\nGoodbye!")
                    break
                
                # Check for empty input
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ["quit", "bye", "exit"]:
                    print("Goodbye!")
                    break
                
                # Generate and display response
                response = self.generate_response(user_input)
                print(response + "\n")
                
        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("\n\nGoodbye!")
            sys.exit(0)
    
    def generate_response(self, user_input: str) -> str:
        """
        Generate a response to the user's input.
        
        Args:
            user_input: The user's message
            
        Returns:
            The model's response text
        """
        try:
            import mlx_lm
            
            # Add user message to conversation history
            messages = [{"role": "user", "content": user_input}]
            prompt = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True
            )

            # Generate response using mlx_lm.generate
            response = mlx_lm.generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                verbose=False
            )
            
            # Extract just the new response (remove the prompt)
            response_text = response.strip()
            #if response_text.startswith(prompt):
            #   response_text = response_text[len(prompt):].strip()
            
            # Add assistant response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(error_msg)
            # Don't add failed exchanges to history
            self.conversation_history.pop()  # Remove the user message we just added
            return "I encountered an error. Please try again."
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
