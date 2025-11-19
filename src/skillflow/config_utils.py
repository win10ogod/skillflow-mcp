"""Configuration utilities for MCP server management.

This module provides tools for importing, exporting, validating and
managing MCP server configurations compatible with Claude Code.
"""

import json
from pathlib import Path
from typing import Any, Optional
import logging

from .schemas import ServerConfig, ServerRegistry, TransportType

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates MCP server configurations."""

    @staticmethod
    def validate_server_config(config: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a single server configuration.

        Args:
            config: Server configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["server_id", "name", "transport", "config"]

        # Check required fields
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        # Validate transport
        if config["transport"] not in [t.value for t in TransportType]:
            return False, f"Invalid transport: {config['transport']}"

        # Validate config structure
        if not isinstance(config["config"], dict):
            return False, "config must be a dictionary"

        # For STDIO transport, validate command and args
        if config["transport"] == "stdio":
            if "command" not in config["config"]:
                return False, "STDIO transport requires 'command' in config"

        return True, None

    @staticmethod
    def validate_registry(registry: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a complete server registry.

        Args:
            registry: Registry dictionary with 'servers' key

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check top-level structure
        if "servers" not in registry:
            return False, ["Missing 'servers' key in registry"]

        if not isinstance(registry["servers"], dict):
            return False, ["'servers' must be a dictionary"]

        # Validate each server
        for server_id, server_config in registry["servers"].items():
            # Check if server_id matches the key
            if "server_id" in server_config and server_config["server_id"] != server_id:
                errors.append(
                    f"Server ID mismatch: key is '{server_id}' but "
                    f"server_id field is '{server_config['server_id']}'"
                )

            # Validate server config
            is_valid, error = ConfigValidator.validate_server_config(server_config)
            if not is_valid:
                errors.append(f"Server '{server_id}': {error}")

        return len(errors) == 0, errors


class ConfigConverter:
    """Converts between different configuration formats."""

    @staticmethod
    def _normalize_server_config(server_id: str, server_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize a server configuration by filling in missing fields.

        Args:
            server_id: The server identifier
            server_data: Raw server configuration data

        Returns:
            Normalized server configuration
        """
        normalized = dict(server_data)

        # Ensure server_id is set
        if "server_id" not in normalized:
            normalized["server_id"] = server_id

        # Ensure name is set (default to server_id)
        if "name" not in normalized:
            normalized["name"] = server_id.replace("_", " ").replace("-", " ").title()

        # Ensure transport is set (default to stdio)
        if "transport" not in normalized:
            normalized["transport"] = "stdio"

        # Normalize config structure
        # If command/args/env are at root level, move them into config
        if "config" not in normalized:
            config = {}

            # Move command, args, env into config if they exist at root
            if "command" in normalized:
                config["command"] = normalized.pop("command")
            if "args" in normalized:
                config["args"] = normalized.pop("args")
            if "env" in normalized:
                config["env"] = normalized.pop("env")

            normalized["config"] = config

        # Ensure enabled is set (default to True)
        if "enabled" not in normalized:
            normalized["enabled"] = True

        # Ensure metadata is set (default to empty dict)
        if "metadata" not in normalized:
            normalized["metadata"] = {}

        return normalized

    @staticmethod
    def from_claude_code(claude_code_config: dict[str, Any]) -> ServerRegistry:
        """Convert Claude Code configuration to ServerRegistry.

        Supports both standard Claude Code format with 'mcpServers' key
        and SkillFlow internal format with 'servers' key.

        Automatically normalizes incomplete configurations by:
        - Adding missing server_id, name, transport fields
        - Moving command/args/env from root to config object
        - Setting default values for enabled and metadata

        Args:
            claude_code_config: Configuration dict with 'mcpServers' or 'servers' key

        Returns:
            ServerRegistry instance

        Raises:
            ValueError: If configuration is invalid after normalization
        """
        # Handle both 'mcpServers' (standard Claude Code) and 'servers' (internal) keys
        if "mcpServers" in claude_code_config:
            # Convert mcpServers to servers for processing
            servers_dict = claude_code_config["mcpServers"]
        elif "servers" in claude_code_config:
            servers_dict = claude_code_config["servers"]
        else:
            raise ValueError("Configuration must contain either 'mcpServers' or 'servers' key")

        # Normalize each server configuration
        normalized_servers = {}
        skipped_servers = []
        for server_id, server_data in servers_dict.items():
            try:
                normalized = ConfigConverter._normalize_server_config(
                    server_id, server_data
                )
                normalized_servers[server_id] = normalized
                logger.debug(f"Normalized server '{server_id}': {normalized.get('name', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to normalize server '{server_id}': {e}")
                skipped_servers.append(server_id)
                # Skip this server but continue processing others
                continue

        if skipped_servers:
            logger.warning(f"Skipped {len(skipped_servers)} invalid servers: {', '.join(skipped_servers)}")

        normalized_config = {"servers": normalized_servers}

        # Validate normalized config
        is_valid, errors = ConfigValidator.validate_registry(normalized_config)
        if not is_valid:
            logger.error(f"Validation failed after normalization: {'; '.join(errors)}")
            raise ValueError(f"Invalid configuration after normalization: {'; '.join(errors)}")

        # Convert to ServerRegistry
        servers = {}
        failed_servers = []
        for server_id, server_data in normalized_servers.items():
            try:
                servers[server_id] = ServerConfig(**server_data)
                logger.debug(f"Created ServerConfig for '{server_id}': transport={server_data.get('transport')}")
            except Exception as e:
                logger.error(f"Failed to create ServerConfig for '{server_id}': {e}", exc_info=True)
                failed_servers.append(server_id)
                # Skip invalid servers
                continue

        if failed_servers:
            logger.warning(f"Failed to create {len(failed_servers)} server configs: {', '.join(failed_servers)}")

        if not servers:
            raise ValueError("No valid servers found in configuration")

        logger.info(f"Successfully created registry with {len(servers)} servers: {', '.join(servers.keys())}")
        return ServerRegistry(servers=servers)

    @staticmethod
    def to_claude_code(registry: ServerRegistry) -> dict[str, Any]:
        """Convert ServerRegistry to Claude Code format.

        Args:
            registry: ServerRegistry instance

        Returns:
            Configuration dictionary compatible with Claude Code
        """
        return {
            "servers": {
                server_id: config.model_dump(mode="json")
                for server_id, config in registry.servers.items()
            }
        }

    @staticmethod
    def merge_registries(
        base: ServerRegistry,
        overlay: ServerRegistry,
        overwrite: bool = False
    ) -> ServerRegistry:
        """Merge two server registries.

        Args:
            base: Base registry
            overlay: Overlay registry (higher priority)
            overwrite: If True, overlay servers overwrite base servers

        Returns:
            Merged ServerRegistry
        """
        merged_servers = dict(base.servers)

        for server_id, server_config in overlay.servers.items():
            if server_id in merged_servers and not overwrite:
                logger.warning(
                    f"Server '{server_id}' exists in both registries, "
                    f"keeping base version (use overwrite=True to replace)"
                )
            else:
                merged_servers[server_id] = server_config

        return ServerRegistry(servers=merged_servers)


class ConfigImporter:
    """Imports configurations from various sources."""

    @staticmethod
    async def from_file(file_path: Path) -> ServerRegistry:
        """Import configuration from a JSON file.

        Args:
            file_path: Path to JSON configuration file

        Returns:
            ServerRegistry instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not valid JSON or configuration is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        return ConfigConverter.from_claude_code(data)

    @staticmethod
    async def from_dict(config_dict: dict[str, Any]) -> ServerRegistry:
        """Import configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            ServerRegistry instance

        Raises:
            ValueError: If configuration is invalid
        """
        return ConfigConverter.from_claude_code(config_dict)


class ConfigExporter:
    """Exports configurations to various formats."""

    @staticmethod
    async def to_file(registry: ServerRegistry, file_path: Path, indent: int = 2):
        """Export configuration to a JSON file.

        Args:
            registry: ServerRegistry to export
            file_path: Path to output file
            indent: JSON indentation (default: 2)
        """
        config_dict = ConfigConverter.to_claude_code(registry)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=indent, ensure_ascii=False)

    @staticmethod
    def to_json_string(registry: ServerRegistry, indent: int = 2) -> str:
        """Export configuration to a JSON string.

        Args:
            registry: ServerRegistry to export
            indent: JSON indentation (default: 2)

        Returns:
            JSON string
        """
        config_dict = ConfigConverter.to_claude_code(registry)
        return json.dumps(config_dict, indent=indent, ensure_ascii=False)


def validate_config_file(file_path: Path) -> tuple[bool, list[str]]:
    """Validate a configuration file.

    Args:
        file_path: Path to configuration file

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    return ConfigValidator.validate_registry(data)


def print_validation_report(file_path: Path):
    """Print a validation report for a configuration file.

    Args:
        file_path: Path to configuration file
    """
    is_valid, errors = validate_config_file(file_path)

    print(f"\n{'='*60}")
    print(f"Configuration Validation Report")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Status: {'✅ VALID' if is_valid else '❌ INVALID'}")

    if not is_valid:
        print(f"\nErrors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print(f"\n✅ Configuration is valid and compatible with Claude Code!")

    print(f"{'='*60}\n")
