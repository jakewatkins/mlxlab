"""Main entry point for LLM Chat application."""

import sys
from llmchat.model_loader import ModelLoader
from llmchat.chat import ChatEngine


def main():
    """Main entry point for the llmchat command."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: llmchat <model_name>")
        print("\nExample:")
        print("  llmchat mlx-community/Llama-3.2-3B-Instruct-4bit")
        print("\nThe model_name should be a valid Hugging Face model identifier.")
        sys.exit(1)
    
    # Get model name from command line
    model_name = sys.argv[1]
    
    # Load the model
    loader = ModelLoader(model_name)
    model, tokenizer = loader.load()
    
    # Start the chat engine
    try:
        chat = ChatEngine(model, tokenizer, model_name)
        chat.run()
    finally:
        # Cleanup
        loader.cleanup()


if __name__ == "__main__":
    main()
