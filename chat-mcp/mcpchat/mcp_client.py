"""MCP server management and communication."""
import os
import re
import asyncio
import json
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.panel import Panel

console = Console()


class MCPServer:
    """Represents a single MCP server connection."""

    def resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable references in config."""
        config = config.copy()
        if "env" in config:
            resolved_env = {}
            for key, value in config["env"].items():
                # Replace ${VAR_NAME} with actual env var
                if isinstance(value, str):
                    resolved_env[key] = re.sub(
                        r'\$\{([^}]+)\}',
                        lambda m: os.getenv(m.group(1), ''),
                        value
                    )
                else:
                    resolved_env[key] = value
            config["env"] = resolved_env
        return config


    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = self.resolve_env_vars(config)
        self.session: Optional[ClientSession] = None
        self.tools: List[Dict[str, Any]] = []
        self._stdio_context = None

    async def start(self) -> None:
        """Start the MCP server and initialize the connection."""
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config["command"],
                args=self.config.get("args", []),
                env=self.config.get("env"),
            )

            # Start the stdio client (returns a context manager)
            self._stdio_context = stdio_client(server_params)
            read_stream, write_stream = await self._stdio_context.__aenter__()
            
            # Create session
            self.session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await self.session.__aenter__()
            
            # Initialize with server
            await self.session.initialize()

            # List available tools
            tools_result = await self.session.list_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in tools_result.tools
            ]

            console.print(f"[green]✓[/green] Connected to MCP server: {self.name} ({len(self.tools)} tools)")

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to connect to MCP server '{self.name}': {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError(f"MCP server '{self.name}' is not connected")

        start_time = datetime.now()
        
        try:
            # Display tool call
            console.print(Panel(
                f"[bold cyan]Tool:[/bold cyan] {tool_name}\n"
                f"[bold cyan]Arguments:[/bold cyan] {json.dumps(arguments, indent=2)}",
                title=f"[yellow]Calling Tool[/yellow] ({start_time.strftime('%H:%M:%S')})",
                border_style="yellow"
            ))

            # Call the tool with timeout
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, arguments),
                timeout=990.0
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # iterate over result.content getting just the text
            #content = "\n".join(item.get("text", "") for item in result.content if isinstance(item, dict))
            content = result.content[0].text
            # Display result
            console.print(Panel(
                f"[bold green]Result:[/bold green]\n{content}\n\n"
                f"[bold green]Execution time:[/bold green] {duration:.2f}s",
                title="[green]Tool Result[/green]",
                border_style="green"
            ))

            return result

        except asyncio.TimeoutError:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = f"Tool call timed out after {duration:.2f}s (limit: 90s)"
            console.print(Panel(
                f"[bold red]Error:[/bold red] {error_msg}",
                title="[red]Tool Error[/red]",
                border_style="red"
            ))
            raise TimeoutError(error_msg)

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            console.print(Panel(
                f"[bold red]Error:[/bold red] {str(e)}\n\n"
                f"[bold red]Execution time:[/bold red] {duration:.2f}s",
                title="[red]Tool Error[/red]",
                border_style="red"
            ))
            raise

    async def shutdown(self) -> None:
        """Shutdown the MCP server connection."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error shutting down MCP server '{self.name}': {e}")


class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServer] = {}

    async def initialize(self) -> None:
        """Initialize all MCP servers from config file."""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            console.print(f"[yellow]Warning:[/yellow] No MCP config file found at {self.config_path}")
            console.print("[yellow]Running without MCP servers[/yellow]")
            return
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON in {self.config_path}: {e}")
            sys.exit(1)

        servers_config = config.get("servers", {})
        if not servers_config:
            console.print("[yellow]No MCP servers configured[/yellow]")
            return

        console.print(f"\n[bold]Initializing {len(servers_config)} MCP server(s)...[/bold]")

        # Initialize each server
        for name, server_config in servers_config.items():
            if server_config.get("type") != "stdio":
                console.print(f"[yellow]Warning:[/yellow] Skipping server '{name}': only 'stdio' transport is supported")
                continue

            server = MCPServer(name, server_config)
            try:
                await asyncio.wait_for(server.start(), timeout=10.0)
                self.servers[name] = server
            except asyncio.TimeoutError:
                console.print(f"[red]✗[/red] Server '{name}' initialization timed out (10s limit)")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to initialize server '{name}': {e}")
                sys.exit(1)

        console.print(f"[bold green]All MCP servers initialized successfully[/bold green]\n")

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all servers in OpenAI format."""
        tools = []
        for server in self.servers.values():
            for tool in server.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["inputSchema"],
                    }
                })
        return tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by name across all servers."""
        # Find which server has this tool
        for server in self.servers.values():
            for tool in server.tools:
                if tool["name"] == tool_name:
                    return await server.call_tool(tool_name, arguments)

        raise ValueError(f"Tool '{tool_name}' not found in any MCP server")

    async def shutdown_all(self) -> None:
        """Shutdown all MCP servers."""
        if self.servers:
            console.print("\n[bold]Shutting down MCP servers...[/bold]")
            for server in self.servers.values():
                await server.shutdown()
            console.print("[green]MCP servers shut down[/green]")
