"""
Server process management for MCP Host.

Handles starting, stopping, and communicating with MCP server processes.
"""

import asyncio
import logging
import os
import signal
from typing import Any, Dict, Optional, Callable
from asyncio.subprocess import Process
from .types import JSONRPCRequest, JSONRPCResponse, ServerState
from .protocol import JSONRPCMessage, MCPProtocol
from .exceptions import ServerStartupError, TimeoutError as MCPTimeoutError, ProtocolError

logger = logging.getLogger(__name__)


class ServerProcess:
    """Manages a single MCP server process and its communication."""
    
    def __init__(self, name: str):
        """
        Initialize server process.
        
        Args:
            name: Name of the server
        """
        self.name = name
        self.process: Optional[Process] = None
        self.state = ServerState.SHUTDOWN
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._notification_handler: Optional[Callable] = None
    
    async def start(
        self,
        command: str,
        args: list[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> None:
        """
        Start the server process.
        
        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables
            cwd: Working directory
            
        Raises:
            ServerStartupError: If process fails to start
        """
        self.state = ServerState.STARTING
        
        try:
            # Merge environment variables with current environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # Start the process
            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=cwd
            )
            
            logger.info(f"Server '{self.name}' process started with PID {self.process.pid}")
            
            # Start reading messages from stdout
            self._read_task = asyncio.create_task(self._read_loop())
            
            # Start reading stderr for error logging
            self._stderr_task = asyncio.create_task(self._read_stderr())
            
        except FileNotFoundError:
            raise ServerStartupError(
                f"Command not found: {command}",
                server_name=self.name
            )
        except Exception as e:
            raise ServerStartupError(
                f"Failed to start server: {e}",
                server_name=self.name
            )
    
    async def _read_loop(self) -> None:
        """Continuously read messages from the server."""
        if not self.process or not self.process.stdout:
            return
        
        try:
            while True:
                # Read line
                line = await self.process.stdout.readline()
                if not line:
                    # EOF - process terminated
                    logger.warning(f"Server '{self.name}' stdout closed")
                    break
                
                try:
                    # Decode message
                    msg = JSONRPCMessage.decode(line)
                    await self._handle_message(msg)
                except ProtocolError as e:
                    logger.error(f"Protocol error from server '{self.name}': {e}")
                except Exception as e:
                    logger.error(f"Error handling message from server '{self.name}': {e}")
        
        except asyncio.CancelledError:
            pass  # Clean shutdown
        except Exception as e:
            logger.error(f"Read loop error for server '{self.name}': {e}")
    
    async def _read_stderr(self) -> None:
        """Continuously read and log stderr from the server."""
        if not self.process or not self.process.stderr:
            return
        
        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                
                # Log stderr output
                stderr_text = line.decode('utf-8', errors='replace').strip()
                if stderr_text:
                    logger.error(f"Server '{self.name}' stderr: {stderr_text}")
        
        except asyncio.CancelledError:
            pass  # Clean shutdown
        except Exception as e:
            logger.error(f"Stderr read loop error for server '{self.name}': {e}")
    
    async def _handle_message(self, msg: Dict[str, Any]) -> None:
        """
        Handle an incoming message from the server.
        
        Args:
            msg: Message dictionary
        """
        # Check if it's a response or notification
        if "id" in msg:
            # Response to our request
            msg_id = msg["id"]
            if msg_id in self._pending_responses:
                future = self._pending_responses.pop(msg_id)
                if not future.done():
                    future.set_result(msg)
            else:
                logger.warning(f"Received response for unknown request ID: {msg_id}")
        else:
            # Notification from server
            if self._notification_handler:
                await self._notification_handler(self.name, msg)
            # Otherwise silently ignore notifications
    
    async def send_message(self, msg: Dict[str, Any]) -> None:
        """
        Send a message to the server.
        
        Args:
            msg: Message dictionary
            
        Raises:
            ServerStartupError: If process is not running
        """
        if not self.process or not self.process.stdin:
            raise ServerStartupError(
                f"Server process not running",
                server_name=self.name
            )
        
        try:
            encoded = JSONRPCMessage.encode(msg)
            self.process.stdin.write(encoded)
            await self.process.stdin.drain()
        except Exception as e:
            logger.error(f"Failed to send message to server '{self.name}': {e}")
            raise
    
    async def wait_for_response(self, msg_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Wait for a response to a request.
        
        Args:
            msg_id: Message ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            Response message
            
        Raises:
            TimeoutError: If response not received within timeout
        """
        # Create future for this request
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[msg_id] = future
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            # Clean up future
            self._pending_responses.pop(msg_id, None)
            raise MCPTimeoutError(
                f"Timeout waiting for response from server '{self.name}'",
                operation="wait_for_response",
                timeout_seconds=timeout
            )
    
    async def send_request(
        self,
        msg: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send a request and wait for response.
        
        Args:
            msg: Request message (must have 'id' field)
            timeout: Timeout in seconds
            
        Returns:
            Response message
        """
        msg_id = msg.get("id")
        if not msg_id:
            raise ProtocolError("Request message must have an 'id' field")
        
        # Send message
        await self.send_message(msg)
        
        # Wait for response
        return await self.wait_for_response(msg_id, timeout)
    
    async def shutdown(self, timeout: float = 10.0) -> None:
        """
        Shutdown the server process gracefully.
        
        Args:
            timeout: Time to wait for graceful shutdown before forcing
        """
        if not self.process:
            return
        
        logger.info(f"Shutting down server '{self.name}'")
        self.state = ServerState.SHUTDOWN
        
        # Cancel read tasks
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
        
        # Close stdin to signal shutdown
        if self.process.stdin:
            self.process.stdin.close()
            try:
                await self.process.stdin.wait_closed()
            except Exception:
                pass
        
        # Wait for process to terminate
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
            logger.info(f"Server '{self.name}' terminated gracefully")
        except asyncio.TimeoutError:
            # Force kill
            logger.warning(f"Server '{self.name}' did not terminate, forcing kill")
            try:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error killing server '{self.name}': {e}")
        
        # Cancel any pending responses
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
    
    def is_alive(self) -> bool:
        """Check if the process is running."""
        if not self.process:
            return False
        return self.process.returncode is None
    
    def get_exit_code(self) -> Optional[int]:
        """Get the process exit code."""
        if not self.process:
            return None
        return self.process.returncode
    
    def set_notification_handler(self, handler: Callable) -> None:
        """
        Set handler for server notifications.
        
        Args:
            handler: Async function(server_name, msg) to handle notifications
        """
        self._notification_handler = handler


class ServerManager:
    """Manages multiple MCP server processes."""
    
    def __init__(self):
        """Initialize the server manager."""
        self.servers: Dict[str, ServerProcess] = {}
    
    async def create_server(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> ServerProcess:
        """
        Create and start a server process.
        
        Args:
            name: Server name
            config: Server configuration
            
        Returns:
            ServerProcess instance
        """
        server = ServerProcess(name)
        
        # Start the process
        await server.start(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
            cwd=config.get("cwd")
        )
        
        self.servers[name] = server
        return server
    
    async def initialize_server(
        self,
        server: ServerProcess,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Initialize a server using the MCP protocol.
        
        Args:
            server: Server process
            timeout: Initialization timeout
            
        Returns:
            Server capabilities from initialize response
        """
        # Send initialize request
        init_request = MCPProtocol.create_initialize_request()
        response = await server.send_request(init_request, timeout=timeout)
        
        # Parse response
        parsed = MCPProtocol.parse_response(response)
        if parsed.is_error:
            raise ServerStartupError(
                f"Server initialization failed: {parsed.error}",
                server_name=server.name
            )
        
        # Send initialized notification
        initialized = MCPProtocol.create_initialized_notification()
        await server.send_message(initialized)
        
        # Mark as ready
        server.state = ServerState.READY
        logger.info(f"Server '{server.name}' initialized successfully")
        
        return parsed.result or {}
    
    async def shutdown_server(
        self,
        server: ServerProcess,
        timeout: float = 10.0
    ) -> None:
        """
        Shutdown a server.
        
        Args:
            server: Server to shutdown
            timeout: Shutdown timeout
        """
        await server.shutdown(timeout)
        if server.name in self.servers:
            del self.servers[server.name]
    
    async def shutdown_all(self, timeout: float = 10.0) -> None:
        """
        Shutdown all servers.
        
        Args:
            timeout: Shutdown timeout per server
        """
        tasks = [
            server.shutdown(timeout)
            for server in self.servers.values()
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.servers.clear()
