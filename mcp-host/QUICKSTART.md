# Quick Start Guide

## Installation

```bash
# Navigate to the mcp-host directory
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host

# Install the package in development mode
pip install -e .
```

## Basic Usage

### 1. Create Configuration File

Create a file named `mcp.json`:

```json
{
  "servers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

Make sure to set your environment variable:
```bash
export BRAVE_API_KEY="your-api-key-here"
```

### 2. Use the Host

Create a Python script:

```python
import asyncio
from mcp_host import MCPHost

async def main():
    async with MCPHost(config_path="mcp.json") as host:
        # List all available tools
        tools = await host.get_tools()
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool.get('description', '')}")
        
        # Call a tool
        result = await host.call_tool("brave-search.search", {
            "query": "Python MCP examples"
        })
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Run It

```bash
python your_script.py
```

## Common Patterns

### Using as Context Manager

```python
async with MCPHost(config_path="mcp.json") as host:
    # All servers are started
    result = await host.call_tool("tool-name", {"param": "value"})
# All servers are automatically shut down
```

### Manual Lifecycle Management

```python
host = MCPHost(config_path="mcp.json")
try:
    await host.initialize()
    result = await host.call_tool("tool-name", {"param": "value"})
finally:
    await host.shutdown()
```

### Getting Metrics

```python
async with MCPHost(config_path="mcp.json") as host:
    # Use the host
    await host.call_tool("search", {"query": "test"})
    
    # Get performance metrics
    metrics = host.get_metrics()
    print(f"Metrics: {metrics}")
```

### Error Handling

```python
from mcp_host import MCPHost, ServerUnavailableError, TimeoutError

async with MCPHost(config_path="mcp.json") as host:
    try:
        result = await host.call_tool("tool-name", {"param": "value"})
    except ServerUnavailableError as e:
        print(f"Server '{e.server_name}' is not available")
    except TimeoutError as e:
        print(f"Request timed out after {e.timeout_seconds} seconds")
```

## Configuration Options

### MCPHost Constructor

```python
host = MCPHost(
    config_path="mcp.json",         # Path to config file
    cache_enabled=True,              # Enable caching
    cache_max_size=1000,             # Max cache entries
    cache_default_ttl=300,           # Cache TTL in seconds (5 min)
    metrics_enabled=True             # Enable metrics collection
)
```

### Server Configuration

```json
{
  "servers": {
    "server-name": {
      "command": "npx",                          // Command to run
      "args": ["-y", "@org/package"],            // Arguments
      "env": {                                   // Environment variables
        "API_KEY": "${MY_API_KEY}",              // Expand from system env
        "DEBUG": "true"
      },
      "cwd": "/path/to/working/directory",       // Optional working dir
      "dependencies": ["other-server"]           // Optional dependencies
    }
  }
}
```

## Troubleshooting

### Server Won't Start

1. Check the command is valid:
   ```bash
   npx -y @modelcontextprotocol/server-brave-search
   ```

2. Check environment variables are set:
   ```bash
   echo $BRAVE_API_KEY
   ```

3. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Tool Not Found

Make sure you're using the correct format:
- `"tool-name"` - searches all servers
- `"server-name.tool-name"` - specific server

### Timeout Errors

Increase the timeout:
```python
result = await host.call_tool("slow-tool", params, timeout=60.0)
```

## Examples

See the `examples/` directory for more:
- `simple_host.py` - Basic usage
- `mcp.json.example` - Example configuration

## Development

For development work:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run type checking
mypy mcp_host/

# Format code
black mcp_host/
isort mcp_host/
```

## Support

For issues or questions:
1. Check the README.md
2. Review examples/
3. Enable debug logging
4. Check server configuration

## Next Steps

- Read the full [README.md](README.md)
- Review the [API documentation](README.md#api-reference)
- Try the [examples](examples/)
- Check the [requirements](requirements.md)
