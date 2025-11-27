# MCP Host 

I need to create an MCP Client host that will start up MCP servers, get the services the server offers and then be able to shut them down cleanly.  The idea is that the host will be a module that is part of an AI/ML application.  The application will be responsible for everything outside of the MCP features that the MCP host handles.  The host will provide the application a clean interface (api) that allows the application to start the MCP servers, get their capabilities and then make use of the MCP servers.  The MCP host will handle the details of things like starting and shutting down the servers, getting the server's capabilities and then routing calls to the servers.  
As an example, once we have the host working we'll integrate it into an application that will load an LLM, send the LLM prompts and the LLM will use the available tools to complete the tasks the prompt requires.

## basic features
the host will use STDIO
the host will use mcp.json for configuration.
the host will start and initialize each server listed in the configuration file.
the host will interogate each server for its capabilities (prompts, resources, tools) and store them in a server capabilities object
the host will be implemented using python
the host will be used by LLM clients to provide MCP services to LLMs and user
the host will be a module that can be imported in to other applications

## Configuration
the host will support hot-reload of mcp.json without full restart
the host will support environment variable expansion in config
the host will support server-specific configuration (timeouts, resource limits)
the host will support different transport types (stdio, SSE, WebSocket)
the mcp.json file will use the schema followed by tools like vscode:
    - the format will look like:
       {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/jakewatkins/source/trashcode/local-llm/mlx-lab/chat-mcp/"]
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
    this example loads two servers, both using npx.  The brave-search server's configuration demonstrates using variable expansion so secrets can be hidden

## Capabilities discovery
    - after all of the mcp servers have started the host will then send the request tools/list to each server to build a list of tools available.
    - the host will provide an method get_tools that will return all servers with all of their capabilities (tools, prompts, resources)
    - we don't need to query by individual server.  that application will cache the response
    - we don't need to filter the capabilities by type or metadata - the application will be responsible for that

## Host interface
the host will provide the following methods:
    - The host will proivde an initialize method that will start and then call the initialize method on each mcp server that has been configured in mcp.json
        - if there are duplicate servers or servers that have the same name the host will return a configuration error to the application and not start any mcp servers
        - if an mcp server fails to start with in a configurable amount of time the host will return an error message and not start any mcp servers (it will shutdown any that have started)
    - the host will provide a shutdown method that will shutdown all of the mcp servers and free any resources the host has been using
    - the host will provide a call_tool method that will route tool calls to the appropriate server.
        - the mcp standard requires the tool names to be in the format of {server}.{tool} so there should not be conclicts because two servers have the same tool name.
        - if the host is not able to determine which server the call should be routed to it will return an error message to the application
        - the host will validate that the incoming parameters match the requested tool.  if they do not it will return an error message
    - the host will provide a get_prompt method that will route the request to the appropriate server
        - if the host is not able to determine which server the call should be routed to it will return an error message to the application
    - the host will provide a get_resource method that will route the request to the appropriate server
        - if the host is not able to determine which server the call should be routed to it will return an error message to the application
    - the host will act as a proxy for requests coming from the server.  The application will have to register a call back function with the host that will receive all requests from the servers the host contains.

## Session & Lifecycle Management
the host will perform server health checks and automatic restart on failure
the host will implement graceful shutdown with timeout handling for unresponsive servers
the host will implement server initialization retry logic with exponential backoff

## Request Routing & Execution
the host will route tool calls to the appropriate server
the host will handle prompt/resource requests from servers
the host will support sampling/LLM requests from servers
the host will implement request timeout handling and cancellation

## State & Monitoring
the host will track active server connections and their states
the host will implement logging for debugging (server startup/shutdown, requests, errors)
the host will track metrics/statistics (request counts, latencies, error rates)
the host will detect capability changes when servers update their capabilities
the host will not ping servers.  
the host will track server health from usage (prompt, resource and tool successful tool calls).  If a call times out or returns an error indicating the server has crashed the server's state will be marked as unavailable.
the host will no automatically restart servers.
the host will return an error to the application indicating a server is unavailable if a server's state has been set to unavailable.
the host will remove the server and its capabilities from the list of servers when the server's state has been set to unavailable.



## Error Handling
the host will implement retry logic for failed requests
the host will propagate errors to clients with context
the host will implement fallback strategies when servers are unavailable

## Caching
the host will cache server responses for resources and prompts

## Server Dependency Management
the host will manage server dependencies and start servers in order

# Testing

- The test that will demonstrate that the host meets my requirements will be as follows:
    there will be an mcp.json file used to configure the test application's mcp servers.  it will contain configuration for 2 mcp server - brave-search-mcp, and @modelcontextprotocol/server-filesystem
    A python application will use the host module to host a set of MCP servers.  The mcp server's configuration will be stored in mcp.json which will be passed into the mcp host object.
    then the application will get the list of servers and capabilities from the mcp host.
    The application will check to see that each server has the expected tools available and that the tools take the expected parameters by name and type.
    The application will then tell the mcp host to shutdown the servers
    If the servers start, and the list of servers, tools, and parameters match and the servers shutdown without errors the test will have passed.

# Requirements

## Functional Requirements

### FR1: Configuration Management
- FR1.1: The host shall load server configuration from an mcp.json file following the VSCode schema format
- FR1.2: The host shall support environment variable expansion using ${VAR_NAME} syntax
- FR1.3: The host shall validate that server names are unique across the configuration
- FR1.4: The host shall return a configuration error if duplicate server names are detected
- FR1.5: The host shall support per-server configuration including: command, args, env, type, and resource limits
- FR1.6: The host shall support hot-reload of mcp.json without restarting already-running servers
- FR1.7: The host shall validate the JSON schema on load and report errors with specific line/field information

### FR2: Server Lifecycle Management
- FR2.1: The host shall provide an `initialize()` method that starts all configured MCP servers
- FR2.2: The host shall start servers using STDIO transport as the primary transport type
- FR2.3: The host shall support future transport types (SSE, WebSocket) through configuration
- FR2.4: The host shall send initialize requests to each server after process startup
- FR2.5: The host shall wait for initialization with a configurable timeout (default: 30 seconds)
- FR2.6: The host shall shutdown all servers if any server fails to initialize within the timeout
- FR2.7: The host shall return an error message to the application if initialization fails
- FR2.8: The host shall provide a `shutdown()` method that gracefully terminates all servers
- FR2.9: The host shall implement graceful shutdown with configurable timeout (default: 10 seconds)
- FR2.10: The host shall force-terminate unresponsive servers after timeout expires
- FR2.11: The host shall free all resources (processes, pipes, memory) on shutdown

### FR3: Capability Discovery
- FR3.1: The host shall query each server for tools using the `tools/list` request after initialization
- FR3.2: The host shall query each server for prompts using the `prompts/list` request after initialization
- FR3.3: The host shall query each server for resources using the `resources/list` request after initialization
- FR3.4: The host shall store all capabilities in a server capabilities object indexed by server name
- FR3.5: The host shall provide a `get_tools()` method returning all servers with their complete capabilities
- FR3.6: The host shall detect capability changes when servers send notifications
- FR3.7: The host shall update the cached capabilities when changes are detected

### FR4: Request Routing
- FR4.1: The host shall provide a `call_tool(tool_name, parameters)` method for tool invocation
- FR4.2: The host shall parse tool names in the format `{server}.{tool}` to determine routing
- FR4.3: The host shall return an error if the server name cannot be determined from the tool name
- FR4.4: The host shall validate that the target server exists and is available
- FR4.5: The host shall validate that incoming parameters match the tool's schema
- FR4.6: The host shall return validation errors if parameters don't match the schema
- FR4.7: The host shall route the validated tool call to the appropriate server
- FR4.8: The host shall provide a `get_prompt(prompt_name)` method that routes to the appropriate server
- FR4.9: The host shall provide a `get_resource(resource_uri)` method that routes to the appropriate server
- FR4.10: The host shall implement request timeout handling with configurable limits
- FR4.11: The host shall support request cancellation

### FR5: Server Proxy & Callbacks
- FR5.1: The host shall act as a proxy for requests originating from MCP servers
- FR5.2: The host shall allow the application to register a callback function for server-initiated requests
- FR5.3: The host shall route sampling/LLM requests from servers to the registered callback
- FR5.4: The host shall route prompt/resource requests from servers to the registered callback if needed
- FR5.5: The host shall forward callback responses back to the originating server

### FR6: Health Monitoring & State Management
- FR6.1: The host shall track the state of each server (starting, ready, unavailable, shutdown)
- FR6.2: The host shall monitor server health based on successful request completions
- FR6.3: The host shall mark a server as unavailable when a request times out
- FR6.4: The host shall mark a server as unavailable when an error indicates server crash
- FR6.5: The host shall NOT automatically restart servers that become unavailable
- FR6.6: The host shall return an error to the application when routing requests to unavailable servers
- FR6.7: The host shall remove unavailable servers and their capabilities from the active server list
- FR6.8: The host shall NOT implement periodic ping/health check requests

### FR7: Error Handling
- FR7.1: The host shall implement retry logic for failed requests with exponential backoff
- FR7.2: The host shall propagate all errors to the application with full context (server name, error type, message)
- FR7.3: The host shall implement fallback strategies when servers are unavailable (return cached data if available)
- FR7.4: The host shall log all errors with severity levels (debug, info, warning, error, critical)
- FR7.5: The host shall validate all server responses against MCP protocol schema
- FR7.6: The host shall handle malformed responses gracefully and return structured errors

### FR8: Caching
- FR8.1: The host shall cache resource responses with configurable TTL (default: 5 minutes)
- FR8.2: The host shall cache prompt definitions from servers
- FR8.3: The host shall invalidate cache entries when server capabilities change
- FR8.4: The host shall support cache bypass via request parameters
- FR8.5: The host shall implement LRU eviction when cache size limits are reached

### FR9: Logging & Observability
- FR9.1: The host shall log all server lifecycle events (start, initialized, unavailable, shutdown)
- FR9.2: The host shall log all requests and responses with timestamps and latency
- FR9.3: The host shall track metrics per server: request count, success rate, error rate, average latency
- FR9.4: The host shall provide structured logging output in JSON format
- FR9.5: The host shall support configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- FR9.6: The host shall expose metrics via a `get_metrics()` method

### FR10: Server Dependency Management
- FR10.1: The host shall support server dependency declarations in configuration
- FR10.2: The host shall build a dependency graph from configuration
- FR10.3: The host shall start servers in topological order based on dependencies
- FR10.4: The host shall start independent servers in parallel
- FR10.5: The host shall wait for dependency servers to reach "ready" state before starting dependents
- FR10.6: The host shall detect circular dependencies and return configuration errors

## Technical Requirements

### TR1: Architecture & Design
- TR1.1: The host shall be implemented in Python 3.10 or higher
- TR1.2: The host shall be packaged as an importable Python module
- TR1.3: The host shall use asyncio for all I/O operations and concurrent server management
- TR1.4: The host shall use type hints throughout the codebase for static type checking
- TR1.5: The host shall implement the MCP protocol according to the official specification
- TR1.6: The host shall have a modular architecture with clear separation of concerns:
  - Configuration loader
  - Server process manager
  - Protocol handler (JSON-RPC)
  - Capability registry
  - Request router
  - Cache manager
  - Logging/metrics collector
- TR1.7: The host shall minimize external dependencies (prefer standard library)

### TR2: Process Management
- TR2.1: The host shall use `asyncio.create_subprocess_exec()` for server process creation
- TR2.2: The host shall manage STDIO pipes (stdin, stdout, stderr) for each server process
- TR2.3: The host shall handle process signals (SIGTERM, SIGINT) correctly for graceful shutdown
- TR2.4: The host shall use SIGKILL for force termination after timeout
- TR2.5: The host shall prevent zombie processes through proper cleanup and wait operations
- TR2.6: The host shall isolate each server in its own process
- TR2.7: The host shall capture and log stderr from server processes
- TR2.8: The host shall monitor child process exit codes and log abnormal terminations

### TR3: Communication Protocol
- TR3.1: The host shall implement JSON-RPC 2.0 over STDIO
- TR3.2: The host shall use newline-delimited JSON for message framing
- TR3.3: The host shall generate unique message IDs for request/response correlation
- TR3.4: The host shall support notification messages (requests without response)
- TR3.5: The host shall implement proper timeout handling for request/response pairs
- TR3.6: The host shall validate all JSON messages against MCP protocol schemas
- TR3.7: The host shall handle UTF-8 encoding/decoding correctly
- TR3.8: The host shall implement MCP protocol version negotiation (currently 2024-11-05)

### TR4: Concurrency & Async Design
- TR4.1: The host shall use a single asyncio event loop for all operations
- TR4.2: The host shall use `asyncio.Queue` for message passing between components
- TR4.3: The host shall use `asyncio.Lock` for protecting shared state (capabilities, metrics)
- TR4.4: The host shall use `asyncio.wait_for()` for implementing timeouts
- TR4.5: The host shall handle concurrent requests to different servers efficiently
- TR4.6: The host shall implement proper exception handling in async tasks
- TR4.7: The host shall use `asyncio.gather()` for parallel server startup when possible

### TR5: Data Structures
- TR5.1: The host shall use dataclasses or Pydantic models for all protocol messages
- TR5.2: The host shall maintain a registry: `Dict[server_name, ServerInfo]` where ServerInfo includes:
  - Process handle
  - Communication pipes
  - State (starting, ready, unavailable, shutdown)
  - Capabilities (tools, prompts, resources)
  - Metrics (request count, error count, latencies)
- TR5.3: The host shall use `enum.Enum` for server states
- TR5.4: The host shall implement a capability schema using type-safe structures
- TR5.5: The host shall use a cache structure: `Dict[cache_key, CacheEntry]` with TTL support

### TR6: Error Handling & Validation
- TR6.1: The host shall define custom exception classes for different error types:
  - ConfigurationError
  - ServerStartupError
  - ServerUnavailableError
  - ValidationError
  - TimeoutError
  - ProtocolError
- TR6.2: The host shall validate configuration using JSON schema validation
- TR6.3: The host shall validate tool parameters against tool schemas before routing
- TR6.4: The host shall validate all incoming/outgoing messages against MCP schema
- TR6.5: The host shall implement exponential backoff: initial=1s, max=30s, max_retries=3
- TR6.6: The host shall include traceback information in error logs for debugging

### TR7: Testing Requirements
- TR7.1: The host shall have unit tests with >80% code coverage
- TR7.2: The host shall have integration tests using the test scenario described in the Testing section
- TR7.3: The host shall include tests with mock MCP servers for edge cases
- TR7.4: The host shall include performance tests for request routing overhead (<10ms)
- TR7.5: The host shall include tests for all error conditions and edge cases
- TR7.6: The host shall include tests for concurrent request handling
- TR7.7: The host shall validate against the MCP protocol specification

### TR8: Configuration Schema
- TR8.1: The host shall validate mcp.json against this JSON schema:
  ```json
  {
    "type": "object",
    "properties": {
      "servers": {
        "type": "object",
        "patternProperties": {
          ".*": {
            "type": "object",
            "properties": {
              "type": { "type": "string", "enum": ["stdio", "sse", "websocket"] },
              "command": { "type": "string" },
              "args": { "type": "array", "items": { "type": "string" } },
              "env": { "type": "object" },
              "timeout": { "type": "number" },
              "dependencies": { "type": "array", "items": { "type": "string" } }
            },
            "required": ["type", "command"]
          }
        }
      }
    },
    "required": ["servers"]
  }
  ```
- TR8.2: The host shall provide clear error messages referencing the specific configuration path
- TR8.3: The host shall expand environment variables before server startup

### TR9: Performance Requirements
- TR9.1: The host shall add <10ms overhead for routing requests to servers
- TR9.2: The host shall start independent servers in parallel (not sequentially)
- TR9.3: The host shall initialize all servers within 60 seconds (configurable)
- TR9.4: The host shall handle at least 50 concurrent requests across all servers
- TR9.5: The host shall have a base memory footprint <50MB (excluding server processes)
- TR9.6: The host shall implement efficient JSON parsing (use orjson if available)

### TR10: Security & Safety
- TR10.1: The host shall validate server executable paths exist before execution
- TR10.2: The host shall sanitize environment variables to prevent injection attacks
- TR10.3: The host shall not expose internal file paths in error messages returned to applications
- TR10.4: The host shall implement resource limits per server (memory, CPU time) if configured
- TR10.5: The host shall log all security-relevant events (failed starts, permission errors)
- TR10.6: The host shall validate that tool parameters don't contain code injection attempts

### TR11: Platform Compatibility
- TR11.1: The host shall support macOS, Linux, and Windows platforms
- TR11.2: The host shall handle platform-specific path separators correctly
- TR11.3: The host shall handle platform-specific process management differences
- TR11.4: The host shall be compatible with Python 3.10, 3.11, 3.12+
- TR11.5: The host shall use platform-independent subprocess management

### TR12: API Interface Specification
- TR12.1: The host shall expose this public API:
  ```python
  class MCPHost:
      async def initialize(self, config_path: str) -> None
      async def shutdown(self) -> None
      async def call_tool(self, tool_name: str, parameters: dict) -> dict
      async def get_prompt(self, prompt_name: str, arguments: dict = None) -> dict
      async def get_resource(self, resource_uri: str) -> dict
      def get_tools(self) -> dict
      def get_metrics(self) -> dict
      def register_callback(self, callback: Callable) -> None
  ```
- TR12.2: All methods shall be async except `get_tools()`, `get_metrics()`, and `register_callback()`
- TR12.3: All methods shall raise appropriate exceptions on errors
- TR12.4: All methods shall return type-safe results (use dataclasses/TypedDict)

