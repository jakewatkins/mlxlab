"""
Configuration management for MCP Host.

Handles loading, validating, and processing the mcp.json configuration file.
"""

import json
import os
from typing import Any, Dict, List, Set
from .exceptions import ConfigurationError, ValidationError
from .types import TransportType


class ConfigLoader:
    """Loads and validates MCP server configuration."""
    
    # JSON Schema for mcp.json validation
    SCHEMA = {
        "type": "object",
        "properties": {
            "servers": {
                "type": "object",
                "patternProperties": {
                    ".*": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["stdio", "sse", "websocket"]
                            },
                            "command": {
                                "type": "string"
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "env": {
                                "type": "object"
                            },
                            "timeout": {
                                "type": "number"
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["type", "command"]
                    }
                }
            }
        },
        "required": ["servers"]
    }
    
    def __init__(self):
        """Initialize the configuration loader."""
        self._config: Dict[str, Any] = {}
        self._config_path: str = ""
    
    def _load_env_file(self, env_path: str | None = None) -> None:
        """
        Load environment variables from a .env file.
        
        Args:
            env_path: Path to .env file. If None, looks for .env in config directory.
        """
        if env_path is None:
            # Look for .env in same directory as config file
            config_dir = os.path.dirname(self._config_path) if self._config_path else "."
            env_path = os.path.join(config_dir, ".env")
        
        if not os.path.exists(env_path):
            # .env file is optional
            return
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value and value[0] in ('"', "'") and value[0] == value[-1]:
                            value = value[1:-1]
                        
                        # Only set if not already in environment
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            # Log warning but don't fail - .env is optional
            import warnings
            warnings.warn(f"Failed to load .env file: {e}")
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to mcp.json file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded or is invalid
        """
        self._config_path = config_path
        
        # Check if file exists
        if not os.path.exists(config_path):
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                config_path=config_path
            )
        
        # Load JSON
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file: {e}",
                config_path=config_path
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to read configuration file: {e}",
                config_path=config_path
            )
        
        # Validate schema
        self.validate(self._config)
        
        # Check for duplicate server names (already done by dict, but explicit check)
        self._check_duplicates()
        
        # Load .env file if present
        self._load_env_file()
        
        # Expand environment variables
        self._config = self.expand_env_vars(self._config)
        
        # Validate dependencies
        self._validate_dependencies()
        
        return self._config
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Basic schema validation (would use jsonschema in production)
        if not isinstance(config, dict):
            raise ValidationError("Configuration must be a dictionary")
        
        if "servers" not in config:
            raise ValidationError("Configuration must have 'servers' key")
        
        servers = config["servers"]
        if not isinstance(servers, dict):
            raise ValidationError("'servers' must be a dictionary")
        
        # Validate each server
        for server_name, server_config in servers.items():
            self._validate_server(server_name, server_config)
        
        return True
    
    def _validate_server(self, name: str, config: Dict[str, Any]) -> None:
        """Validate a single server configuration."""
        if not isinstance(config, dict):
            raise ValidationError(
                f"Server '{name}' configuration must be a dictionary",
                validation_type="server_config",
                details={"server": name}
            )
        
        # Check required fields
        if "type" not in config:
            raise ValidationError(
                f"Server '{name}' missing required field 'type'",
                validation_type="missing_field",
                details={"server": name, "field": "type"}
            )
        
        if "command" not in config:
            raise ValidationError(
                f"Server '{name}' missing required field 'command'",
                validation_type="missing_field",
                details={"server": name, "field": "command"}
            )
        
        # Validate transport type
        transport_type = config["type"]
        if transport_type not in ["stdio", "sse", "websocket"]:
            raise ValidationError(
                f"Server '{name}' has invalid transport type '{transport_type}'",
                validation_type="invalid_value",
                details={"server": name, "field": "type", "value": transport_type}
            )
        
        # Validate args if present
        if "args" in config and not isinstance(config["args"], list):
            raise ValidationError(
                f"Server '{name}' 'args' must be an array",
                validation_type="invalid_type",
                details={"server": name, "field": "args"}
            )
        
        # Validate env if present
        if "env" in config and not isinstance(config["env"], dict):
            raise ValidationError(
                f"Server '{name}' 'env' must be an object",
                validation_type="invalid_type",
                details={"server": name, "field": "env"}
            )
        
        # Validate timeout if present
        if "timeout" in config and not isinstance(config["timeout"], (int, float)):
            raise ValidationError(
                f"Server '{name}' 'timeout' must be a number",
                validation_type="invalid_type",
                details={"server": name, "field": "timeout"}
            )
        
        # Validate dependencies if present
        if "dependencies" in config:
            if not isinstance(config["dependencies"], list):
                raise ValidationError(
                    f"Server '{name}' 'dependencies' must be an array",
                    validation_type="invalid_type",
                    details={"server": name, "field": "dependencies"}
                )
    
    def expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand environment variables in configuration.
        
        Replaces ${VAR_NAME} with the value of the environment variable.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with expanded variables
        """
        import copy
        import re
        
        config = copy.deepcopy(config)
        env_var_pattern = re.compile(r'\$\{([^}]+)\}')
        
        def expand_value(value: Any) -> Any:
            """Recursively expand environment variables in values."""
            if isinstance(value, str):
                # Find all ${VAR} patterns
                matches = env_var_pattern.findall(value)
                for var_name in matches:
                    env_value = os.environ.get(var_name, '')
                    if not env_value:
                        # Variable not set - could warn or error
                        pass
                    value = value.replace(f'${{{var_name}}}', env_value)
                return value
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value
        
        return expand_value(config)
    
    def _check_duplicates(self) -> None:
        """Check for duplicate server names."""
        servers = self._config.get("servers", {})
        server_names = list(servers.keys())
        
        # Dict keys are already unique, but check for case-insensitive duplicates
        seen: Set[str] = set()
        for name in server_names:
            name_lower = name.lower()
            if name_lower in seen:
                raise ConfigurationError(
                    f"Duplicate server name '{name}' (case-insensitive)",
                    config_path=self._config_path,
                    field=f"servers.{name}"
                )
            seen.add(name_lower)
    
    def _validate_dependencies(self) -> None:
        """
        Validate server dependencies.
        
        Checks that:
        1. All dependency references exist
        2. No circular dependencies
        """
        servers = self._config.get("servers", {})
        
        # Build dependency graph
        for server_name, server_config in servers.items():
            dependencies = server_config.get("dependencies", [])
            
            for dep in dependencies:
                # Check dependency exists
                if dep not in servers:
                    raise ConfigurationError(
                        f"Server '{server_name}' depends on non-existent server '{dep}'",
                        config_path=self._config_path,
                        field=f"servers.{server_name}.dependencies"
                    )
        
        # Check for circular dependencies
        self._check_circular_dependencies(servers)
    
    def _check_circular_dependencies(self, servers: Dict[str, Any]) -> None:
        """Check for circular dependencies using DFS."""
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        
        def dfs(server_name: str) -> bool:
            """DFS to detect cycles."""
            visited.add(server_name)
            recursion_stack.add(server_name)
            
            dependencies = servers[server_name].get("dependencies", [])
            for dep in dependencies:
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in recursion_stack:
                    raise ConfigurationError(
                        f"Circular dependency detected: {server_name} -> {dep}",
                        config_path=self._config_path
                    )
            
            recursion_stack.remove(server_name)
            return False
        
        for server_name in servers:
            if server_name not in visited:
                dfs(server_name)
    
    def get_startup_order(self) -> List[str]:
        """
        Get servers in dependency order (topological sort).
        
        Returns:
            List of server names in order to start them
        """
        servers = self._config.get("servers", {})
        visited: Set[str] = set()
        order: List[str] = []
        
        def dfs(server_name: str) -> None:
            """DFS for topological sort."""
            if server_name in visited:
                return
            
            visited.add(server_name)
            
            dependencies = servers[server_name].get("dependencies", [])
            for dep in dependencies:
                dfs(dep)
            
            order.append(server_name)
        
        for server_name in servers:
            dfs(server_name)
        
        return order
    
    @staticmethod
    def get_json_schema() -> Dict[str, Any]:
        """Get the JSON schema for validation."""
        return ConfigLoader.SCHEMA
