"""
Console output formatting using rich library
"""

from datetime import datetime
from rich.console import Console as RichConsole
from rich.text import Text
import sys


class Console:
    """Handles all formatted console output for LLM Host"""
    
    def __init__(self):
        self.console = RichConsole()
        
    def _get_timestamp(self) -> str:
        """Get current time formatted as HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")
    
    def print_ready(self):
        """Display ready message after initialization"""
        self.console.print("Ready. Type your prompt or 'quit' to exit.", style="bold green")
    
    def print_prompt(self) -> str:
        """Display prompt and read user input"""
        text = Text()
        text.append("prompt -> ", style="cyan bold")
        self.console.print(text, end="")
        
        try:
            user_input = input()
            return user_input
        except EOFError:
            return "quit"
    
    def print_user_input(self, text: str):
        """Display user input (when echoing back)"""
        output = Text()
        output.append("prompt -> ", style="cyan bold")
        output.append(text, style="cyan")
        self.console.print(output)
    
    def print_tool_call(self, tool_name: str, args: dict):
        """Display tool call with timestamp"""
        timestamp = self._get_timestamp()
        
        # Format arguments for display
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        
        output = Text()
        output.append(f"[{timestamp}] ", style="dim")
        output.append("Calling tool: ", style="yellow")
        output.append(f"{tool_name}", style="yellow bold")
        output.append(f"({args_str})", style="yellow")
        output.append(" ...", style="dim")
        
        self.console.print(output)
    
    def print_tool_result(self, result: str, duration: float):
        """Display tool result with timing"""
        timestamp = self._get_timestamp()
        
        # Truncate very long results for display
        display_result = result
        if len(result) > 200:
            display_result = result[:200] + "..."
        
        output = Text()
        output.append(f"[{timestamp}] ", style="dim")
        output.append("Result: ", style="green")
        output.append(display_result, style="green")
        output.append(f" (took {duration:.2f}s)", style="dim")
        
        self.console.print(output)
    
    def print_tool_error(self, error: str, duration: float):
        """Display tool error with timing"""
        timestamp = self._get_timestamp()
        
        output = Text()
        output.append(f"[{timestamp}] ", style="dim")
        output.append("ERROR: ", style="red bold")
        output.append(error, style="red")
        output.append(f" (took {duration:.2f}s)", style="dim")
        
        self.console.print(output)
    
    def print_assistant_prefix(self):
        """Print the assistant prefix before streaming response"""
        text = Text()
        text.append("assistant -> ", style="green bold")
        self.console.print(text, end="")
    
    def stream_token(self, token: str):
        """Display single token for typewriter effect"""
        # Print without newline and flush to see immediately
        self.console.print(token, end="", style="green")
        sys.stdout.flush()
    
    def print_newline(self):
        """Print a newline after streaming is complete"""
        self.console.print()
    
    def print_assistant_response(self, text: str):
        """Display complete assistant response (non-streaming fallback)"""
        output = Text()
        output.append("assistant -> ", style="green bold")
        output.append(text, style="green")
        self.console.print(output)
    
    def print_error(self, error: str):
        """Display general error message"""
        self.console.print(f"Error: {error}", style="red bold")
    
    def print_info(self, message: str):
        """Display informational message"""
        self.console.print(message, style="blue")
