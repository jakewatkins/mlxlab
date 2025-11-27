"""
MCP Host - Main orchestrator class.

Coordinates configuration, server management, routing, caching, and metrics.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .config import ConfigLoader
from .server import ServerManager
from .registry import CapabilityRegistry
from .router import RequestRouter
from .cache import Cache
from .metrics import MetricsCollector
from .types import ServerInfo, ServerState, MetricsData, ServerCapabilities, Tool, Prompt, Resource
from .exceptions import (
    ConfigurationError,
    ServerStartupError,
    ValidationError,
    TimeoutError as MCPTimeoutError
)

logger = logging.getLogger(__name__)


class MCPHost:
    """
    Main MCP Host class.
    
    Manages the lifecycle of multiple MCP servers and provides a unified
    interface for calling tools, getting prompts, and reading resources.
    """
    
    def __init__(
        self,
        config_path: str = "mcp.json",
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        cache_default_ttl: int = 300,
        metrics_enabled: bool = True
    ):
        """
        Initialize the MCP Host.
        
        Args:
            config_path: Path to mcp.json configuration file
            cache_enabled: Whether to enable caching
            cache_max_size: Maximum cache entries
            cache_default_ttl: Default cache TTL in seconds
            metrics_enabled: Whether to enable metrics collection
        """
        self.config_path = config_path
        self.cache_enabled = cache_enabled
        self.metrics_enabled = metrics_enabled
        
        # Core components
        self.config_loader = ConfigLoader()
        self.server_manager = ServerManager()
        self.registry = CapabilityRegistry()
        
        # Optional components
        self.cache: Optional[Cache] = None
        if cache_enabled:
            self.cache = Cache(max_size=cache_max_size, default_ttl=cache_default_ttl)
        
        self.metrics: Optional[MetricsCollector] = None
        if metrics_enabled:
            self.metrics = MetricsCollector()
        
        # Router with dependencies
        self.router = RequestRouter(
            registry=self.registry,
            servers=self.server_manager.servers,
            cache=self.cache,
            metrics=self.metrics
        )
        
        # State
        self._initialized = False
        self._shutdown = False
        
        # Callbacks
        self._notification_handlers: Dict[str, List[Callable]] = {}
    
    async def initialize(self) -> None:
        """
        Initialize the host and start all configured servers.
        
        Raises:
            ConfigurationError: If configuration is invalid
            ServerStartupError: If any server fails to start
        """
        if self._initialized:
            logger.warning("Host already initialized")
            return
        
        logger.info(f"Initializing MCP Host from config: {self.config_path}")
        
        try:
            # Load and validate configuration
            config = self.config_loader.load(self.config_path)
            
            # Extract servers from config
            servers_config = config.get("servers", {})
            logger.info(f"Loaded configuration with {len(servers_config)} server(s)")
            
            # Get startup order based on dependencies
            startup_order = self.config_loader.get_startup_order()
            logger.info(f"Server startup order: {' -> '.join(startup_order)}")
            
            # Start cache cleanup if enabled
            if self.cache:
                self.cache.start_cleanup()
            
            # Start servers in dependency order
            for server_name in startup_order:
                server_config = servers_config[server_name]
                await self._start_server(server_name, server_config)
            
            self._initialized = True
            logger.info("MCP Host initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize host: {e}")
            # Cleanup any started servers
            await self.shutdown()
            raise
    
    async def _start_server(self, name: str, config: Dict[str, Any]) -> None:
        """
        Start a single MCP server.
        
        Args:
            name: Server name
            config: Server configuration
            
        Raises:
            ServerStartupError: If server fails to start
        """
        try:
            logger.info(f"Starting server '{name}'...")
            
            # Create server process
            server = await self.server_manager.create_server(name, config)
            
            # Initialize the server
            init_response = await self.server_manager.initialize_server(server)
            
            # Extract capabilities - these are just indicators, not the actual lists
            caps_dict = init_response.get("capabilities", {})
            
            # Fetch actual capabilities if they're available
            tools = []
            if caps_dict.get("tools"):
                # Request the actual tool list
                from .protocol import MCPProtocol
                tools_request = MCPProtocol.create_tools_list_request()
                tools_response = await server.send_request(tools_request)
                tools_results = tools_response.get("result", {})
                # Tools are nested in results.tools
                tools = [Tool(**t) for t in tools_results.get("tools", [])]
            
            prompts = []
            if caps_dict.get("prompts"):
                # Request the actual prompt list
                from .protocol import MCPProtocol
                prompts_request = MCPProtocol.create_prompts_list_request()
                prompts_response = await server.send_request(prompts_request)
                # Prompts are nested in results.prompts
                prompts = [Prompt(**p) for p in prompts_response.get("results", {}).get("prompts", [])]
            
            resources = []
            if caps_dict.get("resources"):
                # Request the actual resource list
                from .protocol import MCPProtocol
                resources_request = MCPProtocol.create_resources_list_request()
                resources_response = await server.send_request(resources_request)
                # Resources are nested in results.resources
                resources = [Resource(**r) for r in resources_response.get("results", {}).get("resources", [])]
            
            server_caps = ServerCapabilities(
                tools=tools,
                prompts=prompts,
                resources=resources
            )
            
            # Register capabilities
            await self.registry.register_server(name, server_caps)
            
            logger.info(
                f"Server '{name}' started successfully - "
                f"tools: {len(server_caps.tools)}, "
                f"prompts: {len(server_caps.prompts)}, "
                f"resources: {len(server_caps.resources)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to start server '{name}': {e}")
            raise ServerStartupError(f"Server '{name}' failed to start: {e}", server_name=name)
    
    async def shutdown(self) -> None:
        """Shutdown all servers and cleanup resources."""
        if self._shutdown:
            return
        
        logger.info("Shutting down MCP Host...")
        
        # Stop cache cleanup
        if self.cache:
            self.cache.stop_cleanup()
        
        # Shutdown all servers
        await self.server_manager.shutdown_all()
        
        self._shutdown = True
        self._initialized = False
        
        logger.info("MCP Host shutdown complete")
    
    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Call a tool by name.
        
        Args:
            name: Tool name (supports "server.tool" format)
            arguments: Tool arguments
            timeout: Request timeout in seconds
            
        Returns:
            Tool call result
            
        Raises:
            ValidationError: If tool not found or arguments invalid
            TimeoutError: If request times out
            ServerUnavailableError: If server is not available
        """
        self._check_initialized()
        
        if arguments is None:
            arguments = {}
        
        return await self.router.route_tool_call(name, arguments)
    
    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Get a prompt by name.
        
        Args:
            name: Prompt name (supports "server.prompt" format)
            arguments: Prompt arguments
            timeout: Request timeout in seconds
            
        Returns:
            Prompt response
            
        Raises:
            ValidationError: If prompt not found
            TimeoutError: If request times out
            ServerUnavailableError: If server is not available
        """
        self._check_initialized()
        
        if arguments is None:
            arguments = {}
        
        return await self.router.route_prompt_request(name, arguments)
    
    async def read_resource(
        self,
        uri: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Read a resource by URI.
        
        Args:
            uri: Resource URI (supports "server:path" format)
            timeout: Request timeout in seconds
            
        Returns:
            Resource contents
            
        Raises:
            ValidationError: If resource not found
            TimeoutError: If request times out
            ServerUnavailableError: If server is not available
        """
        self._check_initialized()
        
        return await self.router.route_resource_request(uri)
    
    async def get_tools(self, server: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available tools.
        
        Args:
            server: Optional server name to filter by
            
        Returns:
            List of tool definitions
        """
        self._check_initialized()
        
        capabilities = await self.registry.get_all_capabilities()
        
        tools = []
        for server_name, server_caps in capabilities.items():
            if server and server_name != server:
                continue
            
            for tool in server_caps.get("tools", []):
                tools.append({
                    "name": tool["name"],
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema"),
                    "server": server_name
                })
        
        return tools
    
    async def get_prompts(self, server: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available prompts.
        
        Args:
            server: Optional server name to filter by
            
        Returns:
            List of prompt definitions
        """
        self._check_initialized()
        
        capabilities = await self.registry.get_all_capabilities()
        
        prompts = []
        for server_name, server_caps in capabilities.items():
            if server and server_name != server:
                continue
            
            for prompt in server_caps.get("prompts", []):
                prompts.append({
                    "name": prompt["name"],
                    "description": prompt.get("description"),
                    "arguments": prompt.get("arguments"),
                    "server": server_name
                })
        
        return prompts
    
    async def get_resources(self, server: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available resources.
        
        Args:
            server: Optional server name to filter by
            
        Returns:
            List of resource definitions
        """
        self._check_initialized()
        
        capabilities = await self.registry.get_all_capabilities()
        
        resources = []
        for server_name, server_caps in capabilities.items():
            if server and server_name != server:
                continue
            
            for resource in server_caps.get("resources", []):
                resources.append({
                    "uri": resource["uri"],
                    "name": resource["name"],
                    "description": resource.get("description"),
                    "mimeType": resource.get("mimeType"),
                    "server": server_name
                })
        
        return resources
    
    def get_servers(self) -> List[Dict[str, Any]]:
        """
        Get information about all servers.
        
        Returns:
            List of server information
        """
        self._check_initialized()
        
        servers = []
        for name, server in self.server_manager.servers.items():
            servers.append({
                "name": name,
                "state": server.state.value,
                "pid": server.process.pid if server.process else None
            })
        
        return servers
    
    def get_metrics(self, server: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Args:
            server: Optional server name to filter by
            
        Returns:
            Metrics data
        """
        self._check_initialized()
        
        if not self.metrics:
            return {"error": "Metrics not enabled"}
        
        if server:
            metrics = self.metrics.get_server_metrics(server)
            return {
                server: {
                    "request_count": metrics.request_count,
                    "success_count": metrics.success_count,
                    "error_count": metrics.error_count,
                    "success_rate": metrics.success_rate,
                    "avg_latency": metrics.avg_latency,
                    "min_latency": metrics.min_latency if metrics.min_latency != float('inf') else 0.0,
                    "max_latency": metrics.max_latency,
                    "p95_latency": metrics.p95_latency()
                }
            }
        
        return self.metrics.get_all_metrics()
    
    def register_notification_handler(
        self,
        notification_type: str,
        handler: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """
        Register a handler for server notifications.
        
        Args:
            notification_type: Type of notification to handle
            handler: Callback function(server_name, params)
        """
        if notification_type not in self._notification_handlers:
            self._notification_handlers[notification_type] = []
        
        self._notification_handlers[notification_type].append(handler)
        logger.info(f"Registered handler for notification type: {notification_type}")
    
    def _check_initialized(self) -> None:
        """Check if host is initialized."""
        if not self._initialized:
            raise RuntimeError("MCP Host not initialized. Call initialize() first.")
        
        if self._shutdown:
            raise RuntimeError("MCP Host has been shutdown.")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
