"""
Type definitions, enums, and dataclasses for the MCP Host.

This module contains all the type definitions used throughout the MCP Host,
including protocol messages, server state, and capability definitions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ServerState(Enum):
    """State of an MCP server process."""
    STARTING = "starting"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    SHUTDOWN = "shutdown"


class TransportType(Enum):
    """Transport type for MCP server communication."""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class Tool:
    """Represents an MCP tool capability."""
    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None
    outputSchema: Optional[Dict[str, Any]] = None
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters against the input schema."""
        # Basic validation - can be extended with jsonschema
        if not self.inputSchema:
            return True
        
        required = self.inputSchema.get("required", [])
        properties = self.inputSchema.get("properties", {})
        
        # Check required parameters
        for req in required:
            if req not in params:
                return False
        
        # Check parameter types (basic check)
        for key, value in params.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    return False
        
        return True
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
            "null": type(None),
        }
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        return True


@dataclass
class Prompt:
    """Represents an MCP prompt capability."""
    name: str
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Resource:
    """Represents an MCP resource capability."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class ServerCapabilities:
    """Capabilities provided by an MCP server."""
    tools: List[Tool] = field(default_factory=list)
    prompts: List[Prompt] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def get_prompt(self, name: str) -> Optional[Prompt]:
        """Get a prompt by name."""
        for prompt in self.prompts:
            if prompt.name == name:
                return prompt
        return None
    
    def get_resource(self, uri: str) -> Optional[Resource]:
        """Get a resource by URI."""
        for resource in self.resources:
            if resource.uri == uri:
                return resource
        return None


@dataclass
class ServerInfo:
    """Information about a running MCP server."""
    name: str
    state: ServerState
    capabilities: ServerCapabilities = field(default_factory=ServerCapabilities)
    process: Any = None  # asyncio.subprocess.Process
    config: Dict[str, Any] = field(default_factory=dict)
    request_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None


@dataclass
class CacheEntry:
    """Entry in the response cache."""
    key: str
    value: Any
    created_at: datetime
    ttl: int  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl


@dataclass
class MetricsData:
    """Metrics for a server or operation."""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    latencies: List[float] = field(default_factory=list)
    
    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
    
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx] if idx < len(sorted_latencies) else sorted_latencies[-1]


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request message."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response message."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            result["error"] = self.error
        else:
            result["result"] = self.result
        return result
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error response."""
        return self.error is not None


@dataclass
class JSONRPCNotification:
    """JSON-RPC 2.0 notification message (no response expected)."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        return result
