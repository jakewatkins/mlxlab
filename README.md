# MLX Lab

Experiments and projects for running Large Language Models on Apple Silicon using MLX framework.

## Projects

### 🚀 [llm-host](./llm-host) - **Production-Ready LLM with MCP Tools**
MLX-based command-line LLM with Model Context Protocol (MCP) integration for tool calling.

**Features:**
- Streaming inference with MLX
- MCP tool integration (filesystem, web search, etc.)
- Multi-turn conversations with tool execution
- Rich console output with timing metrics
- Graceful error handling and timeouts

**Usage:**
```bash
cd llm-host
llm-host ibm-granite/granite-4.0-1b
```

### 🔧 [mcp-host](./mcp-host) - **MCP Server Manager**
Python library for hosting and managing multiple Model Context Protocol servers.

**Features:**
- Multi-server management with dependency resolution
- Unified API for tools, prompts, and resources
- Request routing with retry logic
- Performance metrics and caching
- Full type safety

**Usage:**
```python
from mcp_host import MCPHost

async with MCPHost(config_path="mcp.json") as host:
    tools = await host.get_tools()
    result = await host.call_tool("search", {"query": "Python"})
```

### 💬 [chat-mcp](./chat-mcp) - **MCP-Enabled Chat**
Interactive LLM chat application with MCP server integration.

**Features:**
- Tool calling via MCP servers
- Streaming responses
- Colored output for tool execution
- Environment variable support
- Conversation history management

**Usage:**
```bash
cd chat-mcp
mcp-chat mlx-community/Hermes-3-Llama-3.1-8B-4bit
```

### 🎯 [chat](./chat) - **Simple LLM Chat**
Minimal interactive chatbot powered by MLX framework.

**Features:**
- Pure MLX inference
- Simple chat interface
- No external dependencies

**Usage:**
```bash
cd chat
llmchat mlx-community/Llama-3.2-3B-Instruct-4bit
```

### 🧪 [lab](./lab) - **Training & Fine-tuning**
Experimental scripts for model training and fine-tuning with MLX.

**Contents:**
- `train.sh` - Fine-tuning script
- `dl-model.sh` - Model download helper
- `adapters/` - LoRA adapter checkpoints
- `data/` - Training datasets

### 🔬 [lab2](./lab2) - **Model Loading Experiments**
Testing ground for various model loading approaches.

## Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python 3.10+**
- **MLX framework**
- **Node.js** (for NPX-based MCP servers)

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/jakewatkins/mlxlab.git
cd mlxlab
```

2. Choose a project and follow its README:
```bash
cd llm-host
pip install -e .
llm-host ibm-granite/granite-4.0-1b
```

## Recommended Models

### For Production (llm-host, chat-mcp)
- **IBM Granite 3.1+**: `ibm-granite/granite-3.1-8b-instruct`
- **Meta Llama 3.1+**: `meta-llama/Llama-3.1-8B-Instruct`
- **Qwen 2.5+**: `Qwen/Qwen2.5-7B-Instruct`

### For Testing
- **IBM Granite 4.0**: `ibm-granite/granite-4.0-1b` (fast, good tool calling)
- **Qwen 2.5 Micro**: `Qwen/Qwen2.5-0.5B-Instruct` (very small)

### MLX-Quantized Models
- `mlx-community/Hermes-3-Llama-3.1-8B-4bit`
- `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`
- `mlx-community/Qwen2.5-7B-Instruct-4bit`

## Project Architecture

```
mlxlab/
├── llm-host/          # Production LLM with MCP tools
│   ├── llmhost/       # Main package
│   ├── config.json    # System prompt configuration
│   └── mcp.json       # MCP server configuration
├── mcp-host/          # MCP server management library
│   └── mcp_host/      # Core library code
├── chat-mcp/          # Chat with MCP integration
│   └── mcpchat/       # Chat application
├── chat/              # Simple chat interface
│   └── llmchat/       # Chat package
├── lab/               # Training experiments
│   ├── adapters/      # LoRA checkpoints
│   └── data/          # Training data
└── lab2/              # Model loading tests
```

## Contributing

This is a personal learning repository, but contributions and suggestions are welcome! Feel free to:
- Open issues for bugs or feature requests
- Submit pull requests with improvements
- Share interesting model configurations or prompts

## License

MIT License - See individual project directories for details.

## Acknowledgments

- [MLX](https://github.com/ml-explore/mlx) - Apple's machine learning framework
- [MLX-LM](https://github.com/ml-explore/mlx-examples/tree/main/llms) - Language model examples for MLX
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool integration protocol
- [Anthropic](https://www.anthropic.com/) - For creating the MCP specification