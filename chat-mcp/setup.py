from setuptools import setup, find_packages

setup(
    name="mcp-chat",
    version="0.1.0",
    description="LLM chat application with MCP server integration",
    author="Jake Watkins",
    packages=find_packages(),
    install_requires=[
        "mlx-lm>=0.18.0",
        "mcp>=0.9.0",
        "transformers",
        "huggingface-hub",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-chat=mcpchat.__main__:main",
        ],
    },
    python_requires=">=3.9",
)
