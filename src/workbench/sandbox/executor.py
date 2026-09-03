"""Sandboxed code execution engine with Docker --network none isolation and local fallback."""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
WORKSPACE_ROOT = Path(os.getenv("WORKBENCH_WORKSPACE_ROOT", os.getcwd())).resolve()

logger = logging.getLogger("workbench.sandbox")


class BaseSandboxExecutor(ABC):
    """Abstract executor for isolated code evaluation."""

    @abstractmethod
    def run_code(self, code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Execute code and return:
        {
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "duration_ms": float,
            "sandbox_type": str,
            "network_isolated": bool
        }
        """
        pass


class DockerSandboxExecutor(BaseSandboxExecutor):
    """
    Docker container sandbox with --network none, restricted CPU/memory, and temporary directory mounting.
    """

    def __init__(self, image_name: str = "python:3.11-slim"):
        self.image_name = image_name
        self._available: Optional[bool] = None
        self._last_checked: float = 0

    def is_docker_available(self) -> bool:
        """Check if Docker daemon is active and responsive, caching the result."""
        now = time.time()
        if self._available is not None and (now - self._last_checked < 60):
            return self._available

        try:
            res = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=2)
            self._available = (res.returncode == 0)
        except Exception:
            self._available = False

        self._last_checked = now
        return self._available

    def run_code(self, code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        scratch_dir = WORKSPACE_ROOT / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        script_filename = f"docker_exec_{int(time.time()*1000)}.py"
        script_path = scratch_dir / script_filename

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Docker run with strict isolation flags
            # Convert Windows path for Docker volume mounting
            abs_scratch = str(scratch_dir.resolve()).replace("\\", "/")
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",            # Strict ZERO network access
                "--memory", "512m",             # Max 512 MB RAM
                "--cpus", "2.0",                # Max 2 CPU cores
                "--pids-limit", "100",          # Fork bomb protection
                "-v", f"{abs_scratch}:/sandbox:rw",
                "-w", "/sandbox",
                self.image_name,
                "python", script_filename
            ]

            start_t = time.perf_counter()
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            duration_ms = (time.perf_counter() - start_t) * 1000.0

            return {
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
                "sandbox_type": "docker_network_none",
                "network_isolated": True
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "exit_code": -1,
                "duration_ms": timeout_seconds * 1000.0,
                "sandbox_type": "docker_network_none",
                "network_isolated": True
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Docker sandbox error: {str(e)}",
                "exit_code": -1,
                "duration_ms": 0.0,
                "sandbox_type": "docker_network_none",
                "network_isolated": True
            }
        finally:
            if script_path.exists():
                try:
                    script_path.unlink()
                except Exception:
                    pass


class SubprocessSandboxExecutor(BaseSandboxExecutor):
    """
    Subprocess sandbox fallback with socket blocking guard injected to emulate network isolation.
    """

    # Injected prefix that disables external socket creation in Python
    NETWORK_GUARD = """
# Sovereign Air-Gap Network Isolation Guard
import socket
def _blocked_socket(*args, **kwargs):
    raise OSError(101, "Network unreachable (Sovereign Air-Gap Policy: Outbound network calls blocked)")
socket.socket = _blocked_socket
socket.create_connection = _blocked_socket
"""

    def run_code(self, code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        scratch_dir = WORKSPACE_ROOT / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        script_filename = f"subproc_exec_{int(time.time()*1000)}.py"
        script_path = scratch_dir / script_filename

        # Prepend network isolation guard
        guarded_code = self.NETWORK_GUARD + "\n# --- User Code ---\n" + code

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(guarded_code)

            start_t = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            duration_ms = (time.perf_counter() - start_t) * 1000.0

            return {
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
                "sandbox_type": "subprocess_airgap_guarded",
                "network_isolated": True
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "exit_code": -1,
                "duration_ms": timeout_seconds * 1000.0,
                "sandbox_type": "subprocess_airgap_guarded",
                "network_isolated": True
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Subprocess sandbox error: {str(e)}",
                "exit_code": -1,
                "duration_ms": 0.0,
                "sandbox_type": "subprocess_airgap_guarded",
                "network_isolated": True
            }
        finally:
            if script_path.exists():
                try:
                    script_path.unlink()
                except Exception:
                    pass


# Singleton Factory
_docker_executor: Optional[DockerSandboxExecutor] = None
_subprocess_executor: Optional[SubprocessSandboxExecutor] = None


def get_sandbox_executor(force_type: Optional[str] = None) -> BaseSandboxExecutor:
    """Return appropriate sandbox executor (Docker if available, otherwise Subprocess)."""
    global _docker_executor, _subprocess_executor

    if force_type == "subprocess":
        if _subprocess_executor is None:
            _subprocess_executor = SubprocessSandboxExecutor()
        return _subprocess_executor

    if force_type == "docker":
        if _docker_executor is None:
            _docker_executor = DockerSandboxExecutor()
        return _docker_executor

    # Auto-detect Docker
    if _docker_executor is None:
        _docker_executor = DockerSandboxExecutor()

    if _docker_executor.is_docker_available():
        return _docker_executor

    if _subprocess_executor is None:
        _subprocess_executor = SubprocessSandboxExecutor()
    return _subprocess_executor
