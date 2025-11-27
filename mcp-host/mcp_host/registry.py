"""
Capability registry for MCP Host.

Manages server capabilities (tools, prompts, resources) and provides
query and validation functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from .types import ServerCapabilities, Tool, Prompt, Resource
from .exceptions import ValidationError, RoutingError

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for server capabilities."""
    
    def __init__(self):
        """Initialize the capability registry."""
        self._capabilities: Dict[str, ServerCapabilities] = {}
        self._lock = asyncio.Lock()
    
    async def register_server(
        self,
        name: str,
        capabilities: ServerCapabilities
    ) -> None:
        """
        Register a server's capabilities.
        
        Args:
            name: Server name
            capabilities: Server capabilities
        """
        async with self._lock:
            self._capabilities[name] = capabilities
            logger.info(
                f"Registered capabilities for server '{name}': "
                f"{len(capabilities.tools)} tools, "
                f"{len(capabilities.prompts)} prompts, "
                f"{len(capabilities.resources)} resources"
            )
    
    async def unregister_server(self, name: str) -> None:
        """
        Unregister a server's capabilities.
        
        Args:
            name: Server name
        """
        async with self._lock:
            if name in self._capabilities:
                del self._capabilities[name]
                logger.info(f"Unregistered capabilities for server '{name}'")
    
    async def update_capabilities(
        self,
        name: str,
        capabilities: ServerCapabilities
    ) -> None:
        """
        Update a server's capabilities.
        
        Args:
            name: Server name
            capabilities: Updated capabilities
        """
        async with self._lock:
            self._capabilities[name] = capabilities
            logger.info(f"Updated capabilities for server '{name}'")
    
    async def get_all_capabilities(self) -> Dict[str, Dict]:
        """
        Get all capabilities from all servers.
        
        Returns:
            Dictionary mapping server names to their capabilities
        """
        async with self._lock:
            result = {}
            for server_name, caps in self._capabilities.items():
                result[server_name] = {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in caps.tools
                    ],
                    "prompts": [
                        {
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        }
                        for prompt in caps.prompts
                    ],
                    "resources": [
                        {
                            "uri": resource.uri,
                            "name": resource.name,
                            "description": resource.description,
                            "mimeType": resource.mime_type
                        }
                        for resource in caps.resources
                    ]
                }
            return result
    
    async def get_server_capabilities(self, name: str) -> Optional[ServerCapabilities]:
        """
        Get capabilities for a specific server.
        
        Args:
            name: Server name
            
        Returns:
            ServerCapabilities or None if server not found
        """
        async with self._lock:
            return self._capabilities.get(name)
    
    async def find_tool(self, tool_name: str) -> Tuple[str, Tool]:
        """
        Find a tool by name.
        
        Expected format: {server}.{tool} or just {tool}
        
        Args:
            tool_name: Tool name (may include server prefix)
            
        Returns:
            Tuple of (server_name, Tool)
            
        Raises:
            RoutingError: If tool not found or ambiguous
        """
        async with self._lock:
            # Check if tool name includes server prefix
            if '.' in tool_name:
                parts = tool_name.split('.', 1)
                server_name = parts[0]
                actual_tool_name = parts[1]
                
                # Look in specific server
                if server_name in self._capabilities:
                    caps = self._capabilities[server_name]
                    tool = caps.get_tool(actual_tool_name)
                    if tool:
                        return (server_name, tool)
                
                raise RoutingError(
                    f"Tool '{actual_tool_name}' not found in server '{server_name}'",
                    target=tool_name,
                    reason="tool_not_found"
                )
            else:
                # Search all servers
                matches: List[Tuple[str, Tool]] = []
                for server_name, caps in self._capabilities.items():
                    tool = caps.get_tool(tool_name)
                    if tool:
                        matches.append((server_name, tool))
                
                if len(matches) == 0:
                    raise RoutingError(
                        f"Tool '{tool_name}' not found in any server",
                        target=tool_name,
                        reason="tool_not_found"
                    )
                elif len(matches) > 1:
                    server_names = [m[0] for m in matches]
                    raise RoutingError(
                        f"Tool '{tool_name}' found in multiple servers: {server_names}. "
                        f"Use format {{server}}.{{tool}} to specify.",
                        target=tool_name,
                        reason="ambiguous_tool"
                    )
                
                return matches[0]
    
    async def find_prompt(self, prompt_name: str) -> Tuple[str, Prompt]:
        """
        Find a prompt by name.
        
        Expected format: {server}.{prompt} or just {prompt}
        
        Args:
            prompt_name: Prompt name (may include server prefix)
            
        Returns:
            Tuple of (server_name, Prompt)
            
        Raises:
            RoutingError: If prompt not found or ambiguous
        """
        async with self._lock:
            # Check if prompt name includes server prefix
            if '.' in prompt_name:
                parts = prompt_name.split('.', 1)
                server_name = parts[0]
                actual_prompt_name = parts[1]
                
                # Look in specific server
                if server_name in self._capabilities:
                    caps = self._capabilities[server_name]
                    prompt = caps.get_prompt(actual_prompt_name)
                    if prompt:
                        return (server_name, prompt)
                
                raise RoutingError(
                    f"Prompt '{actual_prompt_name}' not found in server '{server_name}'",
                    target=prompt_name,
                    reason="prompt_not_found"
                )
            else:
                # Search all servers
                matches: List[Tuple[str, Prompt]] = []
                for server_name, caps in self._capabilities.items():
                    prompt = caps.get_prompt(prompt_name)
                    if prompt:
                        matches.append((server_name, prompt))
                
                if len(matches) == 0:
                    raise RoutingError(
                        f"Prompt '{prompt_name}' not found in any server",
                        target=prompt_name,
                        reason="prompt_not_found"
                    )
                elif len(matches) > 1:
                    server_names = [m[0] for m in matches]
                    raise RoutingError(
                        f"Prompt '{prompt_name}' found in multiple servers: {server_names}. "
                        f"Use format {{server}}.{{prompt}} to specify.",
                        target=prompt_name,
                        reason="ambiguous_prompt"
                    )
                
                return matches[0]
    
    async def find_resource(self, resource_uri: str) -> Tuple[str, Resource]:
        """
        Find a resource by URI.
        
        Args:
            resource_uri: Resource URI
            
        Returns:
            Tuple of (server_name, Resource)
            
        Raises:
            RoutingError: If resource not found
        """
        async with self._lock:
            # Resources are identified by URI, which should be unique
            for server_name, caps in self._capabilities.items():
                resource = caps.get_resource(resource_uri)
                if resource:
                    return (server_name, resource)
            
            raise RoutingError(
                f"Resource '{resource_uri}' not found in any server",
                target=resource_uri,
                reason="resource_not_found"
            )
    
    async def validate_tool_params(
        self,
        tool_name: str,
        params: Dict
    ) -> Tuple[str, bool]:
        """
        Validate tool parameters against schema.
        
        Args:
            tool_name: Tool name
            params: Parameters to validate
            
        Returns:
            Tuple of (server_name, is_valid)
            
        Raises:
            RoutingError: If tool not found
            ValidationError: If parameters are invalid
        """
        server_name, tool = await self.find_tool(tool_name)
        
        is_valid = tool.validate_params(params)
        if not is_valid:
            raise ValidationError(
                f"Invalid parameters for tool '{tool_name}'",
                validation_type="tool_parameters",
                details={
                    "tool": tool_name,
                    "server": server_name,
                    "expected_schema": tool.inputSchema,
                    "provided_params": params
                }
            )
        
        return (server_name, is_valid)
