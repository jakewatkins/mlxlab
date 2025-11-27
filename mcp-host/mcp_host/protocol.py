"""
MCP Protocol implementation using JSON-RPC 2.0.

This module handles encoding/decoding of MCP protocol messages,
message framing, and protocol-level validation.
"""

import json
import uuid
from typing import Any, Dict, Optional
from .types import JSONRPCRequest, JSONRPCResponse, JSONRPCNotification
from .exceptions import ProtocolError


class JSONRPCMessage:
    """Handles JSON-RPC message encoding and decoding."""
    
    @staticmethod
    def encode(msg: Dict[str, Any]) -> bytes:
        """
        Encode a message to bytes with newline delimiter.
        
        Args:
            msg: Dictionary representing the JSON-RPC message
            
        Returns:
            Bytes with newline-delimited JSON
        """
        try:
            json_str = json.dumps(msg, separators=(',', ':'))
            return (json_str + '\n').encode('utf-8')
        except (TypeError, ValueError) as e:
            raise ProtocolError(f"Failed to encode message: {e}", details={'message': msg})
    
    @staticmethod
    def decode(data: bytes) -> Dict[str, Any]:
        """
        Decode bytes to a JSON-RPC message.
        
        Args:
            data: Bytes containing JSON data
            
        Returns:
            Dictionary representing the JSON-RPC message
        """
        try:
            # Remove newline and decode
            json_str = data.decode('utf-8').strip()
            if not json_str:
                raise ProtocolError("Empty message received")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Failed to decode JSON: {e}", details={'data': data.decode('utf-8', errors='replace')})
        except UnicodeDecodeError as e:
            raise ProtocolError(f"Failed to decode UTF-8: {e}")
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique message ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def validate_message(msg: Dict[str, Any]) -> bool:
        """
        Validate that a message follows JSON-RPC 2.0 format.
        
        Args:
            msg: Message dictionary to validate
            
        Returns:
            True if valid
            
        Raises:
            ProtocolError: If message is invalid
        """
        if not isinstance(msg, dict):
            raise ProtocolError("Message must be a dictionary")
        
        if msg.get("jsonrpc") != "2.0":
            raise ProtocolError("Message must have jsonrpc: '2.0'")
        
        # Check if it's a request, response, or notification
        has_method = "method" in msg
        has_result_or_error = "result" in msg or "error" in msg
        has_id = "id" in msg
        
        if has_method:
            # Request or notification
            if not isinstance(msg["method"], str):
                raise ProtocolError("Method must be a string")
            if has_result_or_error:
                raise ProtocolError("Request/notification cannot have result or error")
        elif has_result_or_error:
            # Response
            if not has_id:
                raise ProtocolError("Response must have an id")
            if "result" in msg and "error" in msg:
                raise ProtocolError("Response cannot have both result and error")
        else:
            raise ProtocolError("Message must be a request, response, or notification")
        
        return True


class MCPProtocol:
    """Handles MCP-specific protocol messages."""
    
    # MCP Protocol version
    PROTOCOL_VERSION = "2024-11-05"
    
    @staticmethod
    def create_initialize_request(
        client_info: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an initialize request message.
        
        Args:
            client_info: Information about the client
            capabilities: Client capabilities
            
        Returns:
            JSON-RPC request for initialization
        """
        params = {
            "protocolVersion": MCPProtocol.PROTOCOL_VERSION,
            "clientInfo": client_info or {
                "name": "mcp-host",
                "version": "0.1.0"
            },
            "capabilities": capabilities or {}
        }
        
        request = JSONRPCRequest(
            method="initialize",
            params=params,
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_initialized_notification() -> Dict[str, Any]:
        """Create an initialized notification message."""
        notification = JSONRPCNotification(
            method="notifications/initialized"
        )
        return notification.to_dict()
    
    @staticmethod
    def create_tools_list_request() -> Dict[str, Any]:
        """Create a tools/list request message."""
        request = JSONRPCRequest(
            method="tools/list",
            params={},
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_prompts_list_request() -> Dict[str, Any]:
        """Create a prompts/list request message."""
        request = JSONRPCRequest(
            method="prompts/list",
            params={},
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_resources_list_request() -> Dict[str, Any]:
        """Create a resources/list request message."""
        request = JSONRPCRequest(
            method="resources/list",
            params={},
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_tool_call_request(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a tools/call request message.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            JSON-RPC request for tool call
        """
        request = JSONRPCRequest(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            },
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_prompt_get_request(prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a prompts/get request message.
        
        Args:
            prompt_name: Name of the prompt to get
            arguments: Optional arguments for the prompt
            
        Returns:
            JSON-RPC request for prompt
        """
        params: Dict[str, Any] = {"name": prompt_name}
        if arguments:
            params["arguments"] = arguments
        
        request = JSONRPCRequest(
            method="prompts/get",
            params=params,
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def create_resource_read_request(uri: str) -> Dict[str, Any]:
        """
        Create a resources/read request message.
        
        Args:
            uri: URI of the resource to read
            
        Returns:
            JSON-RPC request for resource
        """
        request = JSONRPCRequest(
            method="resources/read",
            params={"uri": uri},
            id=JSONRPCMessage.generate_id()
        )
        return request.to_dict()
    
    @staticmethod
    def parse_response(msg: Dict[str, Any]) -> JSONRPCResponse:
        """
        Parse a response message.
        
        Args:
            msg: Message dictionary
            
        Returns:
            JSONRPCResponse object
        """
        JSONRPCMessage.validate_message(msg)
        
        return JSONRPCResponse(
            jsonrpc=msg.get("jsonrpc", "2.0"),
            result=msg.get("result"),
            error=msg.get("error"),
            id=msg.get("id")
        )
    
    @staticmethod
    def create_error_response(
        request_id: Optional[str],
        code: int,
        message: str,
        data: Any = None
    ) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            request_id: ID of the request that caused the error
            code: Error code
            message: Error message
            data: Additional error data
            
        Returns:
            JSON-RPC error response
        """
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        response = JSONRPCResponse(
            error=error,
            id=request_id
        )
        return response.to_dict()
