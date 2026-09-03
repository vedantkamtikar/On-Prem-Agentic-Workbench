"""Unified tool exports for Agent Orchestrator."""

from typing import Any, Callable, Dict, List
from workbench.tools.base import ToolDefinition, resolve_safe_path, WORKSPACE_ROOT
from workbench.tools.code_tools import CODE_TOOLS, run_code
from workbench.tools.doc_tools import DOC_TOOLS, edit_spreadsheet, render_docx, render_pptx
from workbench.tools.file_tools import FILE_TOOLS, list_directory, read_file, write_file
from workbench.tools.kb_tools import KB_TOOLS, search_kb
from workbench.tools.vision_tools import VISION_TOOLS, analyze_visual_document, ocr_image

import asyncio
import inspect

ALL_TOOLS: List[ToolDefinition] = FILE_TOOLS + DOC_TOOLS + CODE_TOOLS + KB_TOOLS + VISION_TOOLS
TOOL_MAP: Dict[str, Callable] = {t.name: t.func for t in ALL_TOOLS if t.func is not None}


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Return tool schemas in Ollama / OpenAI function format."""
    return [t.to_ollama_tool() for t in ALL_TOOLS]


async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Safely invoke a tool function by name, supporting both async coroutines and sync tools."""
    if tool_name not in TOOL_MAP:
        return f"Error: Tool '{tool_name}' not found. Available tools: {list(TOOL_MAP.keys())}"

    func = TOOL_MAP[tool_name]
    try:
        if inspect.iscoroutinefunction(func):
            return await func(**arguments)
        else:
            return await asyncio.to_thread(func, **arguments)
    except TypeError as te:
        return f"Error executing tool '{tool_name}' with arguments {arguments}: {str(te)}"
    except Exception as e:
        return f"Error in tool '{tool_name}': {str(e)}"
