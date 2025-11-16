"""
Web server for SkillFlow MCP - provides web UI and REST API.

Serves the control panel, DAG editor, monitoring dashboard,
debugging tools, and interactive skill builder.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audit import AuditEventType, AuditLogger, AuditEventSeverity
from .metrics import MetricsCollector
from .skills import SkillManager
from .storage import StorageLayer
from .recording import RecordingManager
from .engine import ExecutionEngine


class WebServer:
    """Web server for SkillFlow UI and API."""

    def __init__(
        self,
        storage: StorageLayer,
        skill_manager: SkillManager,
        recording_manager: RecordingManager,
        execution_engine: ExecutionEngine,
        audit_logger: AuditLogger,
        metrics_collector: MetricsCollector,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """
        Initialize web server.

        Args:
            storage: Storage layer instance
            skill_manager: Skill manager instance
            recording_manager: Recording manager instance
            execution_engine: Execution engine instance
            audit_logger: Audit logger instance
            metrics_collector: Metrics collector instance
            host: Host to bind to
            port: Port to bind to
        """
        self.storage = storage
        self.skill_manager = skill_manager
        self.recording_manager = recording_manager
        self.engine = execution_engine
        self.audit = audit_logger
        self.metrics = metrics_collector
        self.host = host
        self.port = port

        # Create FastAPI app
        self.app = FastAPI(
            title="SkillFlow MCP Server",
            description="Web UI and REST API for SkillFlow",
            version="0.2.0"
        )

        # WebSocket connections for real-time updates
        self.active_connections: list[WebSocket] = []

        # Setup routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        # Serve static files (CSS, JS, images)
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # ======================
        # HTML Pages
        # ======================

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            """Serve the main dashboard."""
            return await self._render_template("index.html")

        @self.app.get("/skills", response_class=HTMLResponse)
        async def skills_page():
            """Serve the skills management page."""
            return await self._render_template("skills.html")

        @self.app.get("/editor", response_class=HTMLResponse)
        async def editor_page():
            """Serve the visual DAG editor."""
            return await self._render_template("editor.html")

        @self.app.get("/monitoring", response_class=HTMLResponse)
        async def monitoring_page():
            """Serve the execution monitoring dashboard."""
            return await self._render_template("monitoring.html")

        @self.app.get("/debug", response_class=HTMLResponse)
        async def debug_page():
            """Serve the skill debugging tools."""
            return await self._render_template("debug.html")

        @self.app.get("/builder", response_class=HTMLResponse)
        async def builder_page():
            """Serve the interactive skill builder."""
            return await self._render_template("builder.html")

        # ======================
        # API Endpoints - Skills
        # ======================

        @self.app.get("/api/skills")
        async def list_skills():
            """List all skills."""
            skills = await self.skill_manager.list_skills()
            return {"skills": [s.model_dump() for s in skills]}

        @self.app.get("/api/skills/{skill_id}")
        async def get_skill(skill_id: str):
            """Get skill details."""
            skill = await self.skill_manager.get_skill(skill_id)
            if not skill:
                raise HTTPException(status_code=404, detail="Skill not found")
            return skill.model_dump()

        @self.app.delete("/api/skills/{skill_id}")
        async def delete_skill(skill_id: str):
            """Delete a skill."""
            await self.skill_manager.delete_skill(skill_id)
            self.audit.log_event(
                AuditEventType.SKILL_DELETED,
                f"Skill {skill_id} deleted via web UI",
                skill_id=skill_id
            )
            return {"message": "Skill deleted successfully"}

        @self.app.post("/api/skills/{skill_id}/execute")
        async def execute_skill(skill_id: str, inputs: dict[str, Any]):
            """Execute a skill."""
            skill = await self.skill_manager.get_skill(skill_id)
            if not skill:
                raise HTTPException(status_code=404, detail="Skill not found")

            # Execute skill
            result = await self.engine.run_skill(skill, inputs)

            self.audit.log_event(
                AuditEventType.SKILL_EXECUTED,
                f"Skill {skill_id} executed via web UI",
                skill_id=skill_id,
                run_id=result.run_id
            )

            return result.model_dump()

        # ======================
        # API Endpoints - Metrics
        # ======================

        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get current metrics."""
            return self.metrics.get_current_metrics()

        @self.app.get("/api/metrics/dashboard")
        async def get_dashboard_metrics():
            """Get dashboard metrics."""
            return self.metrics.get_dashboard_metrics()

        @self.app.get("/api/metrics/{metric_name}/history")
        async def get_metric_history(
            metric_name: str,
            minutes: int = 60
        ):
            """Get metric history."""
            from datetime import timedelta, timezone
            start_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            points = self.metrics.get_metric_history(
                metric_name,
                start_time=start_time
            )
            return {
                "metric": metric_name,
                "points": [p.model_dump() for p in points]
            }

        @self.app.get("/api/metrics/prometheus")
        async def get_prometheus_metrics():
            """Get metrics in Prometheus format."""
            return self.metrics.export_metrics_prometheus()

        # ======================
        # API Endpoints - Audit
        # ======================

        @self.app.get("/api/audit/events")
        async def get_audit_events(
            event_type: Optional[str] = None,
            severity: Optional[str] = None,
            skill_id: Optional[str] = None,
            limit: int = 100
        ):
            """Query audit events."""
            events = self.audit.query_events(
                event_type=event_type,
                severity=severity,
                skill_id=skill_id,
                limit=limit
            )
            return {
                "events": [e.model_dump() for e in events],
                "total": len(events)
            }

        @self.app.get("/api/audit/statistics")
        async def get_audit_statistics(minutes: int = 60):
            """Get audit statistics."""
            from datetime import timedelta, timezone
            start_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            return self.audit.get_statistics(start_time=start_time)

        # ======================
        # WebSocket - Real-time Updates
        # ======================

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.active_connections.append(websocket)

            try:
                while True:
                    # Send periodic updates
                    await asyncio.sleep(1)

                    # Send current metrics
                    metrics = self.metrics.get_dashboard_metrics()
                    recent_events = self.audit.get_recent_events(limit=10)

                    await websocket.send_json({
                        "type": "update",
                        "metrics": metrics,
                        "recent_events": [e.model_dump() for e in recent_events]
                    })

            except WebSocketDisconnect:
                self.active_connections.remove(websocket)

    async def _render_template(self, template_name: str) -> str:
        """
        Render an HTML template.

        Args:
            template_name: Name of the template file

        Returns:
            Rendered HTML string
        """
        templates_dir = Path(__file__).parent / "templates"
        template_path = templates_dir / template_name

        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template not found")

        return template_path.read_text()

    async def start(self) -> None:
        """Start the web server."""
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )

        server = uvicorn.Server(config)

        self.audit.log_event(
            AuditEventType.SERVER_STARTED,
            f"Web server started on http://{self.host}:{self.port}",
            severity=AuditEventSeverity.INFO
        )

        await server.serve()

    async def stop(self) -> None:
        """Stop the web server."""
        # Close all WebSocket connections
        for connection in self.active_connections:
            await connection.close()

        self.audit.log_event(
            AuditEventType.SERVER_STOPPED,
            "Web server stopped",
            severity=AuditEventSeverity.INFO
        )


# REST API request/response models

class ExecuteSkillRequest(BaseModel):
    """Request model for skill execution."""
    inputs: dict[str, Any]


class CreateSkillRequest(BaseModel):
    """Request model for skill creation."""
    skill_id: str
    name: str
    description: Optional[str] = None
    graph: dict[str, Any]


class UpdateSkillRequest(BaseModel):
    """Request model for skill update."""
    name: Optional[str] = None
    description: Optional[str] = None
    graph: Optional[dict[str, Any]] = None
