"""
HTTP server for LLM inference
"""

import asyncio
import json
import logging
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional
from pathlib import Path

# Add parent directory to path to import mcp_host
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-host"))

from mcp_host import MCPHost

from llmserver.config import Config
from llmserver.logger import setup_logging
from llmserver.model import MLXModel, ModelError


logger = logging.getLogger(__name__)


class LLMServer:
    """Main LLM Server application"""
    
    def __init__(self):
        """Initialize server"""
        self.config: Optional[Config] = None
        self.model: Optional[MLXModel] = None
        self.mcp_host: Optional[MCPHost] = None
        self.http_server: Optional[HTTPServer] = None
        self.shutdown_requested = False
        self.active_requests = 0
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
    
    def load_config(self):
        """Load configuration"""
        try:
            self.config = Config("config.json")
            logger.info("Configuration loaded successfully")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    async def setup_mcp(self):
        """Setup MCP host and servers"""
        if not self.config or not self.config.servers:
            logger.info("No MCP servers configured")
            return
        
        try:
            # Create temporary mcp.json for MCPHost
            # Note: MCPHost expects "servers" not "mcpServers"
            mcp_config = {"servers": self.config.servers}
            mcp_path = Path.cwd() / ".llmserver_mcp.json"
            
            with open(mcp_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
            
            logger.info("Starting MCP servers...")
            self.mcp_host = MCPHost(config_path=str(mcp_path))
            await self.mcp_host.__aenter__()
            
            # Get available tools
            tools = await self.mcp_host.get_tools()
            logger.info(f"MCP initialized with {len(tools)} tools")
            
        except Exception as e:
            logger.warning(f"Failed to initialize MCP servers: {e}")
            logger.warning("Continuing without MCP support")
            self.mcp_host = None
    
    def load_model(self):
        """Load MLX model"""
        if not self.config:
            logger.error("Configuration not loaded")
            sys.exit(1)
        
        try:
            self.model = MLXModel(
                model_path=self.config.model_name,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                min_p=self.config.min_p,
                min_tokens_to_keep=self.config.min_tokens_to_keep
            )
            self.model.load()
            logger.info("Model loaded successfully")
        except ModelError as e:
            logger.error(f"Failed to load model: {e}")
            sys.exit(1)
    
    def parse_tool_calls(self, text: str) -> list:
        """
        Parse tool calls from LLM response
        
        Args:
            text: Generated text to parse
            
        Returns:
            List of tool calls with name and arguments
        """
        import re
        tool_calls = []
        
        # Look for <tool_call> XML tags with JSON inside
        # Use non-greedy match to capture complete JSON object including nested braces
        pattern = r'<tool_call>\s*(\{.+?\})\s*</tool_call>'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                tool_data = json.loads(match.group(1))
                if "name" in tool_data and "arguments" in tool_data:
                    tool_calls.append(tool_data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call JSON: {match.group(1)}")
                continue
        
        return tool_calls
    
    async def process_request(self, prompt: str) -> str:
        """
        Process a request with the LLM
        
        Args:
            prompt: User prompt
            
        Returns:
            Generated response
        """
        if not self.model or not self.config:
            raise Exception("Server not properly initialized")
        
        # Get available tools if MCP is configured
        available_tools = {}
        tools_description = ""
        
        if self.mcp_host:
            try:
                tools = await self.mcp_host.get_tools()
                # Create a mapping of tool names to server.tool format
                for tool in tools:
                    tool_key = f"{tool['server']}.{tool['name']}"
                    available_tools[tool_key] = tool
                    # Also map just the tool name for easier lookup
                    available_tools[tool['name']] = tool
                
                logger.info(f"Available tools: {list(available_tools.keys())}")
                
                # Build tools description for the LLM
                if tools:
                    tools_list = []
                    for tool in tools:
                        tool_desc = f"\n- **{tool['name']}**: {tool.get('description', 'No description')}"
                        if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                            params = tool['inputSchema']['properties']
                            required = tool['inputSchema'].get('required', [])
                            param_list = []
                            for param_name, param_info in params.items():
                                req_marker = " (required)" if param_name in required else ""
                                param_desc = param_info.get('description', 'No description')
                                param_list.append(f"    - `{param_name}`: {param_desc}{req_marker}")
                            if param_list:
                                tool_desc += "\n  Parameters:\n" + "\n".join(param_list)
                        tools_list.append(tool_desc)
                    
                    tools_description = "\n\nAVAILABLE TOOLS:\n" + "\n".join(tools_list)
                    logger.debug(f"Tools description: {tools_description}")
                    
            except Exception as e:
                logger.error(f"Failed to get MCP tools: {e}")
        
        # Build messages with system prompt and tools
        system_content = self.config.system_prompt
        if tools_description:
            system_content += tools_description
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]
        
        # Generate initial response
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Generation iteration {iteration}")
            
            # Generate response
            response = self.model.generate(messages)
            logger.debug(f"Generated response: {response[:200]}...")
            
            # Parse tool calls from response
            tool_calls = self.parse_tool_calls(response)
            
            if not tool_calls or not self.mcp_host:
                # No tool calls or no MCP, return the response
                return response
            
            logger.info(f"Found {len(tool_calls)} tool call(s)")
            
            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                try:
                    # Try to find the tool in available tools
                    tool_key = None
                    if tool_name in available_tools:
                        # Direct match or server.tool match
                        tool_key = tool_name
                    else:
                        # Search for tool name in server.tool format
                        for key in available_tools.keys():
                            if key.endswith(f".{tool_name}"):
                                tool_key = key
                                break
                    
                    if not tool_key:
                        logger.warning(f"Tool '{tool_name}' not found in available tools")
                        tool_results.append({
                            "tool": tool_name,
                            "result": f"Error: Tool '{tool_name}' not available"
                        })
                        continue
                    
                    # Execute the tool
                    result = await self.mcp_host.call_tool(tool_key, tool_args)
                    logger.info(f"Tool result: {str(result)[:200]}...")
                    
                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                    
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}")
                    tool_results.append({
                        "tool": tool_name,
                        "result": f"Error: {str(e)}"
                    })
            
            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response})
            
            # Format tool results for the model
            tool_results_text = "\n\n".join([
                f"Tool '{r['tool']}' returned:\n{json.dumps(r['result'], indent=2)}"
                for r in tool_results
            ])
            
            messages.append({
                "role": "user",
                "content": f"Tool results:\n{tool_results_text}\n\nPlease provide a final answer based on these results."
            })
            
            # Continue loop to generate final response
        
        # If we hit max iterations, return last response
        logger.warning(f"Hit max iterations ({max_iterations}), returning last response")
        return response
    
    def create_request_handler(self):
        """Create HTTP request handler class"""
        server_instance = self
        
        class LLMRequestHandler(BaseHTTPRequestHandler):
            """HTTP request handler"""
            
            def log_message(self, format, *args):
                """Override to use our logger"""
                logger.info(f"{self.address_string()} - {format % args}")
            
            def do_POST(self):
                """Handle POST requests"""
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._handle_post())
                finally:
                    loop.close()
            
            async def _handle_post(self):
                """Async POST handler"""
                try:
                    # Track active request
                    server_instance.active_requests += 1
                    
                    # Check content length
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 10 * 1024 * 1024:  # 10MB limit
                        self.send_error_response(400, "Request too large (max 10MB)")
                        return
                    
                    # Read and parse request body
                    try:
                        body = self.rfile.read(content_length)
                        data = json.loads(body.decode('utf-8'))
                    except json.JSONDecodeError:
                        self.send_error_response(400, "Invalid JSON")
                        return
                    except Exception as e:
                        self.send_error_response(400, f"Error reading request: {e}")
                        return
                    
                    # Validate request has "prompt" field
                    if "prompt" not in data:
                        self.send_error_response(400, "Missing 'prompt' field")
                        return
                    
                    prompt = data["prompt"]
                    logger.info(f"Received request with prompt length: {len(prompt)}")
                    
                    # Process request
                    try:
                        response = await server_instance.process_request(prompt)
                        logger.info(f"Generated response length: {len(response)}")
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        
                        response_data = {"response": response}
                        self.wfile.write(json.dumps(response_data).encode('utf-8'))
                        
                    except Exception as e:
                        logger.error(f"Error processing request: {e}", exc_info=True)
                        self.send_error_response(500, f"Error processing request: {e}")
                
                finally:
                    # Decrement active request counter
                    server_instance.active_requests -= 1
            
            def send_error_response(self, code: int, message: str):
                """Send error response"""
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                error_data = {"Error": message}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))
        
        return LLMRequestHandler
    
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """HTTP Server with threading support"""
        daemon_threads = True
        allow_reuse_address = True
    
    def start_http_server(self):
        """Start HTTP server"""
        if not self.config:
            logger.error("Configuration not loaded")
            sys.exit(1)
        
        try:
            handler_class = self.create_request_handler()
            self.http_server = self.ThreadedHTTPServer(
                ('', self.config.listening_port),
                handler_class
            )
            
            logger.info(f"HTTP server listening on port {self.config.listening_port}")
            print(f"LLM Server started on port {self.config.listening_port}")
            print("Press Ctrl+C to stop the server")
            
            # Use serve_forever which can be interrupted
            try:
                self.http_server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Received KeyboardInterrupt")
                raise
            
        except KeyboardInterrupt:
            # Re-raise to be caught by main()
            raise
        except OSError as e:
            logger.error(f"Failed to start HTTP server on port {self.config.listening_port}: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error starting HTTP server: {e}")
            sys.exit(1)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Initiating graceful shutdown...")
        
        # Stop accepting new requests
        if self.http_server:
            logger.info("Shutting down HTTP server...")
            self.http_server.shutdown()
        
        # Wait for active requests to complete
        logger.info(f"Waiting for {self.active_requests} active requests to complete...")
        while self.active_requests > 0:
            await asyncio.sleep(0.1)
        
        logger.info("All requests completed")
        
        # Shutdown MCP servers
        if self.mcp_host:
            logger.info("Shutting down MCP servers...")
            try:
                await self.mcp_host.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error shutting down MCP: {e}")
        
        # Unload model
        if self.model:
            logger.info("Unloading model...")
            self.model.unload()
        
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    server = LLMServer()
    loop = None
    
    try:
        # Load configuration
        server.load_config()
        
        # Setup logging
        if server.config:
            setup_logging(server.config.log_filename, server.config.log_level)
            logger.info("LLM Server starting...")
        
        # Initialize components
        # Setup MCP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.setup_mcp())
        
        # Load model
        server.load_model()
        
        # Start HTTP server (blocking until Ctrl+C or shutdown)
        server.start_http_server()
        
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        logger.info("Interrupted by user")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Cleanup
        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            logger.info("Running shutdown sequence...")
            loop.run_until_complete(server.shutdown())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            loop.close()
            logger.info("Server stopped")


if __name__ == "__main__":
    main()
