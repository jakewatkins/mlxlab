"""Main chat loop and conversation management."""

import asyncio
import json
import signal
import sys
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.panel import Panel

from .mcp_client import MCPManager
from .model_loader import ModelLoader, load_system_prompt

console = Console()


class ChatSession:
    """Manages the chat conversation and tool execution."""

    def __init__(self, model_loader: ModelLoader, mcp_manager: MCPManager):
        self.model_loader = model_loader
        self.mcp_manager = mcp_manager
        self.conversation_history: List[Dict[str, str]] = []
        self.max_turns = 3
        self.system_prompt = self._build_system_prompt()
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)

    def _build_system_prompt(self) -> str:
        """Build system prompt with tool schemas."""
        base_prompt = load_system_prompt()
        
        # Get tools from MCP servers
        tools = self.mcp_manager.get_all_tools()
        
        if not tools:
            return base_prompt
        
        # Add tool schemas to system prompt
        tool_descriptions = "\n\n## Available Tools\n\n"
        tool_descriptions += "You have access to the following tools. Use the EXACT parameter names shown below:\n\n"
        
        for tool in tools:
            if tool.get('type') == 'function':
                toolFunction = tool.get('function')
                tool_descriptions += f"### {toolFunction['name']}\n"
                tool_descriptions += f"{toolFunction.get('description', 'No description')}\n\n"
                tool_descriptions += "**Parameters:**\n```json\n"
                tool_descriptions += json.dumps(toolFunction.get('parameters', {}), indent=2)
                tool_descriptions += "\n```\n\n"
        
        return base_prompt + tool_descriptions

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        self.running = False
        # Exit immediately on Ctrl+C
        sys.exit(0)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        
        # Keep only last N turns (N user + N assistant messages)
        # Count pairs of user/assistant messages
        turn_count = 0
        for i in range(len(self.conversation_history) - 1, -1, -1):
            if self.conversation_history[i]["role"] == "user":
                turn_count += 1
            if turn_count > self.max_turns:
                # Remove old messages, but keep system message if present
                system_msgs = [m for m in self.conversation_history if m["role"] == "system"]
                recent_msgs = self.conversation_history[i:]
                self.conversation_history = system_msgs + recent_msgs
                break

    def get_messages_for_model(self) -> List[Dict[str, str]]:
        """Get messages formatted for the model."""
        messages = []
        
        # Add system prompt if configured
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        return messages

    async def process_user_input(self, user_input: str) -> None:
        """Process user input and generate response."""
        # Add user message to history
        self.add_message("user", user_input)

        # Get tools from MCP servers
        tools = self.mcp_manager.get_all_tools()

        # Generate response with potential tool calls
        await self._generate_with_tools(tools)

    async def _generate_with_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Generate response and handle tool calls."""
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get current messages
            messages = self.get_messages_for_model()

            # Generate response
            console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")
            response = self.model_loader.generate_response(messages, tools)

            # Check for tool calls
            tool_calls = self.model_loader.extract_tool_calls(response)

            if not tool_calls:
                # No tool calls, just a normal response
                self.add_message("assistant", response)
                break

            # Handle tool calls
            console.print(f"\n[yellow]Found {len(tool_calls)} tool call(s)[/yellow]")
            
            # Add assistant message with tool calls
            self.add_message("assistant", response)

            # Execute each tool call
            tool_results = []
            for tool_call in tool_calls:
                try:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})

                    if not tool_name:
                        console.print(Panel(
                            f"[red]Malformed tool call:[/red]\n{tool_call}",
                            title="[red]Error[/red]",
                            border_style="red"
                        ))
                        continue

                    # Call the tool
                    result = await self.mcp_manager.call_tool(tool_name, tool_args)
                    
                    # Extract content from MCP result
                    if hasattr(result, 'content'):
                        # Handle list of content items
                        if isinstance(result.content, list):
                            content_text = []
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    content_text.append(item.text)
                                else:
                                    content_text.append(str(item))
                            result_data = "\n".join(content_text)
                        else:
                            result_data = str(result.content)
                    else:
                        result_data = str(result)
                    
                    tool_results.append({
                        "tool": tool_name,
                        "result": result_data
                    })

                except TimeoutError as e:
                    console.print(f"[red]Tool timeout:[/red] {e}")
                    tool_results.append({
                        "tool": tool_name,
                        "error": str(e)
                    })
                    # Continue with other tools

                except Exception as e:
                    console.print(Panel(
                        f"[red]Tool execution error:[/red]\n{str(e)}",
                        title=f"[red]Error calling {tool_name}[/red]",
                        border_style="red"
                    ))
                    tool_results.append({
                        "tool": tool_name,
                        "error": str(e)
                    })
                    # Continue with other tools

            # Add tool results to conversation
            if tool_results:
                tool_message = f"Tool results:\n{json.dumps(tool_results, indent=2)}"
                self.add_message("user", tool_message)
                # Continue loop to generate next response
            else:
                break

        if iteration >= max_iterations:
            console.print(f"\n[yellow]Warning: Reached maximum iterations ({max_iterations})[/yellow]")

    async def run(self) -> None:
        """Run the main chat loop."""
        console.print("\n[bold green]Welcome to mcp-chat![/bold green]")
        console.print("[dim]Type 'bye' or 'quit' to exit, or press Ctrl+C[/dim]\n")

        while self.running:
            try:
                # Get user input
                user_input = console.input("[bold blue]prompt -> [/bold blue]").strip()

                # Check for exit commands
                if user_input.lower() in ["bye", "quit", "exit"]:
                    console.print("\n[yellow]Goodbye![/yellow]")
                    break

                # Skip empty input
                if not user_input:
                    continue

                # Process the input
                await self.process_user_input(user_input)

            except EOFError:
                # Handle EOF (Ctrl+D)
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                console.print("\n[yellow]Interrupted![/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error:[/red] {e}")
                # Continue running after errors


import json
