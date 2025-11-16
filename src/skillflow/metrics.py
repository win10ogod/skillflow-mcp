"""
Advanced monitoring and metrics system for SkillFlow MCP server.

Collects and tracks performance metrics, execution statistics,
and resource usage for monitoring and optimization.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .storage import StorageLayer


class MetricType(str):
    """Types of metrics."""

    # Execution metrics
    SKILL_EXECUTION_TIME = "skill_execution_time_ms"
    TOOL_CALL_TIME = "tool_call_time_ms"
    NODE_EXECUTION_TIME = "node_execution_time_ms"

    # Count metrics
    SKILL_EXECUTIONS = "skill_executions_total"
    SKILL_SUCCESSES = "skill_successes_total"
    SKILL_FAILURES = "skill_failures_total"
    TOOL_CALLS = "tool_calls_total"

    # Concurrency metrics
    CONCURRENT_EXECUTIONS = "concurrent_executions_current"
    MAX_CONCURRENT_EXECUTIONS = "max_concurrent_executions"

    # Resource metrics
    MEMORY_USAGE_MB = "memory_usage_mb"
    ACTIVE_CONNECTIONS = "active_connections"

    # Performance metrics
    THROUGHPUT_PER_MINUTE = "throughput_per_minute"
    ERROR_RATE_PERCENT = "error_rate_percent"
    P50_EXECUTION_TIME = "p50_execution_time_ms"
    P95_EXECUTION_TIME = "p95_execution_time_ms"
    P99_EXECUTION_TIME = "p99_execution_time_ms"


class MetricPoint(BaseModel):
    """A single metric data point."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Metric timestamp (UTC)"
    )
    metric_name: str = Field(description="Metric name")
    value: float = Field(description="Metric value")
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Metric tags for filtering"
    )

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricsCollector:
    """Collects and manages metrics for the SkillFlow server."""

    def __init__(self, storage: StorageLayer):
        """
        Initialize metrics collector.

        Args:
            storage: Storage layer instance
        """
        self.storage = storage
        self.metrics_dir = Path(storage.data_dir) / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # In-memory metric storage (time-series data)
        # Key: metric_name, Value: deque of MetricPoint
        self._metrics: dict[str, deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=10000)  # Keep last 10k points per metric
        )

        # Aggregated metrics for fast queries
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}

        # Execution tracking
        self._execution_times: deque[float] = deque(maxlen=1000)
        self._active_executions = 0
        self._max_concurrent = 0

        # Start background tasks
        self._background_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background metric collection tasks."""
        self._background_task = asyncio.create_task(self._collect_system_metrics())

    async def stop(self) -> None:
        """Stop background metric collection tasks."""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

    async def _collect_system_metrics(self) -> None:
        """Background task to collect system-level metrics."""
        while True:
            try:
                # Collect memory usage
                try:
                    import psutil
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    self.record_gauge(MetricType.MEMORY_USAGE_MB, memory_mb)
                except ImportError:
                    # psutil not available, skip memory metrics
                    pass

                # Record concurrent executions
                self.record_gauge(
                    MetricType.CONCURRENT_EXECUTIONS,
                    self._active_executions
                )
                self.record_gauge(
                    MetricType.MAX_CONCURRENT_EXECUTIONS,
                    self._max_concurrent
                )

                # Calculate throughput (executions per minute)
                recent_executions = sum(
                    1 for point in self._metrics.get(MetricType.SKILL_EXECUTIONS, [])
                    if point.timestamp > datetime.now(timezone.utc) - timedelta(minutes=1)
                )
                self.record_gauge(MetricType.THROUGHPUT_PER_MINUTE, recent_executions)

                # Calculate error rate
                total = self._counters.get(MetricType.SKILL_EXECUTIONS, 0)
                failures = self._counters.get(MetricType.SKILL_FAILURES, 0)
                error_rate = (failures / total * 100) if total > 0 else 0.0
                self.record_gauge(MetricType.ERROR_RATE_PERCENT, error_rate)

                # Calculate percentiles
                if self._execution_times:
                    sorted_times = sorted(self._execution_times)
                    p50 = sorted_times[len(sorted_times) // 2]
                    p95 = sorted_times[int(len(sorted_times) * 0.95)]
                    p99 = sorted_times[int(len(sorted_times) * 0.99)]

                    self.record_gauge(MetricType.P50_EXECUTION_TIME, p50)
                    self.record_gauge(MetricType.P95_EXECUTION_TIME, p95)
                    self.record_gauge(MetricType.P99_EXECUTION_TIME, p99)

                await asyncio.sleep(10)  # Collect every 10 seconds

            except Exception:
                # Don't let metrics collection crash the server
                await asyncio.sleep(10)

    def record_counter(
        self,
        metric_name: str,
        value: float = 1.0,
        tags: Optional[dict[str, str]] = None
    ) -> None:
        """
        Record a counter metric (monotonically increasing).

        Args:
            metric_name: Name of the metric
            value: Value to add (default: 1)
            tags: Optional tags for the metric
        """
        point = MetricPoint(
            metric_name=metric_name,
            value=value,
            tags=tags or {}
        )

        self._metrics[metric_name].append(point)
        self._counters[metric_name] += value

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: Optional[dict[str, str]] = None
    ) -> None:
        """
        Record a gauge metric (can go up and down).

        Args:
            metric_name: Name of the metric
            value: Current value
            tags: Optional tags for the metric
        """
        point = MetricPoint(
            metric_name=metric_name,
            value=value,
            tags=tags or {}
        )

        self._metrics[metric_name].append(point)
        self._gauges[metric_name] = value

    def record_timing(
        self,
        metric_name: str,
        duration_ms: float,
        tags: Optional[dict[str, str]] = None
    ) -> None:
        """
        Record a timing metric.

        Args:
            metric_name: Name of the metric
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        point = MetricPoint(
            metric_name=metric_name,
            value=duration_ms,
            tags=tags or {}
        )

        self._metrics[metric_name].append(point)
        self._execution_times.append(duration_ms)

    def execution_started(self) -> None:
        """Track that a skill execution has started."""
        self._active_executions += 1
        self._max_concurrent = max(self._max_concurrent, self._active_executions)
        self.record_counter(MetricType.SKILL_EXECUTIONS)

    def execution_completed(self, duration_ms: float, success: bool = True) -> None:
        """
        Track that a skill execution has completed.

        Args:
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
        """
        self._active_executions = max(0, self._active_executions - 1)

        self.record_timing(MetricType.SKILL_EXECUTION_TIME, duration_ms)

        if success:
            self.record_counter(MetricType.SKILL_SUCCESSES)
        else:
            self.record_counter(MetricType.SKILL_FAILURES)

    def tool_call_completed(self, tool_name: str, duration_ms: float) -> None:
        """
        Track a tool call completion.

        Args:
            tool_name: Name of the tool
            duration_ms: Call duration in milliseconds
        """
        self.record_counter(MetricType.TOOL_CALLS, tags={"tool": tool_name})
        self.record_timing(
            MetricType.TOOL_CALL_TIME,
            duration_ms,
            tags={"tool": tool_name}
        )

    def get_metric_history(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> list[MetricPoint]:
        """
        Get historical metric data.

        Args:
            metric_name: Name of the metric
            start_time: Filter by start time (UTC)
            end_time: Filter by end time (UTC)
            limit: Maximum number of points to return

        Returns:
            List of metric points (newest first)
        """
        if metric_name not in self._metrics:
            return []

        points = list(self._metrics[metric_name])

        # Apply time filters
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]

        # Return newest first
        points.reverse()
        return points[:limit]

    def get_current_metrics(self) -> dict[str, Any]:
        """
        Get current metric values.

        Returns:
            Dictionary of current metric values
        """
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "active_executions": self._active_executions,
            "max_concurrent_executions": self._max_concurrent,
        }

    def get_metric_summary(
        self,
        metric_name: str,
        window_minutes: int = 60
    ) -> dict[str, Any]:
        """
        Get summary statistics for a metric over a time window.

        Args:
            metric_name: Name of the metric
            window_minutes: Time window in minutes

        Returns:
            Summary statistics (min, max, avg, count)
        """
        start_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        points = self.get_metric_history(metric_name, start_time=start_time)

        if not points:
            return {
                "metric": metric_name,
                "window_minutes": window_minutes,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "latest": None,
            }

        values = [p.value for p in points]

        return {
            "metric": metric_name,
            "window_minutes": window_minutes,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[0] if values else None,
        }

    def get_dashboard_metrics(self) -> dict[str, Any]:
        """
        Get key metrics for dashboard display.

        Returns:
            Dictionary with dashboard metrics
        """
        return {
            "current": self.get_current_metrics(),
            "throughput": self.get_metric_summary(
                MetricType.THROUGHPUT_PER_MINUTE,
                window_minutes=60
            ),
            "error_rate": self._gauges.get(MetricType.ERROR_RATE_PERCENT, 0.0),
            "execution_time": {
                "p50": self._gauges.get(MetricType.P50_EXECUTION_TIME, 0.0),
                "p95": self._gauges.get(MetricType.P95_EXECUTION_TIME, 0.0),
                "p99": self._gauges.get(MetricType.P99_EXECUTION_TIME, 0.0),
            },
            "memory_mb": self._gauges.get(MetricType.MEMORY_USAGE_MB, 0.0),
        }

    def export_metrics_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        # Export counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Export gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        return "\n".join(lines) + "\n"


class MetricsTimer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, metric_name: str,
                 tags: Optional[dict[str, str]] = None):
        """
        Initialize metrics timer.

        Args:
            collector: Metrics collector instance
            metric_name: Name of the metric to record
            tags: Optional tags for the metric
        """
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = 0.0

    def __enter__(self) -> "MetricsTimer":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and record metric."""
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.record_timing(self.metric_name, duration_ms, self.tags)
