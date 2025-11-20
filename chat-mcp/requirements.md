# Chat w/ MCP

This is a python based LLM chat application that acts as a MCP client that integrates LLMs with MCP servers.  It is a new tool like my previous LLM Chat, but a separate project.  The too's name will be mcp-chat.
 It is a command line application that takes 1 parameter: the huggingface path to the model the user want's to work with.  The specified model must allow tool usage and be able to work with MCP servers.
after loading the model the application presents the user with a command line to enter their prompt.  the command line will be "prompt ->".  The user will enter their prompt and when they hit enter the application will pass the prompt to the model.   If the user enters "bye" or "quit" or hits control+c the application will clean up and shutdown.  when shutdowning the MCP servers should be shutdown as well.
It is the user's responsiblity to specify LLM models that support function calling.  If the user specifies a model that does not support tool calling then this is just a fancy version of LLM chat.

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
- `mcp>=0.9.0` - Official Model Context Protocol Python SDK for JSON-RPC communication
- `transformers` - For tokenizer and chat template support (mlx-lm dependency)
- `huggingface-hub` - For downloading models from HuggingFace (mlx-lm dependency)
- `rich>=13.0.0` - For colored console output and pretty formatting of tool calls

# Tool Calling / Model Integration
- Use MLX-LM's native tool support via `apply_chat_template` with tools parameter
- Convert MCP tool schemas to OpenAI-compatible format for the model:
  ```python
  openai_format = [{
      "type": "function",
      "function": {
          "name": tool["name"],
          "description": tool["description"],
          "parameters": tool["inputSchema"]
      }
  } for tool in mcp_tools]
  ```
- Models must have chat templates with tool/function calling support (e.g., Llama 3.1+, Hermes 2.5+, Mistral Instruct v0.3+)
- If a model doesn't support tool calling in its template, it will function as basic chat without MCP integration

# Error handling
- if a model fails to download show an error and exit
- if we're not able to connect to an MCP server - show an error and exit
- if the tool returns errors, show them and continue working
- if the model produces a malformed tool call - show a textual representation of the tool call with an error.
- if an MCP server becomes unresponsive or a call times out show an error and continue processing


# User Experience
- don't worry about history or context display
- maintain up to 3 turns in memory.
- To reset or clear the conversation the user will just exit the tool and restart.c
- prompts end when the user hits the enter key.  this version won't support multiline prompts
- showing a steaming response would be cool.  considering that we're showing the calls to the mcp servers.
- let tool calls interupt the stream
- mlx_lm has a built in model download display so we'll use it. 
- mlx_lm handles caching models so we'll use that.

# Configuration
- not worried about setting temperature, top_p or other settings at this time.
- not worried about max tokens.  we're running locally and it costs us nothing
- a configurable system prompt would be cool

# MCP Server Initialization/Handshaking

## Startup Sequence
```
App Start → Parse mcp.json → Launch MCP Servers → Initialize Protocol → Ready for Chat
```

## For Each MCP Server:

1. **Launch the process** using subprocess with stdio pipes
2. **Send `initialize` request** with client capabilities:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "initialize",
     "params": {
       "protocolVersion": "2024-11-05",
       "capabilities": {
         "tools": {}
       },
       "clientInfo": {
         "name": "llmchat-mcp",
         "version": "0.1.0"
       }
     }
   }
   ```
3. **Receive server capabilities** - parse what tools/resources/prompts the server offers
4. **Send `initialized` notification** - signals handshake complete
5. **Call `tools/list`** to get available tools and their schemas

## Error Handling:
- If any server fails initialization, show error and exit
- Use a timeout (e.g., 10 seconds) for initialization to catch hung servers

## Tools Registry:
Maintain a mapping of:
```python
{
  "server_name": {
    "process": <subprocess>,
    "tools": [{"name": "tool1", "description": "...", "inputSchema": {...}}, ...]
  }
}
```

## Tool Execution:
When LLM requests a tool, send:
```json
{
  "jsonrpc": "2.0",
  "id": <unique_id>,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {...}
  }
}
```

## Benefits:
- Gets full tool schemas upfront to pass to the LLM
- Validates servers are working before user interaction
- Fast tool execution during conversation (servers already running)
- Clean shutdown possible (can send proper close notifications), store it in config.json
    if no system prompt is provided, don't use one and leave it blank.

# mcp-chat requirements

## Overview
Python-based LLM chat application that acts as an MCP client, integrating LLMs with MCP servers. Command-line tool that enables local LLMs to use tools from MCP servers.

## Command Line Interface
- **Entry point**: `mcp-chat <huggingface-model-path>`
- **Prompt**: `prompt ->`
- **Exit commands**: `bye`, `quit`, or `Ctrl+C`
- Single-line prompts only (no multiline support)

## MCP Integration

### Configuration File: mcp.json
Located in same directory as program, using VS Code compatible schema:
```json
{
    "servers": {
        "localServer": {
            "type": "stdio",
            "command": "node",
            "args": ["server.js"]
        }
    }
}
```

### Transport & Protocol
- **Transport**: STDIO only for this version
- **Features**: Tools only (no resources or prompts)
- **Protocol version**: `2024-11-05`

### Server Initialization Sequence
```
App Start → Parse mcp.json → Launch MCP Servers → Initialize Protocol → Ready for Chat
```

For each MCP server:
1. Launch process using subprocess with stdio pipes
2. Send `initialize` request with client capabilities
3. Receive server capabilities
4. Send `initialized` notification
5. Call `tools/list` to get available tools and schemas
6. Maintain tools registry:
   ```python
   {
     "server_name": {
       "process": <subprocess>,
       "tools": [{"name": "tool1", "description": "...", "inputSchema": {...}}]
     }
   }
   ```

### Tool Execution
- **Behavior**: Auto-execute all tool calls (no user confirmation)
- **Display format**: Show timestamp, tool name, arguments, results/errors, execution time
- **Timeout**: 90 seconds per tool call
- **Iterations**: No limit on tool call iterations
- **Stream handling**: Tool calls interrupt the response stream

### Tool Call Display Format
For each tool execution, show:
- Timestamp
- Tool name
- Arguments sent to MCP server
- Results and errors returned from MCP server
- Total execution time

## Model Integration (MLX-LM)

### Inference Engine
- **Library**: `mlx-lm>=0.18.0`
- **Method**: `mlx_lm.generate`
- **Response**: Streaming enabled
- **Quantization**: Not required
- **Memory management**: Not a concern for this version

### Tool Calling Support
- Use MLX-LM's native tool support via `apply_chat_template` with tools parameter
- Convert MCP tool schemas to OpenAI-compatible format:
  ```python
  openai_format = [{
      "type": "function",
      "function": {
          "name": tool["name"],
          "description": tool["description"],
          "parameters": tool["inputSchema"]
      }
  } for tool in mcp_tools]
  ```
- **Compatible models**: Llama 3.1+, Hermes 2.5+, Mistral Instruct v0.3+
- **Fallback**: Models without tool support function as basic chat

### Model Loading
- Use MLX-LM's built-in download display
- Use MLX-LM's model caching

### Conversation Context
- Maintain up to 3 turns in memory
- No conversation history display
- Reset by exiting and restarting application

## Error Handling

### Fatal Errors (Exit Application)
- Model download failure
- Unable to connect to MCP server
- MCP server initialization failure (10 second timeout)

### Non-Fatal Errors (Show Error & Continue)
- Tool execution errors from MCP server
- Malformed tool calls from model (show textual representation)
- MCP server unresponsive/timeout during tool call
- Tool execution timeout (>90 seconds)

## Configuration

### System Prompt
- Configurable via `config.json` in application directory
- If not provided, no system prompt used (leave blank)

### Not Implemented (Future)
- Temperature, top_p, or other generation settings
- Maximum token limits
- Multi-line prompts
- Conversation history display

## Dependencies
Required Python packages:
- `mlx-lm>=0.18.0` - Model loading and inference
- `mcp>=0.9.0` - Official Model Context Protocol Python SDK
- `transformers` - Tokenizer and chat template support
- `huggingface-hub` - Model downloading from HuggingFace
- `rich>=13.0.0` - Colored console output and formatting

## Shutdown Behavior
On exit (`bye`, `quit`, or `Ctrl+C`):
1. Clean up resources
2. Shutdown all MCP servers (send proper close notifications)
3. Exit application

