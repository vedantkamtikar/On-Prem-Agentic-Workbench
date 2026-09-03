"""Tool registry and base utilities for sandboxed agent tool execution."""

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

# Root workspace directory to enforce sandboxing
WORKSPACE_ROOT = Path(os.getenv("WORKBENCH_WORKSPACE_ROOT", os.getcwd())).resolve()


def resolve_safe_path(file_path: str, must_exist: bool = False) -> Path:
    """
    Ensure file paths do not escape the workspace root.
    Prevents directory traversal attacks in an air-gapped system.
    """
    raw_path = Path(file_path)
    if not raw_path.is_absolute():
        target = (WORKSPACE_ROOT / raw_path).resolve()
    else:
        target = raw_path.resolve()

    # Enforce containment within workspace
    norm_target = os.path.normcase(str(target))
    norm_root = os.path.normcase(str(WORKSPACE_ROOT))
    try:
        common = os.path.commonpath([norm_target, norm_root])
        if common != norm_root:
            raise PermissionError(f"Access denied: path '{file_path}' traverses outside workspace '{WORKSPACE_ROOT}'")
    except ValueError:
        raise PermissionError(f"Access denied: path '{file_path}' traverses outside workspace '{WORKSPACE_ROOT}'")

    if must_exist and not target.exists():
        raise FileNotFoundError(f"File not found: '{file_path}'")

    return target


class ToolDefinition(BaseModel):
    """Metadata and schema for an agent tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Optional[Any] = None

    def to_ollama_tool(self) -> Dict[str, Any]:
        """Format as Ollama / OpenAI compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
