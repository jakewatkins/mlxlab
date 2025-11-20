"""MLX model loading and tool-calling integration."""

import json
from typing import Any, Dict, List, Optional

import mlx.core as mx
from mlx_lm import load, generate
from rich.console import Console

console = Console()


class ModelLoader:
    """Handles loading and interacting with MLX models."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None

    def load_model(self) -> None:
        """Load the model and tokenizer from HuggingFace."""
        console.print(f"\n[bold]Loading model: {self.model_path}[/bold]")
        try:
            self.model, self.tokenizer = load(self.model_path)
            console.print(f"[green]✓[/green] Model loaded successfully\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to load model: {e}")
            raise

    def supports_tools(self) -> bool:
        """Check if the model's tokenizer supports tool calling."""
        if not self.tokenizer:
            return False
        
        # Check if tokenizer has chat template with tool support
        chat_template = getattr(self.tokenizer, "chat_template", None)
        if chat_template and ("tools" in chat_template or "tool" in chat_template):
            return True
        
        return False

    def format_messages_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Format messages with tools using the model's chat template."""
        if not self.tokenizer:
            raise RuntimeError("Tokenizer not loaded")

        try:
            # Use apply_chat_template with tools if available
            if tools and self.supports_tools():
                formatted = self.tokenizer.apply_chat_template(
                    messages,
                    tools=tools,
                    add_generation_prompt=True,
                    tokenize=False,
                )
            else:
                formatted = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=False,
                )
            return formatted
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error formatting with chat template: {e}")
            # Fallback to simple formatting
            return self._simple_format(messages)

    def _simple_format(self, messages: List[Dict[str, str]]) -> str:
        """Simple fallback message formatting."""
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"System: {content}\n\n"
            elif role == "user":
                formatted += f"User: {content}\n\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n\n"
        formatted += "Assistant: "
        return formatted

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a response from the model."""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")

        # Format the prompt
        prompt = self.format_messages_with_tools(messages, tools)

        # Generate response with streaming
        try:
            response = ""
            for text in generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,
            ):
                # Print streaming output
                print(text, end="", flush=True)
                response += text

            print()  # New line after generation
            return response

        except Exception as e:
            console.print(f"\n[red]Error during generation:[/red] {e}")
            raise

    def extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from the model response."""
        tool_calls = []

        # Try to find tool calls in various formats
        # Format 1: <tool_call>...</tool_call> (Hermes style)
        import re
        
        # Hermes format
        hermes_pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(hermes_pattern, response, re.DOTALL)
        for match in matches:
            try:
                tool_data = json.loads(match.strip())
                tool_calls.append(tool_data)
            except json.JSONDecodeError:
                pass

        # Format 2: Look for JSON with "name" and "arguments" keys
        if not tool_calls:
            json_pattern = r'\{[^{}]*"name"[^{}]*"arguments"[^{}]*\}'
            matches = re.findall(json_pattern, response)
            for match in matches:
                try:
                    tool_data = json.loads(match)
                    if "name" in tool_data and "arguments" in tool_data:
                        tool_calls.append(tool_data)
                except json.JSONDecodeError:
                    pass

        # Format 3: Try parsing entire response as JSON
        if not tool_calls:
            try:
                data = json.loads(response.strip())
                if isinstance(data, dict) and "name" in data:
                    tool_calls.append(data)
                elif isinstance(data, list):
                    tool_calls.extend([t for t in data if isinstance(t, dict) and "name" in t])
            except json.JSONDecodeError:
                pass

        return tool_calls


def load_system_prompt(config_path: str = "config.json") -> Optional[str]:
    """Load system prompt from config file."""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("system_prompt")
    except FileNotFoundError:
        return None
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Error loading config: {e}")
        return None
