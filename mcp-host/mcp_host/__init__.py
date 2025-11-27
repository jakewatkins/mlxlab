"""
MCP Host - A Python module for hosting and managing MCP (Model Context Protocol) servers.

This package provides a clean interface for starting MCP servers, querying their
capabilities, and routing requests to them. It handles all the complexity of process
management, protocol communication, and error handling.
"""

from .host import MCPHost
from .exceptions import (
    MCPHostError,
    ConfigurationError,
    ServerStartupError,
    ServerUnavailableError,
    ValidationError,
    TimeoutError,
    ProtocolError,
    RoutingError,
)

__version__ = "0.1.0"
__all__ = [
    "MCPHost",
    "MCPHostError",
    "ConfigurationError",
    "ServerStartupError",
    "ServerUnavailableError",
    "ValidationError",
    "TimeoutError",
    "ProtocolError",
    "RoutingError",
]
