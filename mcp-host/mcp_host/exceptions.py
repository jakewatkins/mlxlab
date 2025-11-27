"""
Custom exception classes for the MCP Host.

All exceptions inherit from MCPHostError for easy catching of all
host-related errors.
"""

from typing import Any, Dict, Optional


class MCPHostError(Exception):
    """Base exception for all MCP Host errors."""
    pass


class ConfigurationError(MCPHostError):
    """Raised when there is an error in the configuration file."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, field: Optional[str] = None):
        self.config_path = config_path
        self.field = field
        super().__init__(message)


class ServerStartupError(MCPHostError):
    """Raised when a server fails to start or initialize."""
    
    def __init__(self, message: str, server_name: Optional[str] = None):
        self.server_name = server_name
        super().__init__(message)


class ServerUnavailableError(MCPHostError):
    """Raised when attempting to use an unavailable server."""
    
    def __init__(self, message: str, server_name: Optional[str] = None):
        self.server_name = server_name
        super().__init__(message)


class ValidationError(MCPHostError):
    """Raised when validation fails (config, parameters, messages)."""
    
    def __init__(self, message: str, validation_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.validation_type = validation_type
        self.details = details or {}
        super().__init__(message)


class TimeoutError(MCPHostError):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, operation: Optional[str] = None, timeout_seconds: Optional[float] = None):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(message)


class ProtocolError(MCPHostError):
    """Raised when there is a protocol-level error."""
    
    def __init__(self, message: str, protocol_version: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.protocol_version = protocol_version
        self.details = details or {}
        super().__init__(message)


class RoutingError(MCPHostError):
    """Raised when a request cannot be routed to a server."""
    
    def __init__(self, message: str, target: Optional[str] = None, reason: Optional[str] = None):
        self.target = target
        self.reason = reason
        super().__init__(message)
