"""
Tool execution via mcp-host library
"""

import asyncio
import json
import sys
from typing import Dict, Any, List, Optional, Tuple
from mcp_host import MCPHost  # type: ignore
from mcp_host.exceptions import MCPHostError, TimeoutError as MCPTimeoutError  # type: ignore
import time
from datetime import datetime


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
        self.host = MCPHost(config_path=self.mcp_config_path)
        await self.host.initialize()  # type: ignore
        await self._discover_tools()
    
    async def _discover_tools(self):
        """Query all MCP servers for available tools"""
        if not self.host:
            return
        
        all_tools = await self.host.get_tools()
        
        if isinstance(all_tools, dict):
            self.tools = all_tools
        else:
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
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (result, error, duration)
        """
        if not self.host:
            return None, "MCP host not initialized", 0.0
        
        start_time = time.time()
        
        try:
            if not isinstance(args, dict):
                error_msg = f"Tool arguments must be a dictionary, got {type(args).__name__}"
                return None, error_msg, time.time() - start_time
            
            result = await asyncio.wait_for(
                self.host.call_tool(name, args),
                timeout=timeout
            )
            
            duration = time.time() - start_time
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
            description = tool_info.get("description", "No description")
            input_schema = tool_info.get("inputSchema", {})
            
            tool_desc = f"\n- {tool_name}: {description}"
            
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
                    
                    # Build example argument
                    if param_type == "string":
                        if "path" in param_name.lower() or "file" in param_name.lower():
                            example_args[param_name] = "/path/to/file.txt"
                        elif "content" in param_name.lower():
                            example_args[param_name] = "content here"
                        elif "query" in param_name.lower():
                            example_args[param_name] = "search query"
                        else:
                            example_args[param_name] = "value"
                    elif param_type in ("number", "integer"):
                        example_args[param_name] = 123
                    elif param_type == "boolean":
                        example_args[param_name] = True
                    else:
                        example_args[param_name] = "value"
                
                if param_list:
                    tool_desc += "\n  Parameters:\n" + "\n".join(param_list)
                    
                if example_args:
                    example_json = json.dumps({"name": tool_name, "arguments": example_args}, indent=2)
                    tool_desc += f"\n  Example:\n  <tool_call>\n  {example_json}\n  </tool_call>"
            
            tool_descriptions.append(tool_desc)
        
        tool_descriptions.append("\n\nTo use a tool, generate a tool call in the exact format shown in the examples above.")
        
        return "\n".join(tool_descriptions)
    
    async def shutdown(self):
        """Shutdown all MCP servers"""
        if self.host:
            await self.host.shutdown()
    
    def get_tool_count(self) -> int:
        """Return number of available tools"""
        return len(self.tools)
    
    @staticmethod
    def log_tool_call(name: str, args: Dict[str, Any]):
        """Log tool call to stderr"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        args_str = ", ".join([f"{k}={repr(v)}" for k, v in args.items()])
        print(f"[{timestamp}] Calling tool: {name}({args_str}) ...", file=sys.stderr)
    
    @staticmethod
    def log_tool_result(result: Optional[str], error: Optional[str], duration: float):
        """Log tool result to stderr"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if error:
            print(f"[{timestamp}] Error: {error} (took {duration:.2f}s)", file=sys.stderr)
        else:
            # Truncate long results
            result_preview = result[:100] + "..." if result and len(result) > 100 else result
            print(f"[{timestamp}] Result: {result_preview} (took {duration:.2f}s)", file=sys.stderr)
