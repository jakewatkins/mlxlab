# LLM CLI

Command-line interface for MLX-based LLM with MCP tool integration - A non-interactive CLI tool for scripting LLM interactions with tool support.

## Features

- 🚀 **MLX-powered inference** - Uses Apple's MLX framework for efficient on-device LLM inference
- 🔧 **MCP tool integration** - Connects to MCP servers to provide tools to LLMs
- 💬 **Streaming output** - Real-time token streaming to stdout or file
- 🔄 **Automatic tool execution** - Detects and executes tool calls automatically
- 📝 **File I/O** - Read prompts from files, write responses to files
- 🎯 **Scriptable** - Perfect for automation and batch processing

## Installation

### Prerequisites

- Python 3.10 or higher
- macOS (for MLX support)

### Install from source

1. Install mcp-host library (required dependency):
```bash
cd ../mcp-host
pip install -e .
```

2. Install llm-cli:
```bash
cd ../llm-cli
pip install -e .
```

## Configuration

### 1. Create `config.json` (Optional)

Create a `config.json` file in your working directory:

```json
{
  "SystemPrompt": "You are a helpful AI assistant with access to various tools.",
  "temperature": 0.7,
  "top_p": 1.0,
  "min_p": 0.0,
  "min_tokens_to_keep": 1
}
```

If not present, sensible defaults will be used.

### 2. Create `mcp.json` (Optional)

Create an `mcp.json` file to configure MCP servers:

```json
{
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "brave-search-mcp"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

### 3. Environment Variables (Optional)

Store API keys in a `.env` file:

```bash
BRAVE_API_KEY=your_api_key_here
```

Environment variables are automatically loaded and expanded in `mcp.json`.

## Usage

### Basic Prompt

```bash
llm-cli ibm-granite/granite-4.0-1b -p "What is the capital of France?"
```

Output goes to stdout by default.

### Redirect to File

```bash
llm-cli ibm-granite/granite-4.0-1b -p "What is today's weather?" > weather.txt
```

### Write to File Directly

```bash
llm-cli ibm-granite/granite-4.0-1b -p "Search for news" -o output.txt
```

### Read Prompt from File

```bash
llm-cli ibm-granite/granite-4.0-1b -pf prompt.txt -o response.txt
```

### Limit Output Length

```bash
llm-cli ibm-granite/granite-4.0-1b -p "Write a story" --max-tokens 100
```

### Disable Tools

```bash
llm-cli ibm-granite/granite-4.0-1b -p "Hello" --no-tools
```

## Command-Line Options

```
usage: llm-cli <model_path> [options]

Positional arguments:
  model_path              HuggingFace model path (e.g., ibm-granite/granite-4.0-1b)

Options:
  -p, --prompt TEXT       Prompt text to send to LLM
  -pf, --prompt-file PATH Read prompt from file
  -o, --output PATH       Write output to file (default: stdout)
  --max-tokens INT        Maximum tokens to generate (default: 2048)
  --no-tools              Disable MCP tool integration
  -h, --help              Show help message
```

## Output Behavior

- **stdout**: Clean LLM response text only (no timestamps, no formatting)
- **stderr**: Tool execution logs, errors, and status messages

Example stderr output:
```
Loading model: ibm-granite/granite-4.0-1b
Starting MCP servers...
Discovered 5 tools
[14:32:01] Calling tool: brave_web_search(query="Python tutorials") ...
[14:32:02] Result: {...} (took 1.23s)
```

## Exit Codes

- `0`: Success
- `1`: Configuration error
- `2`: Argument validation error
- `3`: Model loading error
- `4`: MCP server error
- `5`: Execution error
- `6`: File I/O error

## Tool Execution

When tools are enabled (default), llm-cli will:

1. Detect tool calls in LLM output
2. Execute tools automatically via MCP servers
3. Feed results back to the LLM
4. Continue until final answer is generated
5. Maximum 10 tool iterations to prevent infinite loops

Tool calls must use this format:
```
<tool_call>
{"name": "tool_name", "arguments": {"param": "value"}}
</tool_call>
```

## Recommended Models

Models that work well with tool calling:

- **IBM Granite 3.1+** - `ibm-granite/granite-3.1-8b-instruct`
- **Meta Llama 3.1+** - `meta-llama/Llama-3.1-8B-Instruct`
- **Qwen 2.5+** - `Qwen/Qwen2.5-7B-Instruct`

Smaller models for testing:
- `ibm-granite/granite-4.0-1b` - Fast, good for testing
- `Qwen/Qwen2.5-0.5B-Instruct` - Very small, basic tool calling

## Examples

### Web Search

```bash
llm-cli ibm-granite/granite-3.1-8b-instruct \
  -p "Search for the latest news about AI" \
  -o news.txt
```

### File Operations

```bash
llm-cli ibm-granite/granite-3.1-8b-instruct \
  -p "List files in /tmp and count them" \
  -o file-count.txt
```

### Batch Processing

```bash
# Process multiple prompts
for prompt_file in prompts/*.txt; do
  output_file="outputs/$(basename "$prompt_file")"
  llm-cli ibm-granite/granite-4.0-1b -pf "$prompt_file" -o "$output_file"
done
```

### Pipeline Integration

```bash
# Generate report and pipe to another tool
llm-cli ibm-granite/granite-3.1-8b-instruct \
  -p "Summarize the key points" | \
  grep "Important" | \
  wc -l
```

## Troubleshooting

### Model Not Found

If you see "Model not found", ensure:
- Model path is correct (check HuggingFace)
- You have internet connection for first download
- MLX will cache models after first download

### MCP Server Errors

If MCP servers fail to start:
- Check `mcp.json` syntax
- Ensure required commands are installed (`npx`, etc.)
- Check `.env` file for API keys
- Run with `--no-tools` to disable tools temporarily

### Empty Output

If output is empty:
- Check stderr for errors
- Try increasing `--max-tokens`
- Ensure prompt is not empty
- Test with simpler prompt first

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
