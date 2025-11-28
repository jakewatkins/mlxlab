"""
Request routing for MCP Host.

Routes requests to appropriate servers with validation, timeout, and retry logic.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from .types import ServerState
from .registry import CapabilityRegistry
from .server import ServerProcess
from .protocol import MCPProtocol
from .exceptions import (
    ServerUnavailableError,
    RoutingError,
    TimeoutError as MCPTimeoutError,
    ValidationError
)

logger = logging.getLogger(__name__)


class RequestRouter:
    """Routes requests to appropriate MCP servers."""
    
    def __init__(
        self,
        registry: CapabilityRegistry,
        servers: Dict[str, ServerProcess],
        cache: Optional[Any] = None,
        metrics: Optional[Any] = None
    ):
        """
        Initialize the request router.
        
        Args:
            registry: Capability registry
            servers: Dictionary of server processes
            cache: Optional cache instance
            metrics: Optional metrics collector
        """
        self.registry = registry
        self.servers = servers
        self.cache = cache
        self.metrics = metrics
        self._retry_config = {
            "initial_delay": 1.0,
            "max_delay": 30.0,
            "max_retries": 3,
            "exponential_base": 2.0
        }
    
    async def route_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a tool call to the appropriate server.
        
        Args:
            tool_name: Name of the tool (may include server prefix)
            params: Tool parameters
            
        Returns:
            Tool call result
            
        Raises:
            RoutingError: If routing fails
            ValidationError: If parameters are invalid
            ServerUnavailableError: If target server is unavailable
        """
        # Find and validate tool
        server_name, is_valid = await self.registry.validate_tool_params(tool_name, params)
        
        # Check server availability
        if server_name not in self.servers:
            raise ServerUnavailableError(
                f"Server '{server_name}' not found",
                server_name=server_name
            )
        
        server = self.servers[server_name]
        if server.state != ServerState.READY:
            raise ServerUnavailableError(
                f"Server '{server_name}' is not ready (state: {server.state.value})",
                server_name=server_name
            )
        
        # Extract actual tool name (remove server prefix if present)
        actual_tool_name = tool_name.split('.')[-1]
        
        # Create tool call request
        request = MCPProtocol.create_tool_call_request(actual_tool_name, params)
        
        # Execute with retry and timeout
        result = await self.execute_with_retry(server_name, request)
        
        return result
    
    async def route_prompt_request(
        self,
        prompt_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a prompt request to the appropriate server.
        
        Args:
            prompt_name: Name of the prompt
            arguments: Optional prompt arguments
            
        Returns:
            Prompt result
            
        Raises:
            RoutingError: If routing fails
            ServerUnavailableError: If target server is unavailable
        """
        # Check cache first
        if self.cache:
            cache_key = f"prompt:{prompt_name}:{arguments}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for prompt '{prompt_name}'")
                return cached
        
        # Find prompt
        server_name, prompt = await self.registry.find_prompt(prompt_name)
        
        # Check server availability
        if server_name not in self.servers:
            raise ServerUnavailableError(
                f"Server '{server_name}' not found",
                server_name=server_name
            )
        
        server = self.servers[server_name]
        if server.state != ServerState.READY:
            raise ServerUnavailableError(
                f"Server '{server_name}' is not ready (state: {server.state.value})",
                server_name=server_name
            )
        
        # Extract actual prompt name (remove server prefix if present)
        actual_prompt_name = prompt_name.split('.')[-1]
        
        # Create prompt request
        request = MCPProtocol.create_prompt_get_request(actual_prompt_name, arguments)
        
        # Execute with retry and timeout
        result = await self.execute_with_retry(server_name, request)
        
        # Cache result
        if self.cache:
            self.cache.set(cache_key, result, ttl=300)  # 5 minutes default
        
        return result
    
    async def route_resource_request(
        self,
        resource_uri: str
    ) -> Dict[str, Any]:
        """
        Route a resource request to the appropriate server.
        
        Args:
            resource_uri: Resource URI
            
        Returns:
            Resource content
            
        Raises:
            RoutingError: If routing fails
            ServerUnavailableError: If target server is unavailable
        """
        # Check cache first
        if self.cache:
            cache_key = f"resource:{resource_uri}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for resource '{resource_uri}'")
                return cached
        
        # Find resource
        server_name, resource = await self.registry.find_resource(resource_uri)
        
        # Check server availability
        if server_name not in self.servers:
            raise ServerUnavailableError(
                f"Server '{server_name}' not found",
                server_name=server_name
            )
        
        server = self.servers[server_name]
        if server.state != ServerState.READY:
            raise ServerUnavailableError(
                f"Server '{server_name}' is not ready (state: {server.state.value})",
                server_name=server_name
            )
        
        # Create resource request
        request = MCPProtocol.create_resource_read_request(resource_uri)
        
        # Execute with retry and timeout
        result = await self.execute_with_retry(server_name, request)
        
        # Cache result
        if self.cache:
            self.cache.set(cache_key, result, ttl=300)  # 5 minutes default
        
        return result
    
    async def execute_with_retry(
        self,
        server_name: str,
        request: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Execute a request with retry logic.
        
        Args:
            server_name: Name of the server
            request: Request to send
            timeout: Request timeout
            
        Returns:
            Response result
            
        Raises:
            ServerUnavailableError: If server becomes unavailable
            MCPTimeoutError: If request times out after retries
        """
        server = self.servers[server_name]
        
        delay = self._retry_config["initial_delay"]
        max_retries = self._retry_config["max_retries"]
        
        for attempt in range(max_retries + 1):
            try:
                # Execute with timeout
                result = await self.execute_with_timeout(
                    server_name,
                    request,
                    timeout
                )
                
                # Record success metric
                if self.metrics:
                    await self.metrics.record_request(
                        server_name,
                        request.get("method", "unknown"),
                        latency=0.0,  # Will be updated by execute_with_timeout
                        success=True
                    )
                
                return result
                
            except MCPTimeoutError as e:
                # Mark server as unavailable on timeout
                server.state = ServerState.UNAVAILABLE
                
                # Record failure metric
                if self.metrics:
                    await self.metrics.record_request(
                        server_name,
                        request.get("method", "unknown"),
                        latency=timeout,
                        success=False
                    )
                
                # Unregister server capabilities
                await self.registry.unregister_server(server_name)
                
                logger.error(
                    f"Request to server '{server_name}' timed out "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                
                if attempt < max_retries:
                    # Retry with exponential backoff
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self._retry_config["exponential_base"],
                        self._retry_config["max_delay"]
                    )
                else:
                    # Final attempt failed
                    raise ServerUnavailableError(
                        f"Server '{server_name}' is unavailable (timeout after {max_retries} retries)",
                        server_name=server_name
                    )
            
            except Exception as e:
                # Record failure metric
                if self.metrics:
                    await self.metrics.record_request(
                        server_name,
                        request.get("method", "unknown"),
                        latency=0.0,
                        success=False
                    )
                
                # Check if error indicates server crash
                if "process" in str(e).lower() or "connection" in str(e).lower():
                    server.state = ServerState.UNAVAILABLE
                    await self.registry.unregister_server(server_name)
                    
                    raise ServerUnavailableError(
                        f"Server '{server_name}' crashed: {e}",
                        server_name=server_name
                    )
                
                raise
        
        # Should not reach here
        raise ServerUnavailableError(
            f"Server '{server_name}' is unavailable",
            server_name=server_name
        )
    
    async def execute_with_timeout(
        self,
        server_name: str,
        request: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """
        Execute a request with timeout.
        
        Args:
            server_name: Name of the server
            request: Request to send
            timeout: Request timeout in seconds
            
        Returns:
            Response result
            
        Raises:
            MCPTimeoutError: If request times out
        """
        server = self.servers[server_name]
        
        start_time = time.time()
        
        try:
            # Send request and wait for response
            response = await server.send_request(request, timeout=timeout)
            
            # Calculate latency
            latency = time.time() - start_time
            
            # Record metric
            if self.metrics:
                await self.metrics.record_request(
                    server_name,
                    request.get("method", "unknown"),
                    latency=latency,
                    success=True
                )
            
            # Parse response
            parsed = MCPProtocol.parse_response(response)
            
            if parsed.is_error:
                error = parsed.error or {}
                logger.error(
                    f"Server '{server_name}' returned error: {error.get('message')}"
                )
                raise ValidationError(
                    f"Server error: {error.get('message')}",
                    validation_type="server_error",
                    details=error
                )
            
            return parsed.result or {}
            
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            raise MCPTimeoutError(
                f"Request to server '{server_name}' timed out",
                operation=request.get("method"),
                timeout_seconds=timeout
            )
