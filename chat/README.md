# LLM Chat Host

A simple interactive LLM chatbot powered by Apple's MLX framework.

## Installation

```bash
pip install -e .
```

## Usage

Start a chat session with any Hugging Face model:

```bash
llmchat mlx-community/Llama-3.2-3B-Instruct-4bit
```

## Commands

- Type your message and press Enter to chat
- Type `quit`, `bye`, or `exit` to end the session
- Press Ctrl+C to interrupt

## Requirements

- macOS (Apple Silicon recommended)
- Python 3.8+
- MLX framework

## Example

```
$ llmchat mlx-community/Llama-3.2-3B-Instruct-4bit
Loading model mlx-community/Llama-3.2-3B-Instruct-4bit...
Model loaded successfully!

prompt -> Hello, how are you?
I'm doing well, thank you for asking! How can I help you today?

prompt -> quit
Goodbye!
```
