"""
Setup configuration for llm-cli package
"""

from setuptools import setup, find_packages

with open("requirements.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llm-cli",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Command-line interface for MLX-based LLM with MCP tool integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "mlx-lm>=0.18.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "llm-cli=llmcli.cli:main",
        ],
    },
)
