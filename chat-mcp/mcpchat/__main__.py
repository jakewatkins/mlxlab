"""Main entry point for mcp-chat."""

import asyncio
import sys

from rich.console import Console

from .chat import ChatSession
from .mcp_client import MCPManager
from .model_loader import ModelLoader

console = Console()


async def async_main(model_path: str) -> None:
    """Async main function."""
    # Initialize MCP manager
    mcp_manager = MCPManager()
    
    try:
        # Load MCP servers
        await mcp_manager.initialize()

        # Load model
        model_loader = ModelLoader(model_path)
        model_loader.load_model()

        # Check if model supports tools
        if mcp_manager.servers:
            if model_loader.supports_tools():
                tool_count = len(mcp_manager.get_all_tools())
                console.print(f"[green]✓[/green] Model supports tool calling ({tool_count} tools available)")
            else:
                console.print("[yellow]Warning:[/yellow] Model may not support tool calling")
                console.print("[yellow]Running in basic chat mode[/yellow]")

        # Create and run chat session
        chat_session = ChatSession(model_loader, mcp_manager)
        await chat_session.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error:[/red] {e}")
        sys.exit(1)
    finally:
        # Clean up MCP servers
        await mcp_manager.shutdown_all()


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        console.print("[red]Usage:[/red] mcp-chat <huggingface-model-path>")
        console.print("\n[bold]Example:[/bold]")
        console.print("  mcp-chat mlx-community/Hermes-3-Llama-3.1-8B-4bit")
        sys.exit(1)

    model_path = sys.argv[1]

    # Run the async main function
    try:
        asyncio.run(async_main(model_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
