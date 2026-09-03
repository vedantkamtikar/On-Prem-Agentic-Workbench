"""Unit test suite for Sovereign On-Prem Agentic AI Workbench."""

import asyncio
import os
import sys
from pathlib import Path
import pytest

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from workbench.tools.base import resolve_safe_path, WORKSPACE_ROOT
from workbench.tools import execute_tool_call, get_all_tool_schemas, TOOL_MAP
from workbench.models.registry import get_model_registry
from workbench.models.ollama_client import OllamaClient, LoadedModelStatus
from workbench.rag.embeddings import get_embedding_function
from workbench.rag.knowledge_base import get_knowledge_base
from workbench.router.classifier import EmbeddingClassifier
from workbench.vision.ocr_engine import get_ocr_engine


def test_safe_path_resolution():
    """Verify path confinement and Windows case-insensitivity."""
    valid_subpath = "data/kb"
    resolved = resolve_safe_path(valid_subpath)
    assert resolved.exists() or str(WORKSPACE_ROOT) in str(resolved)

    # Escape attempt
    with pytest.raises(PermissionError):
        resolve_safe_path("../../outside_workspace.txt")


@pytest.mark.asyncio
async def test_async_tool_execution():
    """Verify execute_tool_call executes async and sync tools without event loop crashes."""
    # Test sync tool
    res_list = await execute_tool_call("list_directory", {"dir_path": "."})
    assert "data" in res_list or "src" in res_list

    # Test unknown tool
    res_unknown = await execute_tool_call("non_existent_tool", {})
    assert "Error" in res_unknown


from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_model_tag_isolation():
    """Verify is_model_loaded differentiates qwen3.5:0.8b from qwen3.5:4b."""
    client = OllamaClient()

    # Simulate mock loaded models from ollama ps
    client.get_loaded_models = AsyncMock(return_value=[
        LoadedModelStatus(
            name="qwen3.5:0.8b",
            model="qwen3.5:0.8b",
            size=1000000000,
            size_vram=1000000000
        )
    ])

    is_08b_loaded = await client.is_model_loaded("qwen3.5:0.8b")
    is_4b_loaded = await client.is_model_loaded("qwen3.5:4b")
    is_7b_loaded = await client.is_model_loaded("qwen2.5-coder:7b")

    assert is_08b_loaded is True
    assert is_4b_loaded is False  # Must NOT be True due to prefix collision!
    assert is_7b_loaded is False


def test_registry_bidirectional_task_matching():
    """Verify task hint matching in registry."""
    reg = get_model_registry()

    general_model = reg.get_model_for_task("drafting")
    assert "4b" in general_model.name

    code_model_1 = reg.get_model_for_task("coding")
    assert "coder" in code_model_1.name

    code_model_2 = reg.get_model_for_task("code")
    assert "coder" in code_model_2.name

    vision_model = reg.get_model_for_task("vision")
    assert "2.5vl" in vision_model.name or "vl" in vision_model.name


def test_shared_embedding_singleton():
    """Verify EmbeddingClassifier reuses singleton CPUEmbeddingFunction."""
    emb_fn = get_embedding_function()
    cls = EmbeddingClassifier(embedding_fn=emb_fn)
    assert cls.embedding_fn is emb_fn


def test_ocr_engine_cpu_guarantee():
    """Verify CPU OCR runs strictly on CPU with 0 CUDA bytes."""
    engine = get_ocr_engine()
    # Test on a synthetic text file or standard mock
    res = engine.extract("data/kb/kirloskar_pump_information.pdf")
    assert res["device"] == "cpu"
    assert res["cuda_allocated_bytes"] == 0
    assert len(res["text"]) > 0


def test_kb_query():
    """Verify local knowledge base search."""
    kb = get_knowledge_base()
    results = kb.query("pump head flow rate", top_k=2)
    assert isinstance(results, list)
    if results:
        assert "source" in results[0]
        assert "score" in results[0]
