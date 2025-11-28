"""
Command-line interface and main application loop
"""

import sys
import signal
import asyncio
import logging
from typing import Optional

from llmhost.config import load_config, load_mcp_config, ConfigError
from llmhost.console import Console
from llmhost.model import MLXModel, ModelError
from llmhost.conversation import ConversationHistory
from llmhost.tool_executor import ToolExecutor

# Configure logging at WARNING level to reduce noise
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class LLMHost:
    """Main application class"""
    
    def __init__(self, model_path: str):
        """
        Initialize LLM Host
        
        Args:
            model_path: HuggingFace model path
        """
        self.model_path = model_path
        self.console = Console()
        self.model: Optional[MLXModel] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.conversation: Optional[ConversationHistory] = None
        self.running = True
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            self.console.print_info("\nShutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Load configurations
            self.console.print_info("Loading configurations...")
            config = load_config("config.json")
            # We just validate mcp.json exists, mcp-host will load it
            _ = load_mcp_config("mcp.json")
            
            # Initialize tool executor and start MCP servers
            self.console.print_info("Starting MCP servers...")
            self.tool_executor = ToolExecutor("mcp.json")
            await self.tool_executor.start()
            
            tool_count = self.tool_executor.get_tool_count()
            self.console.print_info(f"Discovered {tool_count} tools from MCP servers")
            
            # Load MLX model
            self.console.print_info(f"Loading model: {self.model_path}")
            self.model = MLXModel(self.model_path)
            self.model.load()
            
            # Initialize conversation with system prompt
            self.conversation = ConversationHistory()
            system_prompt = config["SystemPrompt"]
            
            # Append tool definitions to system prompt
            tool_definitions = self.tool_executor.format_tools_for_prompt()
            full_system_prompt = system_prompt + tool_definitions
            
            self.conversation.add_system_message(full_system_prompt)
            
            self.console.print_ready()
            
        except ConfigError as e:
            self.console.print_error(str(e))
            sys.exit(1)
        except ModelError as e:
            self.console.print_error(str(e))
            sys.exit(1)
        except Exception as e:
            self.console.print_error(f"Initialization failed: {e}")
            
            sys.exit(1)
    
    async def process_turn(self, user_input: str):
        """
        Process one conversation turn
        
        Args:
            user_input: User's input text
        """
        if not self.conversation:
            return
            
        # Add user message to history
        self.conversation.add_user_message(user_input)
        
        # Generate response
        await self._generate_response()
    
    async def _generate_response(self):
        """Generate response with potential tool calls"""
        if not self.model or not self.conversation or not self.tool_executor:
            return
            
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations and self.running:
            iteration += 1
            
            # Get messages for model
            messages = self.conversation.get_messages()
            
            # Generate response with streaming
            self.console.print_assistant_prefix()
            
            response_text = ""
            try:
                for token in self.model.generate(messages):
                    if not self.running:
                        break
                    self.console.stream_token(token)
                    response_text += token
                
                self.console.print_newline()
                
            except ModelError as e:
                self.console.print_error(str(e))
                return
            
            # Check for tool calls in response
            tool_calls = self.model.detect_tool_calls(response_text)
            
            if not tool_calls:
                # No tool calls, add response and finish
                self.conversation.add_assistant_message(response_text)
                break
            
            # Add assistant message with tool calls
            self.conversation.add_assistant_message(response_text, tool_calls)
            
            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                
                # Display tool call
                self.console.print_tool_call(tool_name, tool_args)
                
                # Execute tool
                result, error, duration = await self.tool_executor.execute_tool(
                    tool_name, 
                    tool_args,
                    timeout=90.0
                )
                
                # Display result or error
                if error:
                    self.console.print_tool_error(error, duration)
                    # Add error to conversation
                    call_id = self.conversation.add_tool_call(tool_name, tool_args)
                    self.conversation.add_tool_result(call_id, tool_name, f"ERROR: {error}")
                else:
                    self.console.print_tool_result(result or "", duration)
                    # Add result to conversation
                    call_id = self.conversation.add_tool_call(tool_name, tool_args)
                    self.conversation.add_tool_result(call_id, tool_name, result or "")
            
            # Continue to next iteration to generate response with tool results
            # (The loop will call generate again with updated history)
        
        if iteration >= max_iterations:
            self.console.print_error("Maximum tool iteration limit reached")
    
    async def run(self):
        """Main application loop"""
        self._setup_signal_handlers()
        
        while self.running:
            try:
                # Get user input
                user_input = self.console.print_prompt()
                
                # Check for exit commands
                if user_input.lower() in ["bye", "quit", "exit"]:
                    break
                
                # Skip empty input
                if not user_input.strip():
                    continue
                
                # Process the turn
                await self.process_turn(user_input)
                
            except KeyboardInterrupt:
                # Caught by signal handler
                break
            except Exception as e:
                self.console.print_error(f"Error: {e}")
    
    async def shutdown(self):
        """Cleanup and shutdown"""
        if self.tool_executor:
            self.console.print_info("Shutting down MCP servers...")
            await self.tool_executor.shutdown()


def main():
    """Main entry point"""
    # Check for model path argument
    if len(sys.argv) < 2:
        print("Error: Model path required")
        print("Usage: llm-host <model-path>")
        print("Example: llm-host ibm-granite/granite-4.0-1b")
        sys.exit(1)
    
    model_path = sys.argv[1]
    
    # Create and run application
    app = LLMHost(model_path)
    
    async def run_app():
        try:
            await app.initialize()
            await app.run()
        finally:
            await app.shutdown()
    
    # Run async application
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
