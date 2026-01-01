# ANE Chat

## Overview
This is a simple LLM chatbot that hosts an LLM and allows the user to interactively prompt it until they type "quit" or "bye". The chat bot is written in Swift and uses Apple's Core ML libraries.

## User Flow
To start the chat bot the user will enter `anechat` followed by the name of the Huggingface LLM they want to use. The program loads the LLM, sets up the model and tokenizer and then asks the user to enter their prompt. The prompt ends with the user typing the enter key. The chat bot transforms the user's prompt into the message object and then generates the LLM's response and prints it on the screen. After the llm has responded the chat bot will put up another line for the user to enter another prompt. The line will be "prompt ->".

## Technical Requirements

### 1. Command-Line Interface
- **Entry Point**: Create a command-line executable named `llmchat`
- **Usage**: `llmchat <model_name>`
  - `<model_name>`: Hugging Face model identifier (e.g., `mlx-community/Llama-3.2-3B-Instruct-4bit`)
- **Validation**: Verify that a model name argument is provided; exit with helpful error message if missing

### 2. Dependencies
- **Python Version**: Python 3.8+
- **Required Libraries**:
  - `mlx` - Apple's MLX machine learning framework
  - `mlx-lm` - MLX language model utilities
  - `transformers` - For tokenizer support
  - `huggingface-hub` - For model downloading

### 3. Model Loading
- **Model Source**: Download from Hugging Face Hub if not cached locally
- **MLX Integration**: Use MLX's model loading utilities (e.g., `mlx_lm.load()`)
- **Components to Load**:
  - Model weights
  - Tokenizer
  - Model configuration
- **Error Handling**: 
  - Handle network errors during download
  - Handle invalid model names
  - Handle insufficient memory errors
  - Provide clear error messages to user

### 4. Chat Loop
- **Initialization**: Display welcome message with loaded model name
- **Prompt Display**: Show `prompt ->` before each user input
- **Input Handling**:
  - Read user input from stdin
  - Trim whitespace from input
  - Check for exit commands (case-insensitive): `quit`, `bye`, `exit`
- **Message Format**: Transform user input into proper chat message format
  - Use standard chat template format (e.g., `[{"role": "user", "content": "<user_input>"}]`)
  - Maintain conversation history for context (optional but recommended)

### 5. Response Generation
- **Generation Parameters**:
  - `max_tokens`: 512 (configurable)
  - `temperature`: 0.7 (configurable)
  - `top_p`: 0.9 (configurable)
- **Processing**:
  - Apply tokenizer's chat template
  - Generate response using MLX model
  - Decode tokens to text
- **Output**: Print model response to stdout
- **Streaming** (optional): Stream tokens as they're generated for better UX

### 6. Exit Behavior
- **Exit Commands**: `quit`, `bye`, `exit` (case-insensitive)
- **Cleanup**: 
  - Display goodbye message
  - Free model from memory
  - Exit gracefully with status code 0

### 7. Error Handling
- **Input Errors**: Handle empty prompts gracefully
- **Generation Errors**: Catch and display generation failures
- **Keyboard Interrupt**: Handle Ctrl+C gracefully with cleanup
- **Resource Errors**: Handle out-of-memory conditions

### 8. User Experience
- **Startup Message**: Display model loading progress
- **Response Formatting**: Clearly separate user prompts from model responses
- **Visual Cues**: Use consistent prompt indicator (`prompt ->`)
- **Performance**: Display response time (optional)

### 9. Configuration (Optional Enhancements)
- **Config File**: Support `.llmchat_config` file for default parameters
- **CLI Flags**:
  - `--temperature`: Set generation temperature
  - `--max-tokens`: Set maximum response length
  - `--no-history`: Disable conversation history

### 10. Installation
- **Package Structure**: Organize as installable Python package
- **Setup Script**: Include `setup.py` or `pyproject.toml`
- **Entry Point**: Register `llmchat` command in package configuration
- **Dependencies**: List all dependencies in `requirements.txt` or package config

## Example Session
```
$ llmchat mlx-community/Llama-3.2-3B-Instruct-4bit
Loading model mlx-community/Llama-3.2-3B-Instruct-4bit...
Model loaded successfully!

prompt -> Hello, how are you?
I'm doing well, thank you for asking! How can I help you today?

prompt -> What is the capital of France?
The capital of France is Paris.

prompt -> quit
Goodbye!
```

## File Structure
```
llmchat/
├── README.md
├── requirements.txt
├── setup.py (or pyproject.toml)
└── llmchat/
    ├── __init__.py
    ├── __main__.py
    ├── chat.py
    ├── model_loader.py
    └── utils.py
```
