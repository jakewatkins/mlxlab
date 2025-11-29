#!/usr/bin/env python3
"""
Test script to verify .env file loading in mcp-host.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add mcp-host to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-host"))

from mcp_host.config import ConfigLoader


def test_env_file_loading():
    """Test that .env files are loaded correctly."""
    
    # Create a temporary directory for our test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a .env file
        env_file = tmpdir / ".env"
        env_file.write_text("""
# Test .env file
TEST_API_KEY=secret_key_123
TEST_VALUE="quoted value"
TEST_NUMBER=42

# Comment line
TEST_ANOTHER=value
""")
        
        # Create a test mcp.json
        config_file = tmpdir / "mcp.json"
        config_file.write_text("""
{
  "servers": {
    "test-server": {
      "type": "stdio",
      "command": "test",
      "env": {
        "API_KEY": "${TEST_API_KEY}",
        "VALUE": "${TEST_VALUE}",
        "NUMBER": "${TEST_NUMBER}"
      }
    }
  }
}
""")
        
        # Clear any existing env vars
        for key in ['TEST_API_KEY', 'TEST_VALUE', 'TEST_NUMBER', 'TEST_ANOTHER']:
            os.environ.pop(key, None)
        
        # Load the config
        loader = ConfigLoader()
        config = loader.load(str(config_file))
        
        # Verify environment variables were loaded
        assert os.environ.get('TEST_API_KEY') == 'secret_key_123', \
            f"Expected 'secret_key_123', got {os.environ.get('TEST_API_KEY')}"
        assert os.environ.get('TEST_VALUE') == 'quoted value', \
            f"Expected 'quoted value', got {os.environ.get('TEST_VALUE')}"
        assert os.environ.get('TEST_NUMBER') == '42', \
            f"Expected '42', got {os.environ.get('TEST_NUMBER')}"
        
        # Verify config expansion worked
        server_env = config['servers']['test-server']['env']
        assert server_env['API_KEY'] == 'secret_key_123', \
            f"Config not expanded correctly: {server_env['API_KEY']}"
        assert server_env['VALUE'] == 'quoted value', \
            f"Config not expanded correctly: {server_env['VALUE']}"
        assert server_env['NUMBER'] == '42', \
            f"Config not expanded correctly: {server_env['NUMBER']}"
        
        print("✅ All tests passed!")
        print(f"   - Loaded .env file from {env_file}")
        print(f"   - Expanded environment variables in mcp.json")
        print(f"   - Server env: {server_env}")
        
        # Clean up
        for key in ['TEST_API_KEY', 'TEST_VALUE', 'TEST_NUMBER', 'TEST_ANOTHER']:
            os.environ.pop(key, None)


def test_system_env_precedence():
    """Test that system environment variables take precedence over .env file."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a .env file
        env_file = tmpdir / ".env"
        env_file.write_text("TEST_VAR=from_env_file\n")
        
        # Create a test mcp.json
        config_file = tmpdir / "mcp.json"
        config_file.write_text("""
{
  "servers": {
    "test": {
      "type": "stdio",
      "command": "test",
      "env": {
        "VAR": "${TEST_VAR}"
      }
    }
  }
}
""")
        
        # Set system environment variable
        os.environ['TEST_VAR'] = 'from_system'
        
        # Load config
        loader = ConfigLoader()
        config = loader.load(str(config_file))
        
        # Verify system env took precedence
        assert os.environ.get('TEST_VAR') == 'from_system', \
            "System environment variable should take precedence"
        assert config['servers']['test']['env']['VAR'] == 'from_system', \
            "Config should use system environment variable"
        
        print("✅ System environment precedence test passed!")
        
        # Clean up
        os.environ.pop('TEST_VAR', None)


if __name__ == '__main__':
    print("Testing .env file loading...\n")
    test_env_file_loading()
    print()
    test_system_env_precedence()
    print("\n✅ All tests completed successfully!")
