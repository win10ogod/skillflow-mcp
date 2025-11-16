#!/usr/bin/env python3
"""
Quick start script for SkillFlow Web UI.
Can be run directly for testing: python run_web.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.storage import StorageLayer
from skillflow.skills import SkillManager
from skillflow.recording import RecordingManager
from skillflow.engine import ExecutionEngine
from skillflow.audit import AuditLogger
from skillflow.metrics import MetricsCollector


async def dummy_tool_executor(server_id, tool_name, args):
    """Dummy tool executor for web-only mode."""
    raise NotImplementedError(
        "Tool execution not available in standalone mode. "
        "Use the full MCP server for skill execution."
    )


async def main():
    """Start the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="SkillFlow Web UI - Quick Start")
    parser.add_argument("--data-dir", type=str, default="data", help="Data directory")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    args = parser.parse_args()

    print("=" * 60)
    print("SkillFlow MCP - Web UI")
    print("=" * 60)
    print(f"Data directory: {args.data_dir}")
    print(f"Server: http://{args.host}:{args.port}")
    print("=" * 60)

    # Initialize components
    storage = StorageLayer(args.data_dir)
    await storage.initialize()

    skill_manager = SkillManager(storage)
    recording_manager = RecordingManager(storage)
    audit_logger = AuditLogger(storage)
    metrics_collector = MetricsCollector(storage)

    # Create execution engine (minimal for web UI)
    execution_engine = ExecutionEngine(
        storage=storage,
        tool_executor=dummy_tool_executor,
        skill_manager=skill_manager
    )

    # Start metrics collection
    await metrics_collector.start()

    print("\nInitializing web server...")

    # Check for web dependencies
    try:
        from skillflow.web_server import WebServer
    except ImportError as e:
        print("\n" + "=" * 60)
        print("ERROR: Web UI dependencies not installed!")
        print("=" * 60)
        print("\nInstall with one of these commands:")
        print("  uv sync --extra web")
        print("  uv sync --extra full")
        print("\nThen run again:")
        print("  uv run python run_web.py")
        print("=" * 60)
        sys.exit(1)

    # Create and start web server
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

    print("\n" + "=" * 60)
    print("✓ SkillFlow Web UI is running!")
    print("=" * 60)
    print(f"\n  🏠 Dashboard:      http://{args.host}:{args.port}/")
    print(f"  📋 Skills:         http://{args.host}:{args.port}/skills")
    print(f"  🎨 DAG Editor:     http://{args.host}:{args.port}/editor")
    print(f"  📊 Monitoring:     http://{args.host}:{args.port}/monitoring")
    print(f"  🔍 Debug Tools:    http://{args.host}:{args.port}/debug")
    print(f"  🏗️  Skill Builder:  http://{args.host}:{args.port}/builder")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    try:
        await web_server.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        await metrics_collector.stop()
        print("Goodbye! 👋")
    except Exception as e:
        print(f"\n❌ Error starting web server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
