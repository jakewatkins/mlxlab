"""
Configuration loading and validation for LLM CLI
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
    Load and validate config.json with defaults
    
    Args:
        config_path: Path to config.json file
        
    Returns:
        Parsed configuration dictionary with defaults applied
    """
    # Default configuration
    config = {
        "SystemPrompt": "You are a helpful AI assistant with access to various tools. When you need to perform an action or retrieve information, use the available tools by generating tool calls in the specified format. Always provide clear, helpful responses.",
        "temperature": 0.7,
        "top_p": 1.0,
        "min_p": 0.0,
        "min_tokens_to_keep": 1
    }
    
    # If config file exists, load and merge with defaults
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config.json: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to read config.json: {e}")
    
    # Validate types
    if not isinstance(config["SystemPrompt"], str):
        raise ConfigError("config.json field 'SystemPrompt' must be a string")
    
    return config


def load_mcp_config(mcp_path: str = "mcp.json") -> Dict[str, Any]:
    """
    Load and validate mcp.json
    
    Args:
        mcp_path: Path to mcp.json file
        
    Returns:
        Parsed MCP configuration dictionary
        
    Raises:
        ConfigError: If file is invalid or has schema errors
    """
    if not os.path.exists(mcp_path):
        # Return empty config if file doesn't exist (tools will be disabled)
        return {"servers": {}}
    
    try:
        with open(mcp_path, 'r') as f:
            mcp_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in mcp.json: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read mcp.json: {e}")
    
    # Validate schema (mcp-host compatible format)
    if "servers" not in mcp_config:
        raise ConfigError("mcp.json missing required field 'servers'")
    
    if not isinstance(mcp_config["servers"], dict):
        raise ConfigError("mcp.json field 'servers' must be an object")
    
    return mcp_config
