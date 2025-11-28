# LLM Host

LLM Host is a python application that uses Apple's MLX framework to integrate LLMs.  It will use the mcp-host libary to integrate MCP servers to provide tools to the LLMs.
This application will be like chat-mcp (see chat-mcp/requirements.md), except mcp-host will be used for integrating mcp servers.
The application will take 1 command line parameter that is the Huggingface path to the LLM to be loaded.  For example:
    llm-host ibm-granite/granite-4.0-1b
this will cause the application to use IBM's granite LLM.

Once the mcp servers have been started and the llm has been loaded and is ready a command line saying "prompt ->" will be displayed.  The user can enter their prompt and when they hit enter.  when the enter key is pressed the prompt will be sent to the llm for processing.  the llm's response will be displayed on the screen.  If the user enters "bye" or "quit" or hits control+c the application will clean up and shutdown.  when shuting down the MCP servers should be shutdown as well.

# MCP 
The MCP server configuration will be stored in a file called mcp.json and will be in the same directory as the program.  The schema will be the same as used with vs code, for example:
    {
        "servers": {
            "localServer": {
                "type": "stdio",
                "command": "node",
                "args": ["server.js"]
            }
        }
    }
when the model request to use a tool the app will auto-execute the request.  
Each request will be displayed on the console with the time, the tool name and a summary of what is being done.  
    - show the arguments sent to the MCP server
    - show the results and errors the MCP server returns
    - the total execution time from when the call is initially made and when the MCP server finishes its work
There won't be a limit on call iterations.
If a tool takes more than 90 seconds to respond consider it a timeout, show an error and continue with the rest of the generation
    
For this version we will only support MCP servers that use STDIO as the transport.  
For this version we will just use tools in MCP servers.

# MLX
Apple's MLX-LM library will be used for LLM inference.  No specific quantization will be required and we're not worried about memory management.
The app will use mlx_lm.generate

# Dependencies
Required Python packages:
- `mlx-lm>=0.18.0` - For model loading and inference
- `transformers` - For tokenizer and chat template support (mlx-lm dependency)
- `huggingface-hub` - For downloading models from HuggingFace (mlx-lm dependency)
- `rich>=13.0.0` - For colored console output and pretty formatting of tool calls

# Model loading
- MLX has a builtin loading indicator that we'll use
- If the requested model either does not exist or is not accessible to the user we'll show an error and exit.
- We'll take advantage of MLX's builtin model cache.

## Conversation Management
- Maintain full conversation history for context
- No artificial limit on history length (rely on model's context window)
- Each tool call and result is added to history
- History is reset on app restart

## Console Output Format
- User prompts: `prompt -> [user input]`
- Tool calls: `[HH:MM:SS] Calling tool: <tool_name>(<args>) ...`
- Tool results: `[HH:MM:SS] Result: <summary> (took X.XXs)`
- Tool errors: `[HH:MM:SS] ERROR: <error message> (took X.XXs)`
- Assistant responses: `assistant -> [response]`
- Streaming tokens as they generate (typewriter effect)

# Error display
- if an MCP server returns an error: continue with what the model does next

# System prompt
- the system prompt will be stored in config.json.  the prompt will be stored in a field named "SystemPrompt".  
- the application will append the available tools and resources to the system prompt so the llm will be aware of their availablity.

## Model Requirements
- Must be compatible with mlx_lm
- Should support function/tool calling (models with appropriate chat templates)
- Recommended models: granite-3.1+, llama-3.1+, qwen-2.5+
- Model will be automatically downloaded from HuggingFace if not cached

## Startup Sequence
1. Load mcp.json configuration
2. Start all MCP servers (using mcp-host library)
3. Download/load MLX model from HuggingFace
4. Initialize conversation with empty history
5. Display "Ready. Type your prompt or 'quit' to exit."
6. Show `prompt ->` and wait for input

# Requirements

## Core Requirements (CR)

**CR1: Command-Line Interface**
- Application name: `llm-host`
- Accept exactly one required argument: HuggingFace model path
- Example: `llm-host ibm-granite/granite-4.0-1b`
- Exit with error message if model path not provided

**CR2: MCP Server Integration**
- Use mcp-host library for all MCP server management
- Read MCP server configuration from `mcp.json` in the application directory
- Support VSCode-compatible mcp.json schema with "servers" object
- Only support STDIO transport type for this version
- Only use tools from MCP servers (not prompts or resources)

**CR3: MLX Model Integration**
- Use `mlx_lm.generate` for inference
- Use MLX's built-in model loading indicator
- Use MLX's built-in model cache
- No specific quantization requirements
- No memory management constraints

**CR4: Conversation Management**
- Maintain full conversation history throughout session
- No artificial limit on history length (use model's context window)
- Include user prompts, assistant responses, tool calls, and tool results in history
- Reset history only on application restart

**CR5: Tool Execution**
- Auto-execute all tool requests without user confirmation
- Support unlimited tool call iterations per generation
- Apply 90-second timeout per tool call
- Continue generation if tool times out or returns error
- Display detailed tool execution information to console

**CR6: User Input/Output**
- Display `prompt ->` to indicate ready for user input
- Accept user input via stdin
- Recognize "bye", "quit" as exit commands
- Support Ctrl+C for graceful shutdown
- Stream assistant response tokens as they generate (typewriter effect)

**CR7: Graceful Shutdown**
- Shutdown all MCP servers when application exits
- Clean up resources on exit (via "bye", "quit", or Ctrl+C)
- Ensure mcp-host library properly closes all server processes

**CR8: System Prompt Configuration**
- Load system prompt from `config.json` file in application directory
- Read from "SystemPrompt" field in config.json
- Append available tool definitions to system prompt automatically
- Tool definitions must include tool name, description, and parameters

**CR9: Error Handling**
- Show error and exit if model does not exist or is not accessible
- Continue generation if MCP server returns error
- Display all MCP server errors to console
- Handle tool timeouts gracefully without crashing

**CR10: Console Output Formatting**
- Use rich library for colored and formatted console output
- Display user prompts: `prompt -> [user input]`
- Display tool calls: `[HH:MM:SS] Calling tool: <tool_name>(<args>) ...`
- Display tool results: `[HH:MM:SS] Result: <summary> (took X.XXs)`
- Display tool errors: `[HH:MM:SS] ERROR: <error message> (took X.XXs)`
- Display assistant responses: `assistant -> [response]`

## Functional Requirements (FR)

**FR1: Configuration Loading**
- Load mcp.json at startup (fail if missing)
- Load config.json at startup (fail if missing or SystemPrompt field missing)
- Validate JSON syntax and schema
- Parse server configurations from mcp.json

**FR2: MCP Server Lifecycle**
- Initialize mcp-host library with mcp.json configuration
- Start all configured MCP servers before showing prompt
- Query available tools from all servers
- Maintain server connections throughout session
- Shutdown all servers on application exit

**FR3: Model Loading**
- Accept HuggingFace model path as command-line argument
- Download model from HuggingFace if not in cache
- Show MLX's built-in loading progress indicator
- Validate model is compatible with mlx_lm
- Exit with clear error if model loading fails

**FR4: Tool Discovery**
- Query all available tools from MCP servers via mcp-host
- Parse tool schemas (name, description, parameters)
- Format tool definitions for inclusion in system prompt
- Update system prompt with tool definitions before first prompt

**FR5: Conversation Loop**
- Display "Ready. Type your prompt or 'quit' to exit." after initialization
- Show `prompt ->` and wait for user input
- Accept multi-line input (until Enter is pressed)
- Add user message to conversation history
- Generate response using mlx_lm.generate with full history
- Parse response for tool calls
- Execute any tool calls via mcp-host
- Add tool results to conversation history
- Continue generation if tool calls were made
- Display final assistant response
- Return to `prompt ->` for next input

**FR6: Tool Execution Flow**
- Detect tool calls in model output
- For each tool call:
  - Display `[HH:MM:SS] Calling tool: <name>(<args>)`
  - Call tool via mcp-host library with 90-second timeout
  - Measure execution time
  - Display result or error with execution time
  - Add tool result to conversation history
- Support multiple tool calls in single generation
- Support multiple rounds of tool calling (no iteration limit)

**FR7: Response Display**
- Stream tokens as they are generated (typewriter effect)
- Display assistant response with `assistant ->` prefix
- Preserve formatting and newlines in responses
- Use rich library for colored output

**FR8: Exit Handling**
- Recognize "bye" or "quit" commands (case-insensitive)
- Catch Ctrl+C (SIGINT) signal
- Call mcp-host shutdown for all servers
- Exit cleanly with status code 0

**FR9: Error Recovery**
- Continue generation if tool call fails or times out
- Display error message for failed tool calls
- Don't crash on MCP server errors
- Provide helpful error messages for configuration issues

**FR10: Tool Information Display**
- Show tool name being called
- Show all arguments being passed to tool
- Show complete result or error from tool
- Show execution time for each tool call
- Format output with timestamps in HH:MM:SS format

## Technical Requirements (TR)

**TR1: Python Version**
- Require Python 3.10 or higher
- Use type hints throughout codebase
- Follow async/await patterns where appropriate

**TR2: Dependencies**
- mlx-lm >= 0.18.0 (MLX model loading and inference)
- transformers (tokenizer and chat template support)
- huggingface-hub (model downloading)
- rich >= 13.0.0 (console formatting)
- mcp-host library (local installation)

**TR3: Configuration Files**
- mcp.json: MCP server configuration (VSCode schema)
- config.json: Application configuration with SystemPrompt field
- Both files must be in same directory as application

**TR4: File Structure**
```
llm-host/
├── llmhost/              # Main package
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── cli.py            # Command-line interface
│   ├── model.py          # MLX model wrapper
│   ├── conversation.py   # Conversation history
│   ├── tool_executor.py  # Tool execution via mcp-host
│   └── config.py         # Configuration loading
├── examples/
│   ├── config.json.example
│   └── mcp.json.example
├── setup.py
├── requirements.txt
└── README.md
```

**TR5: Logging**
- Use rich library for all console output
- Include timestamps for all tool-related messages
- Format timestamps as HH:MM:SS
- Use appropriate colors for different message types

**TR6: Conversation History Format**
- Use standard chat message format: list of dicts with "role" and "content"
- Roles: "system", "user", "assistant", "tool"
- Include tool calls and results in history
- Preserve exact order of all messages

**TR7: Tool Call Format**
- Parse tool calls from model output (format depends on model's chat template)
- Extract tool name and arguments
- Pass to mcp-host library using: `await host.call_tool(name, arguments, timeout=90.0)`
- Handle timeout exceptions from mcp-host

**TR8: System Prompt Construction**
- Load base prompt from config.json["SystemPrompt"]
- Query available tools from mcp-host: `await host.get_tools()`
- Format tools as JSON schema or text description
- Append tool definitions to system prompt
- Insert complete system prompt as first message in conversation history

**TR9: Signal Handling**
- Register SIGINT (Ctrl+C) handler
- Call cleanup functions on signal
- Shutdown MCP servers gracefully
- Exit with code 0 after cleanup

**TR10: Async Execution**
- Use asyncio for MCP server operations (via mcp-host)
- Use async context manager for mcp-host: `async with MCPHost() as host:`
- Handle async tool execution properly
- Coordinate between sync MLX calls and async MCP operations

**TR11: Error Messages**
- Model not found: "Error: Model '{model_path}' not found or not accessible"
- Config missing: "Error: {filename} not found in application directory"
- Invalid JSON: "Error: Invalid JSON in {filename}: {error details}"
- Tool timeout: "[HH:MM:SS] ERROR: Tool '{name}' timed out after 90.0s"
- MCP error: "[HH:MM:SS] ERROR: {error message from MCP server} (took X.XXs)"

**TR12: Model Compatibility**
- Must work with mlx_lm library
- Recommended: Models with function calling support
  - granite-3.1 and later
  - llama-3.1 and later  
  - qwen-2.5 and later
- Use model's chat template for formatting messages
- Support standard chat message roles
