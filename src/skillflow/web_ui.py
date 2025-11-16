#!/usr/bin/env python3
"""
Standalone web server launcher for SkillFlow MCP.

This script starts the web UI independently from the MCP server,
providing a browser-based interface for managing skills, monitoring
executions, and debugging.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from skillflow.storage import StorageLayer
from skillflow.skills import SkillManager
from skillflow.recording import RecordingManager
from skillflow.engine import ExecutionEngine
from skillflow.audit import AuditLogger
from skillflow.metrics import MetricsCollector
from skillflow.mcp_clients import MCPClientManager


async def dummy_tool_executor(server_id, tool_name, args):
    """Dummy tool executor for web-only mode."""
    raise NotImplementedError(
        "Tool execution not available in web-only mode. "
        "Start the full MCP server for skill execution."
    )


async def main():
    """Start the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="SkillFlow Web UI")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory (default: data)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)"
    )
    args = parser.parse_args()

    print(f"Starting SkillFlow Web UI...")
    print(f"Data directory: {args.data_dir}")
    print(f"Server: http://{args.host}:{args.port}")

    # Initialize components
    storage = StorageLayer(args.data_dir)
    await storage.initialize()

    skill_manager = SkillManager(storage)
    recording_manager = RecordingManager(storage)
    audit_logger = AuditLogger(storage)
    metrics_collector = MetricsCollector(storage)

    # Create a minimal execution engine (read-only for web UI)
    execution_engine = ExecutionEngine(
        storage=storage,
        tool_executor=dummy_tool_executor,
        skill_manager=skill_manager
    )

    # Start metrics collection
    await metrics_collector.start()

    # Import and start web server
    try:
        from skillflow.web_server import WebServer

        web_server = WebServer(
            storage=storage,
            skill_manager=skill_manager,
            recording_manager=recording_manager,
            execution_engine=execution_engine,
            audit_logger=audit_logger,
            metrics_collector=metrics_collector,
            host=args.host,
            port=args.port,
        )

        print("\n✓ SkillFlow Web UI is running!")
        print(f"\n  Dashboard:    http://{args.host}:{args.port}/")
        print(f"  Skills:       http://{args.host}:{args.port}/skills")
        print(f"  DAG Editor:   http://{args.host}:{args.port}/editor")
        print(f"  Monitoring:   http://{args.host}:{args.port}/monitoring")
        print(f"  Debug Tools:  http://{args.host}:{args.port}/debug")
        print(f"  Skill Builder: http://{args.host}:{args.port}/builder")
        print("\nPress Ctrl+C to stop\n")

        await web_server.start()

    except ImportError:
        print("\n❌ Error: Web UI dependencies not installed!")
        print("\nInstall with: uv sync --extra web")
        print("Or install all features: uv sync --extra full")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        await metrics_collector.stop()
    except Exception as e:
        print(f"\n❌ Error starting web server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
