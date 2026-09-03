"""File manipulation tools with strict path sandboxing."""

import os
from pathlib import Path
from typing import Any, Dict, List
from workbench.tools.base import ToolDefinition, resolve_safe_path


def read_file(file_path: str, max_chars: int = 20000) -> str:
    """
    Read text from a file within the workspace.
    """
    safe_path = resolve_safe_path(file_path, must_exist=True)
    try:
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        if safe_path.stat().st_size > max_chars:
            content += f"\n... [Truncated at {max_chars} characters. Total size: {safe_path.stat().st_size} bytes]"
        return content
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file within the workspace, creating parent directories if needed.
    """
    safe_path = resolve_safe_path(file_path, must_exist=False)
    try:
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{file_path}'"
    except Exception as e:
        return f"Error writing file '{file_path}': {str(e)}"


def list_directory(dir_path: str = ".") -> str:
    """
    List files and directories within a workspace subfolder.
    """
    safe_path = resolve_safe_path(dir_path, must_exist=True)
    try:
        items = []
        for p in safe_path.iterdir():
            t = "DIR" if p.is_dir() else "FILE"
            size = f"({p.stat().st_size} bytes)" if p.is_file() else ""
            items.append(f"[{t}] {p.name} {size}")
        return "\n".join(items) if items else "(Empty directory)"
    except Exception as e:
        return f"Error listing directory '{dir_path}': {str(e)}"


# Tool Schemas for LLM
FILE_TOOLS = [
    ToolDefinition(
        name="read_file",
        description="Read text content from a file in the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to file in workspace, e.g. 'data/report.txt'"},
                "max_chars": {"type": "integer", "description": "Maximum characters to read", "default": 20000}
            },
            "required": ["file_path"]
        },
        func=read_file
    ),
    ToolDefinition(
        name="write_file",
        description="Write text content to a file in the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to output file, e.g. 'output/notes.txt'"},
                "content": {"type": "string", "description": "Text content to write"}
            },
            "required": ["file_path", "content"]
        },
        func=write_file
    ),
    ToolDefinition(
        name="list_directory",
        description="List files in a workspace directory.",
        parameters={
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "description": "Directory to inspect, e.g. 'data' or '.'", "default": "."}
            }
        },
        func=list_directory
    )
]
