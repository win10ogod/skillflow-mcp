"""Parameter transformation utilities for JSONPath and Jinja2."""

import json
import re
from typing import Any, Optional

try:
    import jsonpath_ng
    from jsonpath_ng import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False

try:
    from jinja2 import Environment, Template, TemplateSyntaxError, UndefinedError
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class ParameterTransformError(Exception):
    """Error during parameter transformation."""
    pass


class ParameterTransformer:
    """Handles parameter transformations using JSONPath or Jinja2."""

    def __init__(self):
        """Initialize the parameter transformer."""
        if JINJA2_AVAILABLE:
            self.jinja_env = Environment(
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.jinja_env = None

    def transform(
        self,
        value: Any,
        engine: str,
        expression: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Transform a value using the specified engine.

        Args:
            value: The value to transform
            engine: Transformation engine ("jsonpath", "jinja2", or "none")
            expression: The transformation expression
            context: Additional context for the transformation

        Returns:
            Transformed value

        Raises:
            ParameterTransformError: If transformation fails
        """
        if engine == "none" or expression is None:
            return value

        if engine == "jsonpath":
            return self._transform_jsonpath(value, expression, context)
        elif engine == "jinja2":
            return self._transform_jinja2(value, expression, context)
        else:
            raise ParameterTransformError(f"Unknown transformation engine: {engine}")

    def _transform_jsonpath(
        self,
        value: Any,
        expression: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Transform value using JSONPath.

        Args:
            value: The value to query
            expression: JSONPath expression
            context: Additional context (not used for JSONPath)

        Returns:
            Extracted value(s)

        Raises:
            ParameterTransformError: If JSONPath is not available or query fails
        """
        if not JSONPATH_AVAILABLE:
            raise ParameterTransformError(
                "JSONPath transformation requires jsonpath-ng package. "
                "Install with: pip install jsonpath-ng"
            )

        try:
            # Parse the JSONPath expression
            jsonpath_expr = jsonpath_parse(expression)

            # Execute the query
            matches = jsonpath_expr.find(value)

            # Return results
            if not matches:
                return None
            elif len(matches) == 1:
                return matches[0].value
            else:
                return [match.value for match in matches]

        except Exception as e:
            raise ParameterTransformError(
                f"JSONPath transformation failed: {str(e)}"
            ) from e

    def _transform_jinja2(
        self,
        value: Any,
        expression: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Transform value using Jinja2 template.

        Args:
            value: The value to use in template
            expression: Jinja2 template string
            context: Additional context variables

        Returns:
            Rendered template result

        Raises:
            ParameterTransformError: If Jinja2 is not available or rendering fails
        """
        if not JINJA2_AVAILABLE:
            raise ParameterTransformError(
                "Jinja2 transformation requires jinja2 package. "
                "Install with: pip install jinja2"
            )

        if self.jinja_env is None:
            raise ParameterTransformError("Jinja2 environment not initialized")

        try:
            # Create template context
            template_context = {
                "value": value,
                **(context or {}),
            }

            # Render the template
            template = self.jinja_env.from_string(expression)
            result = template.render(template_context)

            # Try to parse as JSON if it looks like JSON
            result = result.strip()
            if result.startswith(("{", "[")):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    pass

            return result

        except (TemplateSyntaxError, UndefinedError) as e:
            raise ParameterTransformError(
                f"Jinja2 transformation failed: {str(e)}"
            ) from e
        except Exception as e:
            raise ParameterTransformError(
                f"Jinja2 transformation error: {str(e)}"
            ) from e

    def evaluate_condition(
        self,
        condition: str,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a condition expression.

        Conditions can be:
        - JSONPath expressions (e.g., "$.status == 'success'")
        - Jinja2 expressions (e.g., "{{ value > 10 }}")
        - Python-like comparisons (e.g., "status == 'success'")

        Args:
            condition: The condition expression
            context: Context for evaluation

        Returns:
            Boolean result of condition

        Raises:
            ParameterTransformError: If evaluation fails
        """
        condition = condition.strip()

        # Try Jinja2 if it looks like a template
        if "{{" in condition or "{%" in condition:
            result = self._transform_jinja2(context, f"{{% if {condition} %}}true{{% else %}}false{{% endif %}}", context)
            return result == "true"

        # Try JSONPath if it starts with $
        if condition.startswith("$"):
            result = self._transform_jsonpath(context, condition, context)
            return bool(result)

        # Try simple comparison evaluation
        try:
            # Replace variable names with context lookups
            # This is a simplified evaluation - in production, consider using a safer evaluator
            for key in context:
                condition = condition.replace(key, f'context["{key}"]')

            return bool(eval(condition, {"context": context}))
        except Exception as e:
            raise ParameterTransformError(
                f"Failed to evaluate condition '{condition}': {str(e)}"
            ) from e


# Global transformer instance
_transformer = ParameterTransformer()


def transform_parameter(
    value: Any,
    engine: str = "none",
    expression: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> Any:
    """Transform a parameter value.

    Args:
        value: Value to transform
        engine: Transformation engine
        expression: Transformation expression
        context: Additional context

    Returns:
        Transformed value
    """
    return _transformer.transform(value, engine, expression, context)


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition expression.

    Args:
        condition: Condition expression
        context: Evaluation context

    Returns:
        Boolean result
    """
    return _transformer.evaluate_condition(condition, context)
