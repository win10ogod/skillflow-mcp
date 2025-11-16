"""Data models and schemas for SkillFlow MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ========== Recording Session Models ==========

class ToolCallStatus(str, Enum):
    """Status of a tool call execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolCallLog(BaseModel):
    """A single tool call log entry in a recording session."""
    index: int
    timestamp: datetime
    server: str
    tool: str
    args: dict[str, Any]
    result_summary: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float
    status: ToolCallStatus


class RecordingContext(BaseModel):
    """Context information for a recording session."""
    client_id: str
    workspace_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecordingSession(BaseModel):
    """A complete recording session."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    client_id: str
    workspace_id: str = "default"
    logs: list[ToolCallLog] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ========== Skill Models ==========

class SkillAuthor(BaseModel):
    """Author information for a skill."""
    workspace_id: str
    client_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeKind(str, Enum):
    """Type of node in skill graph."""
    TOOL_CALL = "tool_call"
    SKILL_CALL = "skill_call"
    CONTROL = "control"


class ErrorStrategy(str, Enum):
    """Error handling strategy for a node."""
    FAIL_FAST = "fail_fast"
    SKIP_DEPENDENTS = "skip_dependents"
    RETRY = "retry"
    CONTINUE = "continue"


class RetryConfig(BaseModel):
    """Retry configuration for error handling."""
    max_retries: int = 3
    backoff_ms: int = 1000
    backoff_multiplier: float = 2.0


class SkillNode(BaseModel):
    """A single node in the skill execution graph."""
    id: str
    kind: NodeKind
    server: Optional[str] = None  # None for local tools
    tool: str
    args_template: dict[str, Any]
    export_outputs: dict[str, str] = Field(default_factory=dict)  # output_name -> JSONPath
    depends_on: list[str] = Field(default_factory=list)
    error_strategy: ErrorStrategy = ErrorStrategy.FAIL_FAST
    retry_config: Optional[RetryConfig] = None
    timeout_ms: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillEdge(BaseModel):
    """An edge in the skill execution graph."""
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    condition: Optional[str] = None  # JSONPath condition

    class Config:
        populate_by_name = True


class ConcurrencyMode(str, Enum):
    """Concurrency mode for skill execution."""
    SEQUENTIAL = "sequential"
    PHASED = "phased"
    FULL_PARALLEL = "full_parallel"


class Concurrency(BaseModel):
    """Concurrency configuration for skill execution."""
    mode: ConcurrencyMode = ConcurrencyMode.SEQUENTIAL
    phases: dict[str, list[str]] = Field(default_factory=dict)  # phase_id -> node_ids
    max_parallel: Optional[int] = None


class SkillGraph(BaseModel):
    """Execution graph for a skill."""
    nodes: list[SkillNode]
    edges: list[SkillEdge] = Field(default_factory=list)
    concurrency: Concurrency = Field(default_factory=Concurrency)


class Skill(BaseModel):
    """A complete skill definition."""
    id: str
    name: str
    version: int = 1
    description: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    author: SkillAuthor
    inputs_schema: dict[str, Any]  # JSON Schema
    output_schema: dict[str, Any]  # JSON Schema
    graph: SkillGraph
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillMeta(BaseModel):
    """Lightweight skill metadata for listing."""
    id: str
    name: str
    version: int
    description: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    author: SkillAuthor


class SkillFilter(BaseModel):
    """Filter criteria for skill queries."""
    query: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    author_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


# ========== Skill Execution Models ==========

class NodeStatus(str, Enum):
    """Execution status of a node."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class NodeExecution(BaseModel):
    """Execution record for a single node."""
    run_id: str
    skill_id: str
    version: int
    node_id: str
    status: NodeStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    server: Optional[str] = None
    tool: str
    args_resolved: dict[str, Any]
    output: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0


class RunStatus(str, Enum):
    """Overall status of a skill run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkillRunStatus(BaseModel):
    """Status information for a skill run."""
    run_id: str
    skill_id: str
    version: int
    status: RunStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    node_statuses: dict[str, NodeStatus]
    current_phase: Optional[str] = None
    error: Optional[str] = None


class SkillRunResult(BaseModel):
    """Final result of a skill run."""
    run_id: str
    skill_id: str
    version: int
    status: RunStatus
    started_at: datetime
    ended_at: datetime
    outputs: dict[str, Any]
    error: Optional[str] = None
    node_executions: list[NodeExecution]


# ========== MCP Server Registry ==========

class TransportType(str, Enum):
    """MCP transport type."""
    STDIO = "stdio"
    HTTP_SSE = "http_sse"
    STREAMABLE_HTTP = "streamable_http"


class ServerConfig(BaseModel):
    """Configuration for an upstream MCP server."""
    server_id: str
    name: str
    transport: TransportType
    config: dict[str, Any]  # Transport-specific config
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServerRegistry(BaseModel):
    """Registry of upstream MCP servers."""
    servers: dict[str, ServerConfig] = Field(default_factory=dict)


# ========== Skill Creation ==========

class StepSelection(BaseModel):
    """Selection of steps from a recording session."""
    session_id: str
    indices: Optional[list[int]] = None  # None means all
    start_index: Optional[int] = None
    end_index: Optional[int] = None


class ExposeParamSpec(BaseModel):
    """Specification for exposing a parameter from session logs."""
    name: str
    description: str
    schema_: dict[str, Any] = Field(alias="schema")
    source_path: str  # JSONPath to extract from logs

    class Config:
        populate_by_name = True


class SkillDraft(BaseModel):
    """Draft skill created from a recording session."""
    skill_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    graph: SkillGraph
    inputs_schema: dict[str, Any]
    output_schema: dict[str, Any]
    source_session_id: str
