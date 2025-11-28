# MCP Host - Packaging & Distribution Guide

## 📦 Package Installation Options

### Option 1: Install from Local Directory (Development)

Best for active development and testing:

```bash
# Install in editable mode
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

### Option 2: Install from Local Directory (Production)

For use in other projects on the same machine:

```bash
# Direct install
pip install /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host

# Or from your project's requirements.txt
echo "mcp-host @ file:///Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host" >> requirements.txt
pip install -r requirements.txt
```

### Option 3: Build and Install as Wheel

Create a distributable wheel file:

```bash
# Install build tools
pip install build

# Build the package
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host
python -m build

# This creates:
# - dist/mcp_host-0.1.0-py3-none-any.whl
# - dist/mcp-host-0.1.0.tar.gz

# Install the wheel in another project
pip install /path/to/mcp-host/dist/mcp_host-0.1.0-py3-none-any.whl
```

### Option 4: Install from Git Repository

If you push to GitHub/GitLab:

```bash
# Install directly from git
pip install git+https://github.com/jakewatkins/mcp-host.git

# Or specific branch/tag
pip install git+https://github.com/jakewatkins/mcp-host.git@main
pip install git+https://github.com/jakewatkins/mcp-host.git@v0.1.0

# In requirements.txt
mcp-host @ git+https://github.com/jakewatkins/mcp-host.git
```

### Option 5: Publish to PyPI (Public)

For public distribution:

```bash
# Install twine
pip install twine

# Build the package
python -m build

# Upload to PyPI
twine upload dist/*

# Then anyone can install with:
pip install mcp-host
```

### Option 6: Private Package Server

For internal use:

```bash
# Upload to private PyPI server
twine upload --repository-url https://your-pypi-server.com dist/*

# Install from private server
pip install --index-url https://your-pypi-server.com mcp-host
```

## 🎯 Recommended Approach for Your Use Case

### For Development (Current Project)
```bash
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host
pip install -e ".[dev]"
```

### For Other Local Projects
Create a `requirements.txt` in your other project:

```txt
# requirements.txt
mcp-host @ file:///Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host
```

Or use the built wheel:

```bash
# Build once
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host
python -m build

# Use in other projects
pip install /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host/dist/mcp_host-0.1.0-py3-none-any.whl
```

## 📝 Usage in Other Projects

Once installed, use it like any other package:

```python
# your_project/main.py
from mcp_host import MCPHost
import asyncio

async def main():
    async with MCPHost(config_path="mcp.json") as host:
        tools = await host.get_tools()
        print(f"Available tools: {len(tools)}")
        
        result = await host.call_tool("search", {"query": "test"})
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 Building for Distribution

### Create a Wheel Package

```bash
# Install build tools if not already installed
pip install build twine

# Navigate to the package directory
cd /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host

# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Build the package
python -m build

# Verify the built package
twine check dist/*
```

This creates:
- `dist/mcp_host-0.1.0-py3-none-any.whl` - Wheel file (recommended)
- `dist/mcp-host-0.1.0.tar.gz` - Source distribution

### Test the Built Package

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate  # On macOS/Linux

# Install the built wheel
pip install dist/mcp_host-0.1.0-py3-none-any.whl

# Test import
python -c "from mcp_host import MCPHost; print('Success!')"

# Deactivate and cleanup
deactivate
rm -rf test_env
```

## 📤 Sharing the Package

### Share the Wheel File
Simply copy `dist/mcp_host-0.1.0-py3-none-any.whl` to another machine and:

```bash
pip install mcp_host-0.1.0-py3-none-any.whl
```

### Share via Git
```bash
# In the mcp-host directory
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/jakewatkins/mcp-host.git
git push -u origin main

# Others can install with:
pip install git+https://github.com/jakewatkins/mcp-host.git
```

## 🔍 Verifying Installation

After installation in another project:

```bash
# Check installation
pip show mcp-host

# Verify imports work
python -c "from mcp_host import MCPHost; print(MCPHost.__doc__)"

# Check version
python -c "import mcp_host; print(mcp_host.__version__)"
```

## 📋 Version Management

To update the version:

1. Edit `pyproject.toml`: change `version = "0.1.0"` to new version
2. Edit `mcp_host/__init__.py`: change `__version__ = "0.1.0"`
3. Rebuild: `python -m build`
4. Reinstall in projects: `pip install --upgrade mcp-host`

## 🎬 Quick Start for New Project

```bash
# In your new project directory
mkdir my_llm_project
cd my_llm_project

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install mcp-host
pip install /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host

# Create your script
cat > main.py << 'EOF'
import asyncio
from mcp_host import MCPHost

async def main():
    async with MCPHost(config_path="mcp.json") as host:
        tools = await host.get_tools()
        print(f"Loaded {len(tools)} tools")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Copy example config
cp /Users/jakewatkins/source/trashcode/local-llm/mlx-lab/mcp-host/examples/mcp.json.example mcp.json

# Run it
python main.py
```

## 🆘 Troubleshooting

### "No module named 'mcp_host'"

```bash
# Verify installation
pip list | grep mcp-host

# Reinstall
pip install --force-reinstall /path/to/mcp-host
```

### Import errors

```bash
# Check Python version (requires 3.10+)
python --version

# Verify package contents
pip show -f mcp-host
```

### Updating after changes

```bash
# If installed with -e (editable)
# Changes are immediately available

# If installed normally
cd /path/to/mcp-host
python -m build
pip install --force-reinstall dist/mcp_host-0.1.0-py3-none-any.whl
```
