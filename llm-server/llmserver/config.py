"""
Configuration loading and validation
"""

import json
import os
import sys
from typing import Dict, Any
from pathlib import Path


class ConfigError(Exception):
    """Raised when configuration is invalid"""
    pass


class Config:
    """Configuration management"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Load and validate configuration
        
        Args:
            config_path: Path to config.json file
            
        Raises:
            ConfigError: If configuration is invalid or missing
        """
        self.config_path = config_path
        self.data: Dict[str, Any] = {}
        self._load()
        self._validate()
        self._substitute_secrets()
    
    def _load(self):
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            print(f"Error: Configuration file '{self.config_path}' not found")
            sys.exit(1)
        
        try:
            with open(self.config_path, 'r') as f:
                self.data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Could not read configuration file: {e}")
            sys.exit(1)
    
    def _validate(self):
        """Validate required configuration fields"""
        required_fields = [
            "model_name",
            "listening_port",
            "system_prompt",
            "temperature",
            "top_p",
            "min_p",
            "min_tokens_to_keep",
            "log_level",
            "log_filename"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in self.data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"Error: Missing required configuration fields: {', '.join(missing_fields)}")
            sys.exit(1)
        
        # Validate listening_port is a number
        if not isinstance(self.data.get("listening_port"), int):
            print("Error: 'listening_port' must be an integer")
            sys.exit(1)
        
        # Validate log_level
        valid_log_levels = ["trace", "warning", "error"]
        if self.data.get("log_level") not in valid_log_levels:
            print(f"Error: 'log_level' must be one of {valid_log_levels}")
            sys.exit(1)
        
        # Servers can be empty but must exist
        if "servers" not in self.data:
            self.data["servers"] = {}
    
    def _substitute_secrets(self):
        """Substitute environment variables in configuration"""
        def substitute_value(value: Any) -> Any:
            """Recursively substitute environment variables"""
            if isinstance(value, str):
                # Check for ${VAR_NAME} pattern
                if value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    
                    # First check environment variables
                    env_value = os.environ.get(var_name)
                    if env_value is not None:
                        return env_value
                    
                    # Then check .env file
                    env_file = Path.cwd() / ".env"
                    if env_file.exists():
                        try:
                            with open(env_file, 'r') as f:
                                for line in f:
                                    line = line.strip()
                                    if not line or line.startswith('#'):
                                        continue
                                    if '=' in line:
                                        key, val = line.split('=', 1)
                                        if key.strip() == var_name:
                                            return val.strip().strip('"').strip("'")
                        except Exception as e:
                            print(f"Error: Could not read .env file: {e}")
                            sys.exit(1)
                    
                    # Not found
                    print(f"Error: Environment variable '{var_name}' not found in environment or .env file")
                    sys.exit(1)
                
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(v) for v in value]
            else:
                return value
        
        self.data = substitute_value(self.data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.data.get(key, default)
    
    @property
    def model_name(self) -> str:
        return self.data["model_name"]
    
    @property
    def listening_port(self) -> int:
        return self.data["listening_port"]
    
    @property
    def servers(self) -> Dict[str, Any]:
        return self.data.get("servers", {})
    
    @property
    def system_prompt(self) -> str:
        return self.data["system_prompt"]
    
    @property
    def temperature(self) -> float:
        return self.data["temperature"]
    
    @property
    def top_p(self) -> float:
        return self.data["top_p"]
    
    @property
    def min_p(self) -> float:
        return self.data["min_p"]
    
    @property
    def min_tokens_to_keep(self) -> int:
        return self.data["min_tokens_to_keep"]
    
    @property
    def log_level(self) -> str:
        return self.data["log_level"]
    
    @property
    def log_filename(self) -> str:
        return self.data["log_filename"]
