# LLM CLI - Technical Implementation Plan

Based on llm-host architecture, adapted for non-interactive CLI usage.

## Architecture Overview

llm-cli will be a simplified, non-interactive version of llm-host with the following components:

```
llm-cli/
├── llmcli/
│   ├── __init__.py
│   ├── __main__.py       # Entry point for CLI
│   ├── cli.py            # Main CLI orchestration
│   ├── config.py         # Configuration loading (reuse from llm-host)
│   ├── model.py          # MLX model wrapper (reuse from llm-host)
│   ├── tool_executor.py  # MCP tool execution (reuse from llm-host)
│   └── output_writer.py  # Output handling (stdout/file)
├── setup.py
├── requirements.txt
└── README.md
```

## Component Specifications

### 1. CLI Module (`cli.py`)

**Purpose**: Main orchestration - parse arguments, load config, execute single prompt

**Key Functions**:
- `parse_arguments()` - Parse command-line arguments
- `run_prompt(model, prompt, tools, config, max_tokens)` - Execute single prompt with tool support
- `main()` - Entry point coordinating all operations

**Command-line Arguments**:
```
llm-cli <model_path> [options]

Positional:
  model_path              HuggingFace model path (e.g., ibm-granite/granite-4.0-1b)

Options:
  -p, --prompt TEXT       Prompt text to send to LLM
  -pf, --prompt-file PATH Read prompt from file
  -o, --output PATH       Write output to file (default: stdout)
  --max-tokens INT        Maximum tokens to generate
  --no-tools              Disable MCP tool integration
  -h, --help             Show help message
```

**Validation**:
- Must provide either `-p` or `-pf` (not both, not neither)
- `--prompt-file` must exist and be readable
- Exit with usage message if validation fails

**Exit Codes**:
- 0: Success
- 1: Configuration error (missing config files, invalid JSON)
- 2: Argument validation error
- 3: Model loading error
- 4: MCP server startup error
- 5: Execution error (tool failure, generation error)
- 6: File I/O error

### 2. Configuration Module (`config.py`)

**Purpose**: Load and validate configuration files

**Reuse from llm-host**:
- Config loading logic
- JSON validation
- Default values

**Configuration Files** (all in current working directory):
- `config.json` - System prompt and sampling parameters
- `mcp.json` - MCP server configuration
- `.env` - Environment variables (optional)

**Config.json Schema**:
```json
{
  "SystemPrompt": "string (required)",
  "temperature": "float (optional, default: 0.7)",
  "top_p": "float (optional, default: 1.0)",
  "min_p": "float (optional, default: 0.0)",
  "min_tokens_to_keep": "int (optional, default: 1)"
}
```

**Behavior**:
- If `config.json` doesn't exist, use default system prompt
- If `mcp.json` doesn't exist and `--no-tools` not specified, warn but continue
- If `.env` exists, load environment variables before expanding `mcp.json`

### 3. Model Module (`model.py`)

**Purpose**: MLX model wrapper for streaming generation

**Reuse from llm-host**:
- `MLXModel` class
- Model loading
- Streaming generation
- Chat template formatting

**Key Differences from llm-host**:
- No need for console output during generation (handled by output_writer)
- May need to buffer tokens for file writing

### 4. Tool Executor Module (`tool_executor.py`)

**Purpose**: MCP server integration and tool execution

**Reuse from llm-host**:
- `ToolExecutor` class
- MCP server management via mcp-host
- Tool call detection and parsing
- Tool execution logic

**Key Behavior**:
- Start MCP servers on initialization
- Detect tool calls in streaming output
- Execute tools automatically
- Continue generation until final answer
- Shutdown servers on completion

**Error Handling**:
- Tool execution failures should be logged to stderr
- Return error message to LLM for retry
- Maximum 10 tool iterations to prevent infinite loops

### 5. Output Writer Module (`output_writer.py`) - **NEW**

**Purpose**: Handle streaming output to stdout or file

**Class**: `OutputWriter`

**Methods**:
```python
class OutputWriter:
    def __init__(self, output_path: str | None = None):
        """
        Initialize output writer.
        
        Args:
            output_path: File path for output, or None for stdout
        """
        
    def write_token(self, token: str) -> None:
        """Write a single token (streaming)."""
        
    def finalize(self) -> None:
        """Flush and close output."""
```

**Behavior**:
- If `output_path` is None, write to stdout
- If `output_path` is specified, write to file (overwrite)
- Stream tokens as they arrive (no buffering)
- Handle UTF-8 encoding
- Flush after each token for real-time output
- Ensure proper cleanup in `finalize()`

**Error Handling**:
- If file cannot be opened/written, raise exception with exit code 6
- Write errors to stderr before exiting

### 6. Main Entry Point (`__main__.py`)

**Purpose**: Package entry point

**Behavior**:
```python
from llmcli.cli import main

if __name__ == "__main__":
    main()
```

## Execution Flow

```
1. Parse command-line arguments
   └─> Validate (prompt provided, files exist, etc.)
   
2. Load configuration files
   ├─> Load .env (if exists)
   ├─> Load config.json (with defaults if missing)
   └─> Load mcp.json (if --no-tools not specified)
   
3. Initialize components
   ├─> Start MCP servers (if enabled)
   ├─> Load MLX model
   └─> Initialize output writer
   
4. Read prompt
   └─> From -p argument OR -pf file
   
5. Execute prompt with tool support
   ├─> Format prompt with system prompt and tools
   ├─> Generate streaming response
   ├─> Detect tool calls
   ├─> Execute tools and continue generation
   └─> Repeat until final answer
   
6. Write output
   └─> Stream tokens to stdout or file
   
7. Cleanup
   ├─> Finalize output
   └─> Shutdown MCP servers
   
8. Exit with appropriate code
```

## Tool Call Loop

```
while not final_answer:
    1. Generate tokens from model
    2. Stream tokens to output
    3. Check for <tool_call> XML tags
    4. If tool call detected:
       a. Parse tool name and arguments
       b. Execute tool via MCP server
       c. Log to stderr: "[TIME] Calling tool: name(args) ..."
       d. Log to stderr: "[TIME] Result: ... (took Xs)"
       e. Add tool result to conversation
       f. Continue generation
    5. If no tool call and generation complete:
       a. Mark as final_answer
       b. Break loop
    6. If max iterations (10) reached:
       a. Log warning to stderr
       b. Return current output
       c. Break loop
```

## Error Handling Strategy

**Configuration Errors** (exit code 1):
- Missing required config values
- Invalid JSON syntax
- MCP server config errors

**Argument Errors** (exit code 2):
- No prompt provided
- Both -p and -pf specified
- Invalid argument combinations

**Model Errors** (exit code 3):
- Model not found on HuggingFace
- Model download failed
- MLX initialization failed

**MCP Errors** (exit code 4):
- MCP server startup failed
- Server crashed during execution

**Execution Errors** (exit code 5):
- Generation failed
- Tool execution failed repeatedly
- Maximum iterations exceeded

**I/O Errors** (exit code 6):
- Cannot read prompt file
- Cannot write output file
- File permission errors

**All errors**:
- Write descriptive message to stderr
- Exit with appropriate code
- Ensure MCP servers are shutdown

## Logging Strategy

**stderr output** (always enabled):
- Tool execution: `[14:32:01] Calling tool: calculator(expression="25 * 37") ...`
- Tool results: `[14:32:01] Result: 925 (took 0.12s)`
- Errors: `Error: <descriptive message>`
- Warnings: `Warning: <message>`

**stdout output**:
- Only the LLM's final answer (clean text)
- No timestamps, no formatting, no markup

## Code Reuse from llm-host

**Direct reuse** (copy and adapt):
- `config.py` - Configuration loading
- `model.py` - MLX model wrapper
- `tool_executor.py` - MCP integration

**New modules**:
- `cli.py` - Argument parsing and orchestration
- `output_writer.py` - Output handling

**Not needed**:
- `console.py` - Interactive console UI
- `conversation.py` - Multi-turn conversation management (we have single prompt)

## Dependencies

**Same as llm-host**:
```
mlx-lm>=0.18.0
rich>=13.0.0
mcp-host (local package)
```

**Additional** (for argument parsing):
```
argparse (stdlib)
```

## Setup.py Configuration

```python
setup(
    name="llm-cli",
    version="0.1.0",
    packages=["llmcli"],
    install_requires=[
        "mlx-lm>=0.18.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "llm-cli=llmcli.cli:main",
        ],
    },
    python_requires=">=3.10",
)
```

## Testing Strategy

**Manual tests**:
1. Basic prompt: `llm-cli granite-4.0-1b -p "Hello, world!"`
2. File prompt: `llm-cli granite-4.0-1b -pf prompt.txt`
3. File output: `llm-cli granite-4.0-1b -p "Test" -o output.txt`
4. Tool usage: `llm-cli granite-4.0-1b -p "What files are in /tmp?"`
5. No tools: `llm-cli granite-4.0-1b -p "Hello" --no-tools`
6. Max tokens: `llm-cli granite-4.0-1b -p "Write a story" --max-tokens 50`
7. Error cases: Missing prompt, invalid file, etc.

## Implementation Phases

### Phase 1: Project Setup
- Create directory structure
- Create `setup.py` and `requirements.txt`
- Copy reusable modules from llm-host

### Phase 2: Core CLI
- Implement `cli.py` with argument parsing
- Implement `output_writer.py`
- Basic integration without tools

### Phase 3: Tool Integration
- Integrate `tool_executor.py`
- Implement tool call loop
- Test with MCP servers

### Phase 4: Error Handling & Polish
- Implement all exit codes
- Add comprehensive error messages
- Test edge cases

### Phase 5: Documentation
- Create README.md
- Add usage examples
- Document configuration

## Success Criteria

- ✅ Can execute single prompt and get response
- ✅ Supports reading prompt from file
- ✅ Can write output to file or stdout
- ✅ Automatically executes tool calls
- ✅ Streams output in real-time
- ✅ Proper error handling with meaningful messages
- ✅ All exit codes working correctly
- ✅ Configuration files loaded correctly
- ✅ Environment variable expansion working
- ✅ `--no-tools` flag disables MCP
- ✅ `--max-tokens` limits output length
