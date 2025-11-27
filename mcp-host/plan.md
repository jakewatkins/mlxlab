# MCP Host Implementation Plan

## Project Structure

```
mcp-host/
├── mcp_host/                      # Main package directory
│   ├── __init__.py               # Package initialization, exports MCPHost
│   ├── host.py                   # MCPHost main class
│   ├── config.py                 # Configuration loading and validation
│   ├── server.py                 # ServerManager and ServerInfo classes
│   ├── protocol.py               # JSON-RPC and MCP protocol implementation
│   ├── router.py                 # Request routing logic
│   ├── registry.py               # Capability registry and management
│   ├── cache.py                  # Caching implementation
│   ├── metrics.py                # Metrics collection and reporting
│   ├── exceptions.py             # Custom exception classes
│   └── types.py                  # Type definitions, enums, dataclasses
│
├── tests/                         # Test directory
│   ├── __init__.py
│   ├── test_config.py            # Configuration tests
│   ├── test_server.py            # Server lifecycle tests
│   ├── test_protocol.py          # Protocol implementation tests
│   ├── test_router.py            # Request routing tests
│   ├── test_registry.py          # Capability registry tests
│   ├── test_cache.py             # Cache tests
│   ├── test_integration.py       # Integration tests (full flow)
│   ├── mocks/                    # Mock MCP servers for testing
│   │   ├── mock_server.py        # Simple mock server
│   │   └── failing_server.py     # Server that simulates failures
│   └── fixtures/                 # Test fixtures
│       ├── mcp.json              # Test configuration
│       └── invalid_mcp.json      # Invalid config for error testing
│
├── examples/                      # Example usage
│   ├── simple_host.py            # Basic usage example
│   ├── llm_integration.py        # Example LLM integration
│   └── mcp.json                  # Example configuration
│
├── docs/                          # Documentation
│   ├── api.md                    # API documentation
│   ├── architecture.md           # Architecture overview
│   └── examples.md               # Usage examples
│
├── requirements.md                # Requirements specification
├── plan.md                        # This file
├── setup.py                       # Package setup
├── requirements.txt               # Dependencies
├── requirements-dev.txt           # Development dependencies
├── README.md                      # Project README
└── pyproject.toml                 # Modern Python project config

```

## Module Organization

### 1. `types.py` - Type Definitions
**Purpose**: Central location for all type definitions, enums, and data classes

**Contents**:
- `ServerState` enum (STARTING, READY, UNAVAILABLE, SHUTDOWN)
- `TransportType` enum (STDIO, SSE, WEBSOCKET)
- `Tool` dataclass
- `Prompt` dataclass
- `Resource` dataclass
- `ServerCapabilities` dataclass
- `ServerInfo` dataclass
- `CacheEntry` dataclass
- `MetricsData` dataclass
- Protocol message types (Request, Response, Notification)

**Dependencies**: None (only stdlib and typing)

---

### 2. `exceptions.py` - Custom Exceptions
**Purpose**: Define all custom exception classes for error handling

**Contents**:
- `MCPHostError` (base exception)
- `ConfigurationError`
- `ServerStartupError`
- `ServerUnavailableError`
- `ValidationError`
- `TimeoutError`
- `ProtocolError`
- `RoutingError`

**Dependencies**: None

---

### 3. `config.py` - Configuration Management
**Purpose**: Load, validate, and manage configuration from mcp.json

**Key Classes**:
- `ConfigLoader`
  - `load(config_path: str) -> dict`
  - `validate(config: dict) -> bool`
  - `expand_env_vars(config: dict) -> dict`
  - `get_json_schema() -> dict`

**Responsibilities**:
- Load mcp.json file
- Validate against JSON schema
- Expand environment variables (${VAR_NAME})
- Detect duplicate server names
- Parse server dependencies

**Dependencies**: `types`, `exceptions`, `json`, `jsonschema`, `os`

---

### 4. `protocol.py` - MCP Protocol Implementation
**Purpose**: Handle JSON-RPC 2.0 and MCP protocol messages

**Key Classes**:
- `JSONRPCMessage`
  - `encode(msg: dict) -> bytes`
  - `decode(data: bytes) -> dict`
  - `generate_id() -> str`
  
- `MCPProtocol`
  - `create_initialize_request() -> dict`
  - `create_tools_list_request() -> dict`
  - `create_prompts_list_request() -> dict`
  - `create_resources_list_request() -> dict`
  - `create_tool_call_request(tool: str, params: dict) -> dict`
  - `parse_response(msg: dict) -> dict`
  - `validate_message(msg: dict) -> bool`

**Responsibilities**:
- Create MCP protocol messages
- Parse and validate responses
- Handle message framing (newline-delimited JSON)
- Generate unique message IDs
- Validate against MCP schema

**Dependencies**: `types`, `exceptions`, `json`, `uuid`

---

### 5. `server.py` - Server Process Management
**Purpose**: Manage individual MCP server processes and communication

**Key Classes**:
- `ServerProcess`
  - `async start(command: str, args: list, env: dict) -> None`
  - `async send_message(msg: dict) -> None`
  - `async receive_message() -> dict`
  - `async shutdown(timeout: int) -> None`
  - `async wait_for_response(msg_id: str, timeout: int) -> dict`
  - `is_alive() -> bool`
  - `get_exit_code() -> int`

- `ServerManager`
  - `async create_server(name: str, config: dict) -> ServerProcess`
  - `async initialize_server(server: ServerProcess) -> None`
  - `async shutdown_server(server: ServerProcess, timeout: int) -> None`
  - `async health_check(server: ServerProcess) -> bool`

**Responsibilities**:
- Create and manage subprocess
- Handle STDIO pipes (stdin, stdout, stderr)
- Send/receive JSON-RPC messages
- Handle process termination (SIGTERM, SIGKILL)
- Monitor process health
- Capture stderr logs

**Dependencies**: `types`, `exceptions`, `protocol`, `asyncio`, `subprocess`

---

### 6. `registry.py` - Capability Registry
**Purpose**: Store and manage server capabilities (tools, prompts, resources)

**Key Classes**:
- `CapabilityRegistry`
  - `register_server(name: str, capabilities: ServerCapabilities) -> None`
  - `unregister_server(name: str) -> None`
  - `update_capabilities(name: str, capabilities: ServerCapabilities) -> None`
  - `get_all_capabilities() -> dict`
  - `get_server_capabilities(name: str) -> ServerCapabilities`
  - `find_tool(tool_name: str) -> tuple[str, Tool]`
  - `find_prompt(prompt_name: str) -> tuple[str, Prompt]`
  - `find_resource(resource_uri: str) -> tuple[str, Resource]`
  - `validate_tool_params(tool_name: str, params: dict) -> bool`

**Responsibilities**:
- Store server capabilities
- Query capabilities
- Validate tool parameters against schemas
- Parse {server}.{tool} format for routing
- Thread-safe access to capability data

**Dependencies**: `types`, `exceptions`, `asyncio.Lock`

---

### 7. `cache.py` - Response Caching
**Purpose**: Cache resource and prompt responses with TTL

**Key Classes**:
- `Cache`
  - `get(key: str) -> Optional[Any]`
  - `set(key: str, value: Any, ttl: int) -> None`
  - `invalidate(key: str) -> None`
  - `invalidate_server(server_name: str) -> None`
  - `clear() -> None`
  - `cleanup_expired() -> None`

**Responsibilities**:
- Store cached responses with TTL
- LRU eviction when size limit reached
- Invalidate entries on capability changes
- Thread-safe cache operations
- Background cleanup of expired entries

**Dependencies**: `types`, `asyncio`, `time`, `collections.OrderedDict`

---

### 8. `metrics.py` - Metrics Collection
**Purpose**: Collect and report performance metrics

**Key Classes**:
- `MetricsCollector`
  - `record_request(server: str, method: str, latency: float, success: bool) -> None`
  - `get_server_metrics(server: str) -> MetricsData`
  - `get_all_metrics() -> dict`
  - `reset_metrics(server: str = None) -> None`

**Responsibilities**:
- Track request counts per server
- Track success/error rates
- Track latency statistics (avg, min, max, p95)
- Thread-safe metrics updates
- Aggregate metrics across servers

**Dependencies**: `types`, `asyncio.Lock`, `time`, `statistics`

---

### 9. `router.py` - Request Router
**Purpose**: Route requests to appropriate servers with validation

**Key Classes**:
- `RequestRouter`
  - `async route_tool_call(tool_name: str, params: dict) -> dict`
  - `async route_prompt_request(prompt_name: str, args: dict) -> dict`
  - `async route_resource_request(uri: str) -> dict`
  - `async execute_with_retry(server: str, request: dict) -> dict`
  - `async execute_with_timeout(server: str, request: dict, timeout: int) -> dict`

**Responsibilities**:
- Parse tool/prompt/resource names to determine target server
- Validate parameters before routing
- Execute requests with timeout
- Implement retry logic with exponential backoff
- Handle cache lookup and update
- Track metrics for routed requests
- Handle errors and mark servers unavailable

**Dependencies**: `types`, `exceptions`, `registry`, `cache`, `metrics`, `server`, `asyncio`

---

### 10. `host.py` - Main MCPHost Class
**Purpose**: Main public API and orchestration

**Key Classes**:
- `MCPHost`
  - `async initialize(config_path: str) -> None`
  - `async shutdown() -> None`
  - `async call_tool(tool_name: str, parameters: dict) -> dict`
  - `async get_prompt(prompt_name: str, arguments: dict = None) -> dict`
  - `async get_resource(resource_uri: str) -> dict`
  - `get_tools() -> dict`
  - `get_metrics() -> dict`
  - `register_callback(callback: Callable) -> None`
  - `async _start_servers() -> None`
  - `async _query_capabilities() -> None`
  - `async _handle_server_callback(server: str, request: dict) -> dict`

**Responsibilities**:
- Orchestrate all components
- Implement public API
- Coordinate server startup with dependency management
- Handle server callbacks (proxy to application)
- Manage overall lifecycle
- Coordinate graceful shutdown

**Dependencies**: All other modules

---

## Implementation Phases

### Phase 1: Foundation (Core Types & Protocol)
**Goal**: Establish basic types and protocol handling

**Tasks**:
1. Create project structure
2. Implement `types.py` with all dataclasses and enums
3. Implement `exceptions.py` with all custom exceptions
4. Implement `protocol.py` with JSON-RPC and MCP message handling
5. Write unit tests for types and protocol

**Deliverable**: Basic protocol encoding/decoding working

---

### Phase 2: Configuration & Server Management
**Goal**: Load configuration and manage server processes

**Tasks**:
1. Implement `config.py` with JSON schema validation
2. Implement `server.py` with process management
3. Create basic server startup/shutdown flow
4. Write unit tests with mock processes
5. Test environment variable expansion

**Deliverable**: Can start/stop a single MCP server

---

### Phase 3: Capability Registry & Routing
**Goal**: Query capabilities and route requests

**Tasks**:
1. Implement `registry.py` for capability storage
2. Implement `router.py` for request routing
3. Add capability querying (tools/list, prompts/list, resources/list)
4. Add parameter validation
5. Write unit tests for registry and router

**Deliverable**: Can query server capabilities and route tool calls

---

### Phase 4: Caching & Metrics
**Goal**: Add caching and observability

**Tasks**:
1. Implement `cache.py` with TTL support
2. Implement `metrics.py` for performance tracking
3. Integrate caching into router
4. Integrate metrics into router
5. Write unit tests for cache and metrics

**Deliverable**: Caching and metrics collection working

---

### Phase 5: Main Host Integration
**Goal**: Assemble all components into MCPHost

**Tasks**:
1. Implement `host.py` with public API
2. Implement dependency management and ordered startup
3. Add callback registration for server requests
4. Implement hot-reload support
5. Add comprehensive error handling

**Deliverable**: Full MCPHost API working

---

### Phase 6: Testing & Validation
**Goal**: Comprehensive testing and validation

**Tasks**:
1. Create mock MCP servers for testing
2. Write integration tests matching requirements.md test scenario
3. Test with real MCP servers (brave-search, filesystem)
4. Performance testing (routing overhead <10ms)
5. Error scenario testing (timeouts, crashes, invalid configs)
6. Achieve >80% code coverage

**Deliverable**: All tests passing, requirements validated

---

### Phase 7: Documentation & Examples
**Goal**: Complete documentation and examples

**Tasks**:
1. Write API documentation
2. Write architecture documentation
3. Create example scripts
4. Update README with installation and usage
5. Create setup.py and pyproject.toml

**Deliverable**: Ready for integration into applications

---

## Development Guidelines

### Coding Standards
- Use Python 3.10+ features (match/case, type unions with `|`)
- All functions/methods must have type hints
- Use async/await for all I/O operations
- Follow PEP 8 style guide
- Use dataclasses for data structures
- Comprehensive docstrings (Google style)

### Testing Strategy
- Unit tests for each module (>80% coverage)
- Integration tests for full workflows
- Mock external dependencies (processes, servers)
- Test both success and error paths
- Performance benchmarks for critical paths

### Error Handling
- Use custom exceptions for all error cases
- Always include context in error messages
- Log all errors with appropriate severity
- Gracefully handle edge cases
- Never expose internal paths/details to applications

### Async Patterns
- Use `asyncio.create_task()` for background tasks
- Use `asyncio.gather()` for parallel operations
- Use `asyncio.wait_for()` for timeouts
- Proper cleanup in finally blocks
- Handle cancellation correctly

### Logging Strategy
- Use Python `logging` module
- Structured logging (JSON format for production)
- Configurable log levels
- Include correlation IDs for request tracing
- Separate logger per module

---

## Dependencies

### Core Dependencies
- Python 3.10+
- `jsonschema` - JSON schema validation
- `aiofiles` - Async file I/O (if needed)

### Development Dependencies
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Code coverage
- `black` - Code formatting
- `mypy` - Static type checking
- `ruff` - Fast linting

### Optional Dependencies
- `orjson` - Fast JSON parsing (performance optimization)
- `uvloop` - Fast event loop (performance optimization)

---

## Success Criteria

The implementation will be considered complete when:

1. ✅ All functional requirements (FR1-FR10) are implemented
2. ✅ All technical requirements (TR1-TR12) are met
3. ✅ The test scenario in requirements.md passes successfully
4. ✅ Unit test coverage exceeds 80%
5. ✅ Integration tests with real MCP servers pass
6. ✅ Request routing overhead is <10ms
7. ✅ Documentation is complete and clear
8. ✅ Code passes type checking (mypy) with no errors
9. ✅ All edge cases and error scenarios are handled
10. ✅ Ready to integrate into LLM application

---

## Next Steps

1. Review this plan and confirm approach
2. Set up project structure and dependencies
3. Begin Phase 1 implementation
4. Iterate through phases with testing at each step
5. Final validation with integration test
