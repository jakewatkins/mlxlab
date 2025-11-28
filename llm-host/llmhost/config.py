"""
Configuration loading and validation for LLM Host
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigError(Exception):
    """Raised when configuration loading or validation fails"""
    pass


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load and validate config.json
    
    Args:
        config_path: Path to config.json file
        
    Returns:
        Parsed configuration dictionary
        
    Raises:
        ConfigError: If file is missing, invalid JSON, or missing required fields
    """
    if not os.path.exists(config_path):
        raise ConfigError(f"Error: config.json not found in application directory")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Error: Invalid JSON in config.json: {e}")
    
    # Validate required fields
    if "SystemPrompt" not in config:
        raise ConfigError("Error: config.json missing required field 'SystemPrompt'")
    
    if not isinstance(config["SystemPrompt"], str):
        raise ConfigError("Error: config.json field 'SystemPrompt' must be a string")
    
    return config


def load_mcp_config(mcp_path: str = "mcp.json") -> Dict[str, Any]:
    """
    Load and validate mcp.json
    
    Args:
        mcp_path: Path to mcp.json file
        
    Returns:
        Parsed MCP configuration dictionary
        
    Raises:
        ConfigError: If file is missing, invalid JSON, or invalid schema
    """
    if not os.path.exists(mcp_path):
        raise ConfigError(f"Error: mcp.json not found in application directory")
    
    try:
        with open(mcp_path, 'r') as f:
            mcp_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Error: Invalid JSON in mcp.json: {e}")
    
    # Validate schema (mcp-host compatible format)
    if "servers" not in mcp_config:
        raise ConfigError("Error: mcp.json missing required field 'servers'")
    
    if not isinstance(mcp_config["servers"], dict):
        raise ConfigError("Error: mcp.json field 'servers' must be an object")
    
    # Validate each server configuration
    for server_name, server_config in mcp_config["servers"].items():
        if not isinstance(server_config, dict):
            raise ConfigError(f"Error: Server '{server_name}' configuration must be an object")
        
        if "command" not in server_config:
            raise ConfigError(f"Error: Server '{server_name}' missing required field 'command'")
        
        if "args" not in server_config:
            raise ConfigError(f"Error: Server '{server_name}' missing required field 'args'")
        
        if not isinstance(server_config["args"], list):
            raise ConfigError(f"Error: Server '{server_name}' field 'args' must be an array")
    
    return mcp_config
