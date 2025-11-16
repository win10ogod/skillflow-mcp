"""Execution engine for skill DAG execution."""

import asyncio
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from .schemas import (
    ConcurrencyMode,
    ErrorStrategy,
    NodeExecution,
    NodeKind,
    NodeStatus,
    RunStatus,
    Skill,
    SkillGraph,
    SkillNode,
    SkillRunResult,
    SkillRunStatus,
)
from .storage import StorageLayer


class ExecutionContext:
    """Context for a skill execution run."""

    def __init__(self, run_id: str, skill: Skill, inputs: dict[str, Any]):
        """Initialize execution context.

        Args:
            run_id: Unique run identifier
            skill: Skill being executed
            inputs: Input parameters for the skill
        """
        self.run_id = run_id
        self.skill = skill
        self.inputs = inputs
        self.outputs: dict[str, Any] = {}
        self.node_outputs: dict[str, dict[str, Any]] = {}
        self.node_statuses: dict[str, NodeStatus] = {}
        self.node_executions: list[NodeExecution] = []
        self.cancelled = False


class ExecutionEngine:
    """Engine for executing skill DAGs with concurrency support."""

    def __init__(
        self,
        storage: StorageLayer,
        tool_executor: Callable,
        max_concurrency: int = 32,
    ):
        """Initialize execution engine.

        Args:
            storage: Storage layer for logging
            tool_executor: Async function to execute tools (server, tool, args) -> result
            max_concurrency: Maximum concurrent tasks
        """
        self.storage = storage
        self.tool_executor = tool_executor
        self.max_concurrency = max_concurrency
        self._active_runs: dict[str, ExecutionContext] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run_skill(
        self,
        skill: Skill,
        inputs: dict[str, Any],
    ) -> SkillRunResult:
        """Execute a skill with given inputs.

        Args:
            skill: The skill to execute
            inputs: Input parameters

        Returns:
            Skill run result

        Raises:
            ValueError: If inputs don't match schema
        """
        run_id = f"run_{uuid4().hex}"
        context = ExecutionContext(run_id, skill, inputs)
        self._active_runs[run_id] = context

        started_at = datetime.utcnow()
        status = RunStatus.RUNNING

        try:
            # Initialize all nodes as pending
            for node in skill.graph.nodes:
                context.node_statuses[node.id] = NodeStatus.PENDING

            # Execute the graph
            await self._execute_graph(context, skill.graph)

            # Determine final status
            if context.cancelled:
                status = RunStatus.CANCELLED
            elif any(s == NodeStatus.FAILED for s in context.node_statuses.values()):
                if any(s == NodeStatus.SUCCESS for s in context.node_statuses.values()):
                    status = RunStatus.PARTIAL_FAILURE
                else:
                    status = RunStatus.FAILED
            else:
                status = RunStatus.SUCCESS

            # Extract outputs
            context.outputs = self._extract_outputs(context, skill)

        except Exception as e:
            status = RunStatus.FAILED
            context.outputs = {"error": str(e)}

        finally:
            ended_at = datetime.utcnow()
            del self._active_runs[run_id]

        return SkillRunResult(
            run_id=run_id,
            skill_id=skill.id,
            version=skill.version,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            outputs=context.outputs,
            error=context.outputs.get("error") if status == RunStatus.FAILED else None,
            node_executions=context.node_executions,
        )

    async def get_run_status(self, run_id: str) -> Optional[SkillRunStatus]:
        """Get status of an active run.

        Args:
            run_id: Run identifier

        Returns:
            Run status or None if not found
        """
        context = self._active_runs.get(run_id)
        if not context:
            return None

        total_nodes = len(context.skill.graph.nodes)
        completed_nodes = sum(
            1 for s in context.node_statuses.values()
            if s in (NodeStatus.SUCCESS, NodeStatus.FAILED, NodeStatus.SKIPPED)
        )
        failed_nodes = sum(1 for s in context.node_statuses.values() if s == NodeStatus.FAILED)

        # Determine overall status
        if context.cancelled:
            status = RunStatus.CANCELLED
        elif all(s in (NodeStatus.SUCCESS, NodeStatus.SKIPPED) for s in context.node_statuses.values()):
            status = RunStatus.SUCCESS
        elif any(s == NodeStatus.FAILED for s in context.node_statuses.values()):
            status = RunStatus.PARTIAL_FAILURE if completed_nodes < total_nodes else RunStatus.FAILED
        else:
            status = RunStatus.RUNNING

        return SkillRunStatus(
            run_id=run_id,
            skill_id=context.skill.id,
            version=context.skill.version,
            status=status,
            started_at=datetime.utcnow(),  # Should track actual start time
            total_nodes=total_nodes,
            completed_nodes=completed_nodes,
            failed_nodes=failed_nodes,
            node_statuses=context.node_statuses.copy(),
        )

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel an active run.

        Args:
            run_id: Run identifier

        Returns:
            True if run was cancelled
        """
        context = self._active_runs.get(run_id)
        if not context:
            return False

        context.cancelled = True
        return True

    async def _execute_graph(self, context: ExecutionContext, graph: SkillGraph) -> None:
        """Execute the skill graph.

        Args:
            context: Execution context
            graph: Skill graph to execute
        """
        if graph.concurrency.mode == ConcurrencyMode.SEQUENTIAL:
            await self._execute_sequential(context, graph)
        elif graph.concurrency.mode == ConcurrencyMode.PHASED:
            await self._execute_phased(context, graph)
        elif graph.concurrency.mode == ConcurrencyMode.FULL_PARALLEL:
            await self._execute_full_parallel(context, graph)

    async def _execute_sequential(self, context: ExecutionContext, graph: SkillGraph) -> None:
        """Execute nodes sequentially in topological order.

        Args:
            context: Execution context
            graph: Skill graph
        """
        # Topological sort
        nodes_order = self._topological_sort(graph)

        for node in nodes_order:
            if context.cancelled:
                break

            # Check if dependencies succeeded
            if not self._can_execute_node(context, node, graph):
                context.node_statuses[node.id] = NodeStatus.SKIPPED
                continue

            await self._execute_node(context, node)

    async def _execute_phased(self, context: ExecutionContext, graph: SkillGraph) -> None:
        """Execute nodes in phases with parallelism within each phase.

        Args:
            context: Execution context
            graph: Skill graph
        """
        phases = graph.concurrency.phases

        # Sort phase IDs
        phase_ids = sorted(phases.keys())

        for phase_id in phase_ids:
            if context.cancelled:
                break

            node_ids = phases[phase_id]
            nodes = [n for n in graph.nodes if n.id in node_ids]

            # Execute all nodes in phase concurrently
            tasks = []
            for node in nodes:
                if self._can_execute_node(context, node, graph):
                    tasks.append(self._execute_node(context, node))
                else:
                    context.node_statuses[node.id] = NodeStatus.SKIPPED

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_full_parallel(self, context: ExecutionContext, graph: SkillGraph) -> None:
        """Execute all independent nodes in parallel respecting dependencies.

        Args:
            context: Execution context
            graph: Skill graph
        """
        pending = set(n.id for n in graph.nodes)
        running = set()
        finished = set()

        while pending or running:
            if context.cancelled:
                break

            # Find nodes ready to execute
            ready = []
            for node_id in pending:
                node = next(n for n in graph.nodes if n.id == node_id)
                if self._can_execute_node(context, node, graph):
                    ready.append(node)

            # Start ready nodes
            tasks = {}
            for node in ready:
                pending.remove(node.id)
                running.add(node.id)
                task = asyncio.create_task(self._execute_node(context, node))
                tasks[task] = node.id

            if not tasks:
                # No progress possible, mark remaining as skipped
                for node_id in pending:
                    context.node_statuses[node_id] = NodeStatus.SKIPPED
                break

            # Wait for at least one task to complete
            done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                node_id = tasks[task]
                running.remove(node_id)
                finished.add(node_id)

    async def _execute_node(self, context: ExecutionContext, node: SkillNode) -> None:
        """Execute a single node.

        Args:
            context: Execution context
            node: Node to execute
        """
        async with self._semaphore:
            context.node_statuses[node.id] = NodeStatus.RUNNING
            started_at = datetime.utcnow()

            try:
                # Resolve arguments
                args = self._resolve_args(context, node.args_template)

                # Execute based on node kind
                if node.kind == NodeKind.TOOL_CALL:
                    result = await self._execute_tool_call(context, node, args)
                elif node.kind == NodeKind.SKILL_CALL:
                    result = await self._execute_skill_call(context, node, args)
                else:
                    result = {}

                # Store outputs
                context.node_outputs[node.id] = result

                # Extract exported outputs
                for output_name, jsonpath in node.export_outputs.items():
                    value = self._extract_jsonpath(result, jsonpath)
                    context.outputs[output_name] = value

                context.node_statuses[node.id] = NodeStatus.SUCCESS

                # Log execution
                execution = NodeExecution(
                    run_id=context.run_id,
                    skill_id=context.skill.id,
                    version=context.skill.version,
                    node_id=node.id,
                    status=NodeStatus.SUCCESS,
                    started_at=started_at,
                    ended_at=datetime.utcnow(),
                    server=node.server,
                    tool=node.tool,
                    args_resolved=args,
                    output=result,
                )
                context.node_executions.append(execution)
                await self.storage.append_run_log(context.run_id, execution)

            except Exception as e:
                context.node_statuses[node.id] = NodeStatus.FAILED

                execution = NodeExecution(
                    run_id=context.run_id,
                    skill_id=context.skill.id,
                    version=context.skill.version,
                    node_id=node.id,
                    status=NodeStatus.FAILED,
                    started_at=started_at,
                    ended_at=datetime.utcnow(),
                    server=node.server,
                    tool=node.tool,
                    args_resolved=args if 'args' in locals() else {},
                    error=str(e),
                )
                context.node_executions.append(execution)
                await self.storage.append_run_log(context.run_id, execution)

                # Handle error strategy
                if node.error_strategy == ErrorStrategy.FAIL_FAST:
                    raise

    async def _execute_tool_call(
        self,
        context: ExecutionContext,
        node: SkillNode,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool call.

        Args:
            context: Execution context
            node: Node being executed
            args: Resolved arguments

        Returns:
            Tool execution result
        """
        return await self.tool_executor(node.server, node.tool, args)

    async def _execute_skill_call(
        self,
        context: ExecutionContext,
        node: SkillNode,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a nested skill call.

        Args:
            context: Execution context
            node: Node being executed
            args: Resolved arguments

        Returns:
            Skill execution result
        """
        # This would load and execute another skill
        # For now, return placeholder
        return {"nested_skill": node.tool}

    def _can_execute_node(
        self,
        context: ExecutionContext,
        node: SkillNode,
        graph: SkillGraph,
    ) -> bool:
        """Check if a node can be executed.

        Args:
            context: Execution context
            node: Node to check
            graph: Skill graph

        Returns:
            True if node can execute
        """
        # Check dependencies
        for dep_id in node.depends_on:
            status = context.node_statuses.get(dep_id)
            if status != NodeStatus.SUCCESS:
                return False

        # Check incoming edges
        for edge in graph.edges:
            if edge.to_node == node.id:
                from_status = context.node_statuses.get(edge.from_node)
                if from_status != NodeStatus.SUCCESS:
                    return False

        return True

    def _resolve_args(self, context: ExecutionContext, args_template: dict[str, Any]) -> dict[str, Any]:
        """Resolve argument templates.

        Args:
            context: Execution context
            args_template: Argument template with placeholders

        Returns:
            Resolved arguments
        """
        resolved = {}

        for key, value in args_template.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_template_string(context, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_args(context, value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_template_string(context, v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_template_string(self, context: ExecutionContext, template: str) -> Any:
        """Resolve a template string.

        Supports:
        - $inputs.field -> context.inputs["field"]
        - @step_id.outputs.field -> context.node_outputs["step_id"]["field"]

        Args:
            context: Execution context
            template: Template string

        Returns:
            Resolved value
        """
        if not isinstance(template, str):
            return template

        # Match $inputs.field
        if template.startswith("$inputs."):
            field = template[8:]  # Remove "$inputs."
            return self._get_nested_value(context.inputs, field)

        # Match @step_id.outputs.field
        if template.startswith("@"):
            match = re.match(r"@(\w+)\.outputs\.(.+)", template)
            if match:
                step_id, field = match.groups()
                outputs = context.node_outputs.get(step_id, {})
                return self._get_nested_value(outputs, field)

        return template

    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get nested value from dict using dot notation.

        Args:
            obj: Object to extract from
            path: Dot-separated path

        Returns:
            Extracted value or None
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def _extract_jsonpath(self, obj: Any, jsonpath: str) -> Any:
        """Extract value using JSONPath (simplified).

        Args:
            obj: Object to extract from
            jsonpath: JSONPath expression

        Returns:
            Extracted value
        """
        # Simplified JSONPath: $.field.subfield
        if jsonpath.startswith("$."):
            path = jsonpath[2:]
            return self._get_nested_value(obj, path)

        return None

    def _topological_sort(self, graph: SkillGraph) -> list[SkillNode]:
        """Topologically sort nodes.

        Args:
            graph: Skill graph

        Returns:
            Nodes in topological order
        """
        # Build adjacency list
        in_degree = defaultdict(int)
        adj_list = defaultdict(list)
        nodes_by_id = {n.id: n for n in graph.nodes}

        for node in graph.nodes:
            in_degree[node.id] = 0

        for edge in graph.edges:
            adj_list[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] += 1

        # Also handle depends_on
        for node in graph.nodes:
            for dep_id in node.depends_on:
                if dep_id not in adj_list[dep_id]:
                    adj_list[dep_id].append(node.id)
                    in_degree[node.id] += 1

        # Kahn's algorithm
        queue = [n.id for n in graph.nodes if in_degree[n.id] == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(nodes_by_id[node_id])

            for neighbor in adj_list[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _extract_outputs(self, context: ExecutionContext, skill: Skill) -> dict[str, Any]:
        """Extract final outputs based on skill output schema.

        Args:
            context: Execution context
            skill: Skill definition

        Returns:
            Final outputs
        """
        # For now, return accumulated outputs
        # In production, this should respect output_schema
        return context.outputs
