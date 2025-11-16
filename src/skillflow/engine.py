"""Execution engine for skill DAG execution with advanced features support."""

import asyncio
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from .schemas import (
    ConcurrencyMode,
    ConditionalType,
    ErrorStrategy,
    LoopType,
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

# Import parameter transformation utilities
try:
    from .parameter_transform import transform_parameter, evaluate_condition
    TRANSFORMS_AVAILABLE = True
except ImportError:
    TRANSFORMS_AVAILABLE = False
    transform_parameter = None
    evaluate_condition = None


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
        # Advanced features support
        self.loop_vars: dict[str, Any] = {}  # Loop iteration variables
        self.parent_context: Optional['ExecutionContext'] = None  # For nested skill calls


class ExecutionEngine:
    """Engine for executing skill DAGs with concurrency support and advanced features."""

    def __init__(
        self,
        storage: StorageLayer,
        tool_executor: Callable,
        max_concurrency: int = 32,
        skill_manager: Optional[Any] = None,  # SkillManager, optional for skill nesting
    ):
        """Initialize execution engine.

        Args:
            storage: Storage layer for logging
            tool_executor: Async function to execute tools (server, tool, args) -> result
            max_concurrency: Maximum concurrent tasks
            skill_manager: Optional skill manager for nested skill execution
        """
        self.storage = storage
        self.tool_executor = tool_executor
        self.max_concurrency = max_concurrency
        self.skill_manager = skill_manager
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
        """Execute a single node with support for all node types.

        Args:
            context: Execution context
            node: Node to execute
        """
        async with self._semaphore:
            context.node_statuses[node.id] = NodeStatus.RUNNING
            started_at = datetime.utcnow()

            try:
                # Resolve arguments with parameter transformation support
                args = self._resolve_args(context, node.args_template)

                # Apply parameter transformation if configured
                if node.parameter_transform and TRANSFORMS_AVAILABLE:
                    transform_context = {
                        "inputs": context.inputs,
                        "outputs": context.outputs,
                        "loop_vars": context.loop_vars,
                    }
                    args = transform_parameter(
                        args,
                        node.parameter_transform.engine,
                        node.parameter_transform.expression,
                        transform_context,
                    )

                # Execute based on node kind
                if node.kind == NodeKind.TOOL_CALL:
                    result = await self._execute_tool_call(context, node, args)
                elif node.kind == NodeKind.SKILL_CALL:
                    result = await self._execute_skill_call(context, node, args)
                elif node.kind == NodeKind.CONDITIONAL:
                    result = await self._execute_conditional(context, node, args)
                elif node.kind == NodeKind.LOOP:
                    result = await self._execute_loop(context, node, args)
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
        """Execute a nested skill call (Phase 3 feature).

        Args:
            context: Execution context
            node: Node being executed
            args: Resolved arguments

        Returns:
            Skill execution result
        """
        if not node.skill_id:
            raise ValueError(f"SKILL_CALL node {node.id} missing skill_id")

        if not self.skill_manager:
            raise ValueError("Skill nesting requires skill_manager in ExecutionEngine")

        # Load the nested skill
        nested_skill = await self.skill_manager.get_skill(node.skill_id)

        # Execute the nested skill with provided arguments
        result = await self.run_skill(nested_skill, args)

        # Return outputs from nested skill execution
        return result.outputs

    async def _execute_conditional(
        self,
        context: ExecutionContext,
        node: SkillNode,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a conditional node (Phase 3 feature).

        Args:
            context: Execution context
            node: Node being executed
            args: Resolved arguments

        Returns:
            Results from executed branch
        """
        if not node.conditional_config:
            raise ValueError(f"CONDITIONAL node {node.id} missing conditional_config")

        config = node.conditional_config
        eval_context = {
            "inputs": context.inputs,
            "outputs": context.outputs,
            "loop_vars": context.loop_vars,
            "args": args,
        }

        executed_branch = None

        # Evaluate branches in order
        for branch in config.branches:
            if not TRANSFORMS_AVAILABLE or not evaluate_condition:
                # Fallback: simple boolean evaluation
                condition_result = bool(eval_context.get(branch.condition))
            else:
                condition_result = evaluate_condition(branch.condition, eval_context)

            if condition_result:
                executed_branch = branch.nodes
                break

        # Use default branch if no condition matched
        if executed_branch is None and config.default_branch:
            executed_branch = config.default_branch

        if executed_branch is None:
            return {"branch_executed": None, "results": []}

        # Execute nodes in the selected branch
        results = []
        nodes_by_id = {n.id: n for n in context.skill.graph.nodes}

        for node_id in executed_branch:
            if node_id in nodes_by_id:
                branch_node = nodes_by_id[node_id]
                await self._execute_node(context, branch_node)
                results.append({
                    "node_id": node_id,
                    "output": context.node_outputs.get(node_id, {}),
                })

        return {
            "branch_executed": executed_branch,
            "results": results,
        }

    async def _execute_loop(
        self,
        context: ExecutionContext,
        node: SkillNode,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a loop node (Phase 3 feature).

        Args:
            context: Execution context
            node: Node being executed
            args: Resolved arguments

        Returns:
            Results from all iterations
        """
        if not node.loop_config:
            raise ValueError(f"LOOP node {node.id} missing loop_config")

        config = node.loop_config
        iterations = []
        iteration_count = 0

        nodes_by_id = {n.id: n for n in context.skill.graph.nodes}

        # Prepare iteration based on loop type
        if config.type == LoopType.FOR:
            # Iterate over collection
            if not config.collection_path:
                raise ValueError(f"FOR loop {node.id} missing collection_path")

            collection = self._extract_jsonpath(
                {"inputs": context.inputs, "outputs": context.outputs},
                config.collection_path
            )

            if not isinstance(collection, list):
                collection = [collection] if collection is not None else []

            for item in collection:
                if config.max_iterations and iteration_count >= config.max_iterations:
                    break

                # Set loop variable
                context.loop_vars[config.iteration_var] = item
                context.loop_vars["index"] = iteration_count

                # Execute loop body
                iteration_results = await self._execute_loop_body(
                    context, config.body_nodes, nodes_by_id
                )
                iterations.append({
                    "iteration": iteration_count,
                    "item": item,
                    "results": iteration_results,
                })
                iteration_count += 1

        elif config.type == LoopType.WHILE:
            # Loop while condition is true
            if not config.condition:
                raise ValueError(f"WHILE loop {node.id} missing condition")

            while True:
                if config.max_iterations and iteration_count >= config.max_iterations:
                    break

                # Evaluate condition
                eval_context = {
                    "inputs": context.inputs,
                    "outputs": context.outputs,
                    "loop_vars": context.loop_vars,
                }

                if not TRANSFORMS_AVAILABLE or not evaluate_condition:
                    condition_result = bool(eval_context.get(config.condition))
                else:
                    condition_result = evaluate_condition(config.condition, eval_context)

                if not condition_result:
                    break

                # Set loop variable
                context.loop_vars["index"] = iteration_count

                # Execute loop body
                iteration_results = await self._execute_loop_body(
                    context, config.body_nodes, nodes_by_id
                )
                iterations.append({
                    "iteration": iteration_count,
                    "results": iteration_results,
                })
                iteration_count += 1

        elif config.type == LoopType.FOR_RANGE:
            # Iterate over numeric range
            start = config.range_start or 0
            end = config.range_end or 0
            step = config.range_step or 1

            for i in range(start, end, step):
                if config.max_iterations and iteration_count >= config.max_iterations:
                    break

                # Set loop variable
                context.loop_vars[config.iteration_var] = i
                context.loop_vars["index"] = iteration_count

                # Execute loop body
                iteration_results = await self._execute_loop_body(
                    context, config.body_nodes, nodes_by_id
                )
                iterations.append({
                    "iteration": iteration_count,
                    "value": i,
                    "results": iteration_results,
                })
                iteration_count += 1

        # Clear loop variables
        context.loop_vars.clear()

        return {
            "loop_type": config.type.value,
            "iterations": iterations,
            "total_iterations": iteration_count,
        }

    async def _execute_loop_body(
        self,
        context: ExecutionContext,
        body_node_ids: list[str],
        nodes_by_id: dict[str, SkillNode],
    ) -> list[dict[str, Any]]:
        """Execute nodes in a loop body.

        Args:
            context: Execution context
            body_node_ids: Node IDs to execute in loop body
            nodes_by_id: Map of node IDs to nodes

        Returns:
            Results from executed nodes
        """
        results = []

        for node_id in body_node_ids:
            if node_id in nodes_by_id:
                body_node = nodes_by_id[node_id]
                await self._execute_node(context, body_node)
                results.append({
                    "node_id": node_id,
                    "output": context.node_outputs.get(node_id, {}),
                })

        return results

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
        """Resolve a template string with advanced features support.

        Supports:
        - $inputs.field -> context.inputs["field"]
        - @step_id.outputs.field -> context.node_outputs["step_id"]["field"]
        - $loop.var_name -> context.loop_vars["var_name"] (Phase 3)

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

        # Match $loop.var_name (Phase 3 - loop variables)
        if template.startswith("$loop."):
            var_name = template[6:]  # Remove "$loop."
            return context.loop_vars.get(var_name)

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
