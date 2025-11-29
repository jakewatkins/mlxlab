"""
Main CLI orchestration for LLM CLI
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import load_config, load_mcp_config, ConfigError
from .model import MLXModel, ModelError
from .tool_executor import ToolExecutor
from .output_writer import OutputWriter


# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_ARGUMENT_ERROR = 2
EXIT_MODEL_ERROR = 3
EXIT_MCP_ERROR = 4
EXIT_EXECUTION_ERROR = 5
EXIT_IO_ERROR = 6

MAX_TOOL_ITERATIONS = 10


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="LLM CLI - Command-line interface for MLX-based LLM with MCP tool integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  llm-cli ibm-granite/granite-4.0-1b -p "What is today's weather?"
  llm-cli ibm-granite/granite-4.0-1b -p "Search for news" -o output.txt
  llm-cli ibm-granite/granite-4.0-1b -pf prompt.txt -o response.txt
  llm-cli ibm-granite/granite-4.0-1b -p "Hello" --no-tools --max-tokens 100
        """
    )
    
    parser.add_argument(
        "model_path",
        help="HuggingFace model path (e.g., ibm-granite/granite-4.0-1b)"
    )
    
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument(
        "-p", "--prompt",
        help="Prompt text to send to LLM"
    )
    prompt_group.add_argument(
        "-pf", "--prompt-file",
        help="Read prompt from file"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Write output to file (default: stdout)"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="Maximum tokens to generate (default: 2048)"
    )
    
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable MCP tool integration"
    )
    
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command-line arguments
    
    Args:
        args: Parsed arguments
        
    Raises:
        SystemExit: If validation fails
    """
    # Check prompt file exists
    if args.prompt_file and not Path(args.prompt_file).exists():
        print(f"Error: Prompt file not found: {args.prompt_file}", file=sys.stderr)
        sys.exit(EXIT_IO_ERROR)
    
    # Validate max_tokens
    if args.max_tokens <= 0:
        print(f"Error: --max-tokens must be positive, got {args.max_tokens}", file=sys.stderr)
        sys.exit(EXIT_ARGUMENT_ERROR)


def read_prompt(args: argparse.Namespace) -> str:
    """
    Read prompt from arguments or file
    
    Args:
        args: Parsed arguments
        
    Returns:
        Prompt text
    """
    if args.prompt:
        return args.prompt
    elif args.prompt_file:
        try:
            with open(args.prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error: Failed to read prompt file: {e}", file=sys.stderr)
            sys.exit(EXIT_IO_ERROR)
    else:
        # Should never happen due to argparse validation
        print("Error: No prompt provided", file=sys.stderr)
        sys.exit(EXIT_ARGUMENT_ERROR)


async def run_prompt(
    model: MLXModel,
    prompt: str,
    tool_executor: Optional[ToolExecutor],
    config: Dict[str, Any],
    output_writer: OutputWriter,
    max_tokens: int
) -> None:
    """
    Execute single prompt with tool support
    
    Args:
        model: Loaded MLX model
        prompt: User prompt
        tool_executor: Tool executor (or None if disabled)
        config: Configuration dict
        output_writer: Output writer
        max_tokens: Maximum tokens to generate
    """
    # Build system prompt
    system_prompt = config["SystemPrompt"]
    if tool_executor and tool_executor.get_tool_count() > 0:
        system_prompt += tool_executor.format_tools_for_prompt()
    
    # Initialize conversation
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    # Tool execution loop
    iteration = 0
    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        
        # Generate response
        response_text = ""
        try:
            for token in model.generate(
                messages=messages,
                max_tokens=max_tokens,
                temperature=config.get("temperature", 0.7)
            ):
                response_text += token
        except ModelError as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(EXIT_EXECUTION_ERROR)
        
        # Check for tool calls
        if tool_executor:
            tool_calls = model.detect_tool_calls(response_text)
            
            if tool_calls:
                # Execute tools
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["arguments"]
                    
                    # Log tool call to stderr
                    tool_executor.log_tool_call(tool_name, tool_args)
                    
                    # Execute tool
                    result, error, duration = await tool_executor.execute_tool(
                        tool_name,
                        tool_args
                    )
                    
                    # Log result to stderr
                    tool_executor.log_tool_result(result, error, duration)
                    
                    # Collect result
                    if error:
                        tool_results.append(f"Tool '{tool_name}' error: {error}")
                    else:
                        tool_results.append(f"Tool '{tool_name}' result: {result}")
                
                # Add assistant message and tool results to conversation
                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "user",
                    "content": f"Tool results:\n" + "\n".join(tool_results)
                })
                
                # Continue generation without writing tool call to output
                continue
        
        # No tool calls detected, write final response and exit
        for char in response_text:
            output_writer.write_token(char)
        break
    
    # Check if we hit max iterations
    if iteration >= MAX_TOOL_ITERATIONS:
        print(f"\nWarning: Maximum tool iterations ({MAX_TOOL_ITERATIONS}) reached", file=sys.stderr)


async def async_main():
    """Async main entry point"""
    # Parse and validate arguments
    args = parse_arguments()
    validate_arguments(args)
    
    try:
        # Load configuration
        config = load_config()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_CONFIG_ERROR)
    
    # Read prompt
    prompt = read_prompt(args)
    
    # Load model
    print(f"Loading model: {args.model_path}", file=sys.stderr)
    model = MLXModel(args.model_path)
    try:
        model.load()
    except ModelError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_MODEL_ERROR)
    
    # Initialize tool executor if not disabled
    tool_executor: Optional[ToolExecutor] = None
    if not args.no_tools:
        try:
            mcp_config = load_mcp_config()
            if mcp_config["servers"]:
                print("Starting MCP servers...", file=sys.stderr)
                tool_executor = ToolExecutor()
                await tool_executor.start()
                tool_count = tool_executor.get_tool_count()
                print(f"Discovered {tool_count} tools", file=sys.stderr)
        except ConfigError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(EXIT_CONFIG_ERROR)
        except Exception as e:
            print(f"Error: Failed to start MCP servers: {e}", file=sys.stderr)
            sys.exit(EXIT_MCP_ERROR)
    
    # Execute prompt with output writer
    try:
        with OutputWriter(args.output) as writer:
            await run_prompt(
                model=model,
                prompt=prompt,
                tool_executor=tool_executor,
                config=config,
                output_writer=writer,
                max_tokens=args.max_tokens
            )
    except IOError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_IO_ERROR)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_EXECUTION_ERROR)
    finally:
        # Cleanup: shutdown MCP servers
        if tool_executor:
            await tool_executor.shutdown()
    
    sys.exit(EXIT_SUCCESS)


def main():
    """Main entry point for llm-cli"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
