"""
Setup configuration for llm-server package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="llm-server",
    version="0.1.0",
    author="Jake Watkins",
    description="HTTP server for MLX-based LLM inference with MCP tool support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
    ],
    python_requires=">=3.10",
    install_requires=[
        "mlx-lm>=0.14.0",
    ],
    entry_points={
        "console_scripts": [
            "llm-server=llmserver.server:main",
        ],
    },
)
