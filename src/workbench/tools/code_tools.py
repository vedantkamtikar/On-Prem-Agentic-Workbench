"""Code execution tool integrated with sandboxing and network isolation."""

from typing import Any, Dict
from workbench.sandbox.executor import get_sandbox_executor
from workbench.tools.base import ToolDefinition


def run_code(code: str, timeout_seconds: int = 30) -> str:
    """
    Execute Python code in an isolated sandbox (Docker --network none or guarded subprocess).
    Captures stdout, stderr, and execution status.
    """
    executor = get_sandbox_executor()
    res = executor.run_code(code, timeout_seconds=timeout_seconds)

    output = []
    output.append(f"Sandbox Engine: {res['sandbox_type']} (Network Isolated: {res['network_isolated']})")
    output.append(f"Exit Code: {res['exit_code']} (Time: {res['duration_ms']:.1f}ms)")

    if res["stdout"]:
        output.append(f"STDOUT:\n{res['stdout']}")
    if res["stderr"]:
        output.append(f"STDERR:\n{res['stderr']}")
    if not res["stdout"] and not res["stderr"]:
        output.append("(No console output produced)")

    return "\n".join(output)


CODE_TOOLS = [
    ToolDefinition(
        name="run_code",
        description="Execute Python source code in an isolated sandbox with zero network access and return stdout/stderr.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to run in sandbox"},
                "timeout_seconds": {"type": "integer", "description": "Maximum execution time in seconds", "default": 30}
            },
            "required": ["code"]
        },
        func=run_code
    )
]
