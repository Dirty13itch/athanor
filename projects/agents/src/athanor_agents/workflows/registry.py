"""Workflow registry -- stores and retrieves workflow definitions."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Type aliases for clarity
WorkflowStep = dict[str, Any]
WorkflowDefinition = dict[str, Any]

# Internal registry -- populated at import time from definitions.py
_registry: dict[str, WorkflowDefinition] = {}


def register_workflow(definition: WorkflowDefinition) -> None:
    """Register a workflow definition.

    Each definition must have:
        name: str           -- unique workflow identifier
        description: str    -- human-readable summary
        steps: list[WorkflowStep]

    Each step must have:
        agent_id: str       -- which agent handles this step
        action: str         -- short label for what this step does
        input_template: str -- prompt template; may reference {input} and
                               prior step output keys via {step_key}
        output_key: str     -- key under which this step's result is stored
    """
    name = definition.get("name", "")
    if not name:
        raise ValueError("Workflow definition must have a 'name'")
    if not definition.get("steps"):
        raise ValueError(f"Workflow '{name}' must have at least one step")

    _registry[name] = definition
    logger.debug("Registered workflow: %s (%d steps)", name, len(definition["steps"]))


def get_workflow(name: str) -> WorkflowDefinition | None:
    """Get a workflow definition by name."""
    return _registry.get(name)


def list_workflows() -> list[WorkflowDefinition]:
    """List all registered workflow definitions."""
    return list(_registry.values())


def _load_builtins() -> None:
    """Load built-in workflow definitions from definitions module."""
    from .definitions import WORKFLOW_DEFINITIONS

    for defn in WORKFLOW_DEFINITIONS:
        try:
            register_workflow(defn)
        except ValueError as e:
            logger.warning("Skipping invalid built-in workflow: %s", e)


# Auto-load built-in workflows on first import
_load_builtins()
