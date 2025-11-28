# LLM Host Implementation Plan

## Overview
This plan outlines the implementation of LLM Host, a command-line application that integrates Apple's MLX framework for LLM inference with MCP servers for tool capabilities. The implementation follows the requirements specified in `requirements.md`.

## Project Structure
```
llm-host/
├── llmhost/              # Main package
│   ├── __init__.py       # Package initialization, version
│   ├── __main__.py       # Entry point for python -m llmhost
│   ├── cli.py            # Command-line argument parsing and main loop
│   ├── config.py         # Configuration file loading (config.json, mcp.json)
│   ├── model.py          # MLX model wrapper and inference
│   ├── conversation.py   # Conversation history management
│   ├── tool_executor.py  # Tool execution via mcp-host library
│   └── console.py        # Rich console output formatting
├── examples/
│   ├── config.json.example    # Example system prompt configuration
│   └── mcp.json.example       # Example MCP server configuration
├── setup.py              # Package installation
├── requirements.txt      # Dependencies
├── README.md            # User documentation
└── plan.md              # This file
```

## Implementation Phases

### Phase 1: Foundation & Configuration (CR1, FR1, TR3, TR4)
**Goal**: Set up project structure and configuration loading

**Files to create**:
1. `llmhost/__init__.py`
   - Package version
   - Export main entry point

2. `llmhost/config.py`
   - `load_config()` - Load and validate config.json
   - `load_mcp_config()` - Load and validate mcp.json
   - Validate JSON syntax and required fields
   - Return parsed configuration dictionaries
   - Error handling for missing files and invalid JSON (TR11)

3. `examples/config.json.example`
   - Example SystemPrompt field
   - Documentation comments

4. `examples/mcp.json.example`
   - Example STDIO server configuration
   - Documentation comments

5. `requirements.txt`
   - mlx-lm>=0.18.0
   - rich>=13.0.0
   - mcp-host (local path or git+https)

**Success criteria**:
- Configuration files load successfully
- Appropriate errors shown for missing/invalid files
- Example files demonstrate proper format

---

### Phase 2: Console Output (CR10, TR5)
**Goal**: Implement rich console formatting for all output types

**Files to create**:
1. `llmhost/console.py`
   - `Console` class wrapping rich.Console
   - `print_prompt()` - Display "prompt ->" and read input
   - `print_user_input(text)` - Display user input
   - `print_tool_call(tool_name, args)` - Display tool call with timestamp
   - `print_tool_result(result, duration)` - Display result with timing
   - `print_tool_error(error, duration)` - Display error with timing
   - `print_assistant_response(text)` - Display assistant response
   - `stream_token(token)` - Display single token (typewriter effect)
   - `print_ready()` - Display "Ready. Type your prompt or 'quit' to exit."
   - Color coding: user (cyan), assistant (green), tool calls (yellow), errors (red)
   - Timestamp format: HH:MM:SS

**Success criteria**:
- All message types display with proper formatting
- Timestamps include hours, minutes, seconds
- Colors distinguish different message types
- Streaming tokens work smoothly

---

### Phase 3: Conversation History (CR4, TR6)
**Goal**: Manage conversation history with proper message format

**Files to create**:
1. `llmhost/conversation.py`
   - `ConversationHistory` class
   - `add_system_message(content)` - Add system prompt
   - `add_user_message(content)` - Add user input
   - `add_assistant_message(content)` - Add LLM response
   - `add_tool_call(name, args, call_id)` - Add tool call to history
   - `add_tool_result(call_id, result)` - Add tool result to history
   - `get_messages()` - Return full history as list of dicts
   - `clear()` - Reset history (not used but good to have)
   - Message format: `{"role": "user|assistant|system|tool", "content": "..."}`
   - Support for tool call/result format based on model's chat template

**Success criteria**:
- History maintains chronological order
- All message types properly formatted
- Can retrieve complete history for model input
- Tool calls and results properly linked

---

### Phase 4: MLX Model Integration (CR3, FR3, FR7, TR1)
**Goal**: Load and run MLX models with streaming output

**Files to create**:
1. `llmhost/model.py`
   - `MLXModel` class
   - `__init__(model_path)` - Store model path
   - `load()` - Load model using mlx_lm (show MLX's loading indicator)
   - `generate(messages, stream=True)` - Generate response with streaming
   - `get_chat_template()` - Get model's chat template for formatting
   - Error handling for missing/incompatible models (TR11)
   - Use mlx_lm.generate for inference
   - Support streaming token output
   - Detect tool calls in model output

**Success criteria**:
- Models load successfully from HuggingFace
- MLX's loading indicator displays
- Tokens stream to console as generated
- Tool calls detected in model output
- Clear error if model not found

---

### Phase 5: MCP Integration & Tool Execution (CR2, CR5, FR2, FR4, FR6, TR2, TR7, TR10)
**Goal**: Integrate mcp-host library for tool execution

**Files to create**:
1. `llmhost/tool_executor.py`
   - `ToolExecutor` class
   - `async __init__(mcp_config)` - Initialize mcp-host with config
   - `async start()` - Start all MCP servers
   - `async get_tools()` - Query available tools from all servers
   - `async execute_tool(name, args, timeout=90.0)` - Execute single tool
   - `async shutdown()` - Shutdown all MCP servers
   - `format_tools_for_prompt()` - Format tool definitions for system prompt
   - Track execution time for each tool call
   - Handle timeouts (90 seconds)
   - Handle MCP errors gracefully
   - Return results for addition to conversation history
   - Use async context manager pattern

**Success criteria**:
- MCP servers start successfully
- Available tools discovered and formatted
- Tool calls execute with proper timeout
- Execution time measured and displayed
- Errors handled without crashing
- Graceful shutdown of all servers

---

### Phase 6: Main CLI & Event Loop (CR1, CR6, CR8, CR9, FR5, FR8, FR9, TR9)
**Goal**: Tie everything together in main application loop

**Files to create**:
1. `llmhost/cli.py`
   - `main()` - Main entry point
   - Parse command-line arguments (model path)
   - Load configurations (config.json, mcp.json)
   - Initialize console output
   - Initialize tool executor (async)
   - Start MCP servers
   - Load MLX model
   - Build system prompt with tool definitions (CR8, TR8)
   - Initialize conversation history with system message
   - Main loop:
     - Display prompt and read user input
     - Check for exit commands ("bye", "quit")
     - Add user message to history
     - Generate response (may include tool calls)
     - Execute any tool calls via tool_executor
     - Add tool results to history
     - Continue generation if tools were called
     - Display final response
     - Repeat
   - Signal handling (Ctrl+C) with cleanup
   - Error recovery for tool failures

2. `llmhost/__main__.py`
   - Entry point for `python -m llmhost`
   - Call `cli.main()`

**Success criteria**:
- Accepts model path as command-line argument
- Loads all configurations successfully
- Starts MCP servers before showing prompt
- System prompt includes tool definitions
- Main loop processes user input
- Tool calls execute automatically
- Multiple tool iterations supported
- Graceful exit on "bye", "quit", or Ctrl+C
- All resources cleaned up on exit

---

### Phase 7: Packaging & Documentation (CR7, TR4)
**Goal**: Make the application installable and document usage

**Files to create**:
1. `setup.py`
   - Package metadata (name, version, author, description)
   - Entry point: `llm-host = llmhost.cli:main`
   - Dependencies from requirements.txt
   - Python version requirement: >=3.10

2. `README.md`
   - Project description
   - Installation instructions
   - Configuration file setup (mcp.json, config.json)
   - Usage examples
   - Recommended models
   - Troubleshooting section
   - Example session transcript

**Success criteria**:
- Package installs with `pip install -e .`
- `llm-host` command available after install
- README clearly explains setup and usage
- Example configurations work out of the box

---

## Implementation Order

1. **Phase 1** (Foundation & Configuration) - Required for all other phases
2. **Phase 2** (Console Output) - Required for visibility into other phases
3. **Phase 3** (Conversation History) - Required for Phase 4 and Phase 6
4. **Phase 4** (MLX Model Integration) - Can develop in parallel with Phase 5
5. **Phase 5** (MCP Integration) - Can develop in parallel with Phase 4
6. **Phase 6** (Main CLI) - Requires all previous phases
7. **Phase 7** (Packaging) - Final polish

## Key Dependencies Between Phases

```
Phase 1 (Config)
    ├─> Phase 2 (Console)
    ├─> Phase 3 (Conversation)
    ├─> Phase 4 (MLX Model)
    │       └─> Phase 6 (CLI)
    └─> Phase 5 (Tool Executor)
            └─> Phase 6 (CLI)
                    └─> Phase 7 (Packaging)
```

## Testing Strategy

After each phase, test the implemented functionality:

**Phase 1**: Test loading valid and invalid configurations
**Phase 2**: Test all console output methods with sample data
**Phase 3**: Test adding various message types and retrieving history
**Phase 4**: Test loading a real model and generating simple responses
**Phase 5**: Test with a real MCP server (e.g., calculator)
**Phase 6**: Integration test with end-to-end conversation including tool calls
**Phase 7**: Install package and run from command line

## Success Checkpoints

### Checkpoint 1: Configuration Loading Works
- ✅ config.json loads successfully
- ✅ mcp.json loads successfully
- ✅ Appropriate errors for missing/invalid files

### Checkpoint 2: Console Output Works
- ✅ All message types display correctly
- ✅ Colors and formatting applied
- ✅ Timestamps in HH:MM:SS format

### Checkpoint 3: Conversation History Works
- ✅ Messages added in correct order
- ✅ History retrieved as proper format
- ✅ Tool calls/results properly structured

### Checkpoint 4: Model Loading & Generation Works
- ✅ Model downloads and loads from HuggingFace
- ✅ Tokens stream to console
- ✅ Tool calls detected in output

### Checkpoint 5: MCP Integration Works
- ✅ MCP servers start successfully
- ✅ Tools discovered and formatted
- ✅ Tool execution works with timeout
- ✅ Graceful shutdown

### Checkpoint 6: End-to-End Flow Works
- ✅ Complete startup sequence
- ✅ User can enter prompts
- ✅ Model generates responses
- ✅ Tools execute automatically
- ✅ Multiple tool iterations work
- ✅ Exit commands work
- ✅ Ctrl+C cleanup works

### Checkpoint 7: Package Installation Works
- ✅ `pip install -e .` succeeds
- ✅ `llm-host` command available
- ✅ Example configurations work

## Risk Mitigation

**Risk**: MLX and mcp-host async/sync coordination
- **Mitigation**: Use asyncio.run() to wrap async mcp operations, or run MLX in thread pool

**Risk**: Tool call parsing from model output
- **Mitigation**: Use model's chat template, handle multiple formats, graceful fallback

**Risk**: Long tool execution blocking user experience
- **Mitigation**: Show real-time status updates, implement timeout, allow continuation

**Risk**: MCP server crashes during session
- **Mitigation**: Catch exceptions, continue generation, display error clearly

## Future Enhancements (Not in This Version)

- Support for MCP prompts and resources
- Support for SSE transport
- Configuration UI or interactive setup
- Conversation history persistence
- Multi-turn tool execution visualization
- Performance metrics and logging

## Notes

- The mcp-host library is assumed to be installed locally from `/Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host`
- We'll use `pip install -e ../mcp-host` to install it in development mode
- All async operations use asyncio with proper context managers
- Error handling is comprehensive but doesn't crash the application
- User experience is prioritized with clear output formatting and real-time feedback
