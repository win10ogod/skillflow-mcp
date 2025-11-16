"""Tool naming utilities for upstream tool proxying.

Handles generation of proxy tool names with length constraints.
"""

import hashlib
import re
from typing import Optional


class ToolNamingStrategy:
    """Strategy for generating proxy tool names.

    Different MCP clients have different constraints:
    - Cursor: 60 character limit
    - Claude Desktop: No known limit
    - Fount: No known limit

    We optimize for the most restrictive (60 chars).
    """

    # Naming format versions
    FORMAT_LEGACY = "legacy"  # upstream__server_id__tool_name (may exceed 60 chars)
    FORMAT_COMPACT = "compact"  # up_server_id_tool_name (shorter prefix, single _)
    FORMAT_HASH = "hash"  # up_<hash>_tool_name (hash server_id if needed)

    # Length constraints
    MAX_TOTAL_LENGTH = 60
    PREFIX_LEGACY = "upstream__"
    PREFIX_COMPACT = "up_"
    SEPARATOR_LEGACY = "__"
    SEPARATOR_COMPACT = "_"

    def __init__(self, format: str = FORMAT_COMPACT):
        """Initialize naming strategy.

        Args:
            format: Naming format (legacy, compact, or hash)
        """
        self.format = format

    def generate_proxy_tool_name(
        self,
        server_id: str,
        tool_name: str,
        max_length: Optional[int] = None
    ) -> str:
        """Generate proxy tool name with length constraints.

        Args:
            server_id: Upstream server ID
            tool_name: Original tool name
            max_length: Maximum total length (default: 60)

        Returns:
            Proxy tool name

        Examples:
            >>> strategy = ToolNamingStrategy(FORMAT_COMPACT)
            >>> strategy.generate_proxy_tool_name("windows-driver-input", "Move_Tool")
            'up_windows-driver-input_Move_Tool'  # 34 chars

            >>> strategy.generate_proxy_tool_name("very-long-server-name", "Very_Long_Tool_Name")
            'up_3a7b_Very_Long_Tool_Name'  # Uses hash for server
        """
        max_length = max_length or self.MAX_TOTAL_LENGTH

        if self.format == self.FORMAT_LEGACY:
            return self._generate_legacy(server_id, tool_name)
        elif self.format == self.FORMAT_HASH:
            return self._generate_hash(server_id, tool_name, max_length)
        else:  # FORMAT_COMPACT (default)
            return self._generate_compact(server_id, tool_name, max_length)

    def _generate_legacy(self, server_id: str, tool_name: str) -> str:
        """Generate legacy format (may exceed 60 chars).

        Format: upstream__<server_id>__<tool_name>
        """
        return f"{self.PREFIX_LEGACY}{server_id}{self.SEPARATOR_LEGACY}{tool_name}"

    def _generate_compact(
        self,
        server_id: str,
        tool_name: str,
        max_length: int
    ) -> str:
        """Generate compact format with automatic fallback to hash if needed.

        Format: up_<server_id>_<tool_name>
        Falls back to hash if exceeds max_length.
        """
        # Try compact format first
        compact_name = f"{self.PREFIX_COMPACT}{server_id}{self.SEPARATOR_COMPACT}{tool_name}"

        if len(compact_name) <= max_length:
            return compact_name

        # If too long, use hash format
        return self._generate_hash(server_id, tool_name, max_length)

    def _generate_hash(
        self,
        server_id: str,
        tool_name: str,
        max_length: int
    ) -> str:
        """Generate hash format for long names.

        Format: up_<hash>_<tool_name>
        Where <hash> is first 4-8 chars of SHA256 hash of server_id.
        If tool_name itself is too long, it will be truncated.
        """
        # Calculate available space for hash
        # Format: up_ + hash + _ + tool_name
        # Minimum: up_ (3) + hash (4) + _ (1) = 8 chars overhead
        prefix_len = len(self.PREFIX_COMPACT)
        separator_len = len(self.SEPARATOR_COMPACT)
        min_overhead = prefix_len + separator_len + 4  # Minimum hash length is 4

        # Check if tool_name needs truncation
        max_tool_name_len = max_length - min_overhead
        truncated_tool_name = tool_name
        if len(tool_name) > max_tool_name_len:
            # Truncate tool name and add suffix to indicate truncation
            truncated_tool_name = tool_name[:max_tool_name_len - 2] + ".."
            import warnings
            warnings.warn(
                f"Tool name '{tool_name}' truncated to '{truncated_tool_name}' "
                f"to fit within {max_length} char limit"
            )

        # Calculate available space for hash
        available_for_hash = max_length - prefix_len - separator_len - len(truncated_tool_name)

        # Generate hash of server_id
        hash_obj = hashlib.sha256(server_id.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()

        # Use 4-8 chars of hash depending on available space
        if available_for_hash >= 8:
            hash_str = hash_hex[:8]
        elif available_for_hash >= 6:
            hash_str = hash_hex[:6]
        else:
            hash_str = hash_hex[:4]

        result = f"{self.PREFIX_COMPACT}{hash_str}{self.SEPARATOR_COMPACT}{truncated_tool_name}"

        # Final safety check
        if len(result) > max_length:
            # Should not happen, but just in case
            result = result[:max_length]

        return result

    def parse_proxy_tool_name(self, tool_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse proxy tool name to extract components.

        Args:
            tool_name: Proxy tool name

        Returns:
            Tuple of (server_id_or_hash, actual_tool_name, format_type)
            Returns (None, None, None) if not a proxy tool name

        Examples:
            >>> strategy = ToolNamingStrategy()
            >>> strategy.parse_proxy_tool_name("up_windows-driver-input_Move_Tool")
            ('windows-driver-input', 'Move_Tool', 'compact')

            >>> strategy.parse_proxy_tool_name("up_3a7b_Move_Tool")
            ('3a7b', 'Move_Tool', 'hash')
        """
        # Try compact/hash format
        if tool_name.startswith(self.PREFIX_COMPACT):
            parts = tool_name[len(self.PREFIX_COMPACT):].split(self.SEPARATOR_COMPACT, 1)
            if len(parts) == 2:
                server_part, tool_part = parts
                # Determine if it's a hash (4-8 hex chars) or full server_id
                if re.match(r'^[0-9a-f]{4,8}$', server_part):
                    format_type = self.FORMAT_HASH
                else:
                    format_type = self.FORMAT_COMPACT
                return server_part, tool_part, format_type

        # Try legacy format
        if tool_name.startswith(self.PREFIX_LEGACY):
            parts = tool_name[len(self.PREFIX_LEGACY):].split(self.SEPARATOR_LEGACY, 1)
            if len(parts) == 2:
                return parts[0], parts[1], self.FORMAT_LEGACY

        return None, None, None

    def is_proxy_tool(self, tool_name: str) -> bool:
        """Check if tool name is a proxy tool.

        Args:
            tool_name: Tool name to check

        Returns:
            True if proxy tool, False otherwise
        """
        return (
            tool_name.startswith(self.PREFIX_COMPACT) or
            tool_name.startswith(self.PREFIX_LEGACY)
        )


# Singleton instance with default strategy
default_naming_strategy = ToolNamingStrategy(ToolNamingStrategy.FORMAT_COMPACT)


def generate_proxy_tool_name(
    server_id: str,
    tool_name: str,
    max_length: Optional[int] = None
) -> str:
    """Generate proxy tool name using default strategy.

    Args:
        server_id: Upstream server ID
        tool_name: Original tool name
        max_length: Maximum total length (default: 60, but consider client prefixes)

    Returns:
        Proxy tool name

    Note:
        Some MCP clients add prefixes to tool names. For example, Fount adds
        'mcp_<server_name>_' (13 chars for 'mcp_skillflow_'). In such cases,
        pass max_length=47 to ensure the total doesn't exceed 60 chars.
    """
    return default_naming_strategy.generate_proxy_tool_name(server_id, tool_name, max_length)


def parse_proxy_tool_name(tool_name: str) -> tuple[Optional[str], Optional[str]]:
    """Parse proxy tool name using default strategy.

    Args:
        tool_name: Proxy tool name

    Returns:
        Tuple of (server_id_or_hash, actual_tool_name)
        Returns (None, None) if not a proxy tool
    """
    server_part, tool_part, _ = default_naming_strategy.parse_proxy_tool_name(tool_name)
    return server_part, tool_part


def is_proxy_tool(tool_name: str) -> bool:
    """Check if tool name is a proxy tool.

    Args:
        tool_name: Tool name to check

    Returns:
        True if proxy tool, False otherwise
    """
    return default_naming_strategy.is_proxy_tool(tool_name)
