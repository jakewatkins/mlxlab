"""
Setup configuration for mcp-host package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-host",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python module for hosting and managing MCP servers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mcp-host",
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
        # No external dependencies - uses only Python stdlib
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "mypy>=1.0",
            "black>=23.0",
            "isort>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            # Add CLI commands here if needed
        ],
    },
)
