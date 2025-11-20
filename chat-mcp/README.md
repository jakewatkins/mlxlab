# mcp-chat

LLM chat application with Model Context Protocol (MCP) server integration.

## Installation

```bash
cd chat-mcp
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Usage

```bash
mcp-chat <huggingface-model-path>
```

### Example

```bash
mcp-chat mlx-community/Hermes-3-Llama-3.1-8B-4bit
```

## Configuration

### Environment Variables (.env)

Create a `.env` file in the same directory where you run mcp-chat to store sensitive values like API keys:

```bash
BRAVE_API_KEY=your-brave-api-key-here
```

The `.env` file is automatically loaded when mcp-chat starts and is excluded from git commits.

### MCP Servers (mcp.json)

Create an `mcp.json` file in the same directory where you run mcp-chat:

```json
{
    "servers": {
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
        },
        "brave-search": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {
                "BRAVE_API_KEY": "${BRAVE_API_KEY}"
            }
        }
    }
}
```

Use `${VARIABLE_NAME}` syntax to reference environment variables from your `.env` file.

### System Prompt (config.json)

Optionally create a `config.json` file to set a custom system prompt:

```json
{
    "system_prompt": "You are a helpful AI assistant with access to tools. Use them when needed to help the user."
}
```

## Supported Models

mcp-chat works with models that have chat templates supporting tool/function calling:

- Llama 3.1+ (8B, 70B, etc.)
- Hermes 2.5+ (Nous Research)
- Mistral Instruct v0.3+
- Other models with OpenAI-compatible tool calling in their chat templates

### Recommended Models for MLX

```bash
# Hermes 3 (excellent tool calling)
mcp-chat mlx-community/Hermes-3-Llama-3.1-8B-4bit

# Llama 3.1
mcp-chat mlx-community/Meta-Llama-3.1-8B-Instruct-4bit

# Mistral
mcp-chat mlx-community/Mistral-7B-Instruct-v0.3-4bit
```

## Commands

- Type your prompt and press Enter
- Type `bye`, `quit`, or press Ctrl+C to exit

## Features

- ✅ Automatic tool execution from MCP servers
- ✅ Streaming responses
- ✅ Colored console output for tool calls
- ✅ 90-second timeout per tool call
- ✅ Maintains last 3 conversation turns
- ✅ Graceful error handling

## Requirements

- macOS (Apple Silicon for MLX)
- Python 3.9+
- Node.js (if using NPX-based MCP servers)

## Development

The project structure:

```
chat-mcp/
├── mcpchat/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── chat.py           # Chat loop and conversation
│   ├── mcp_client.py     # MCP server management
│   └── model_loader.py   # MLX model loading
├── requirements.txt
├── setup.py
└── README.md
```
