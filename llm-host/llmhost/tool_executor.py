"""
Tool execution via mcp-host library
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from mcp_host import MCPHost  # type: ignore
from mcp_host.exceptions import MCPHostError, TimeoutError as MCPTimeoutError  # type: ignore
import time


class ToolExecutor:
    """Manages MCP server integration and tool execution"""
    
    def __init__(self, mcp_config_path: str = "mcp.json"):
        """
        Initialize tool executor
        
        Args:
            mcp_config_path: Path to mcp.json configuration file
        """
        self.mcp_config_path = mcp_config_path
        self.host: Optional[MCPHost] = None
        self.tools: Dict[str, Any] = {}
    
    async def start(self):
        """Start all MCP servers and discover tools"""
        # Initialize mcp-host with configuration path
        self.host = MCPHost(config_path=self.mcp_config_path)
        await self.host.initialize()  # type: ignore
        
        # Discover available tools
        await self._discover_tools()
    
    async def _discover_tools(self):
        """Query all MCP servers for available tools"""
        if not self.host:
            return
        
        # Get all tools from all servers
        all_tools = await self.host.get_tools()
        
        # Store tools by name for easy lookup
        # get_tools returns a dict where keys are tool names
        if isinstance(all_tools, dict):
            self.tools = all_tools
        else:
            # If it returns a list, convert to dict
            for tool in all_tools:
                if isinstance(tool, dict):
                    self.tools[tool["name"]] = tool
    
    async def execute_tool(
        self, 
        name: str, 
        args: Dict[str, Any], 
        timeout: float = 90.0
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Execute a single tool with timeout
        
        Args:
            name: Tool name
            args: Tool arguments
            timeout: Timeout in seconds (default 90)
            
        Returns:
            Tuple of (result, error, duration)
            - result: Tool result as string (or None if error)
            - error: Error message (or None if success)
            - duration: Execution time in seconds
        """
        if not self.host:
            return None, "MCP host not initialized", 0.0
        
        start_time = time.time()
        
        try:
            # Validate that args is a dict (MCP requires this)
            if not isinstance(args, dict):
                error_msg = f"Tool arguments must be a dictionary, got {type(args).__name__}"
                return None, error_msg, time.time() - start_time
            
            # Call tool via mcp-host
            result = await asyncio.wait_for(
                self.host.call_tool(name, args),
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            # Convert result to string for display
            result_str = json.dumps(result) if not isinstance(result, str) else result
            
            return result_str, None, duration
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error = f"Tool '{name}' timed out after {timeout}s"
            return None, error, duration
            
        except MCPTimeoutError as e:
            duration = time.time() - start_time
            error = f"Tool '{name}' timed out: {e}"
            return None, error, duration
            
        except MCPHostError as e:
            duration = time.time() - start_time
            error = f"MCP error: {e}"
            return None, error, duration
            
        except Exception as e:
            duration = time.time() - start_time
            error = f"Unexpected error: {e}"
            return None, error, duration
    
    def format_tools_for_prompt(self) -> str:
        """
        Format available tools for inclusion in system prompt
        
        Returns:
            Formatted string describing all available tools
        """
        if not self.tools:
            return "\n\nNo tools are currently available."
        
        tool_descriptions = ["\n\nAvailable tools:"]
        
        for tool_name, tool_info in self.tools.items():
            # Extract tool details
            description = tool_info.get("description", "No description")
            input_schema = tool_info.get("inputSchema", {})
            
            # Format tool signature
            tool_desc = f"\n- {tool_name}: {description}"
            
            # Add parameters if available
            if "properties" in input_schema:
                params = input_schema["properties"]
                required = input_schema.get("required", [])
                
                param_list = []
                example_args = {}
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    req_marker = " (required)" if param_name in required else ""
                    param_list.append(
                        f"    - {param_name} ({param_type}){req_marker}: {param_desc}"
                    )
                    
                    # Build contextual example argument based on parameter name and type
                    if param_type == "string":
                        # Use parameter name to create contextual examples
                        if "path" in param_name.lower() or "file" in param_name.lower():
                            example_args[param_name] = "/path/to/file.txt"
                        elif "content" in param_name.lower() or "text" in param_name.lower():
                            example_args[param_name] = "file content here"
                        elif "query" in param_name.lower() or "search" in param_name.lower():
                            example_args[param_name] = "search query"
                        elif "uri" in param_name.lower() or "url" in param_name.lower():
                            example_args[param_name] = "https://example.com"
                        elif "name" in param_name.lower():
                            example_args[param_name] = "example_name"
                        else:
                            example_args[param_name] = "example_value"
                    elif param_type == "number" or param_type == "integer":
                        example_args[param_name] = 123
                    elif param_type == "boolean":
                        example_args[param_name] = True
                    elif param_type == "array":
                        example_args[param_name] = []
                    elif param_type == "object":
                        example_args[param_name] = {}
                    else:
                        example_args[param_name] = "value"
                
                if param_list:
                    tool_desc += "\n  Parameters:\n" + "\n".join(param_list)
                    
                # Add example usage with proper formatting
                if example_args:
                    example_json = json.dumps({"name": tool_name, "arguments": example_args}, indent=2)
                    tool_desc += f"\n  Example:\n  <tool_call>\n  {example_json}\n  </tool_call>"
            
            tool_descriptions.append(tool_desc)
        
        return "\n".join(tool_descriptions)
    
    async def shutdown(self):
        """Shutdown all MCP servers"""
        if self.host:
            await self.host.shutdown()
    
    def get_tool_count(self) -> int:
        """Return number of available tools"""
        return len(self.tools)
