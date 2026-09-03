"""Vision and OCR tools for Agent Orchestrator."""

import asyncio
from typing import Any, Dict
from workbench.tools.base import ToolDefinition
from workbench.vision.ocr_engine import get_ocr_engine
from workbench.vision.vision_analyzer import get_vision_analyzer


def ocr_image(file_path: str) -> str:
    """
    Extract dense printed text, tables, and equipment tags from an image or PDF using CPU-only OCR.
    """
    engine = get_ocr_engine()
    try:
        res = engine.extract(file_path)
        return (
            f"OCR Extraction for '{file_path}' (Completed on CPU in {res['duration_ms']:.1f}ms):\n"
            f"Extracted Text:\n{res['text']}"
        )
    except Exception as e:
        return f"Error executing OCR on '{file_path}': {str(e)}"


async def analyze_visual_document(file_path: str, instruction: str = "Analyze equipment tags and operational parameters") -> str:
    """
    Perform multimodal visual analysis on a diagram (P&ID, schematic) or scanned PDF.
    """
    analyzer = get_vision_analyzer()
    try:
        res = await analyzer.analyze_visual_document(file_path=file_path, user_query=instruction)
        return (
            f"Vision Analysis for '{file_path}' (Model: {res['model_used']}):\n\n"
            f"--- OCR Extracted Text ---\n{res['ocr_text']}\n\n"
            f"--- Visual Interpretation & Engineering Findings ---\n{res['vision_analysis']}"
        )
    except Exception as e:
        return f"Error analyzing visual document '{file_path}': {str(e)}"


VISION_TOOLS = [
    ToolDefinition(
        name="ocr_image",
        description="Extract text, tabular data, and engineering tags from an image or scanned PDF using CPU OCR.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to image or PDF in workspace"}
            },
            "required": ["file_path"]
        },
        func=ocr_image
    ),
    ToolDefinition(
        name="analyze_visual_document",
        description="Perform deep visual and OCR understanding on an engineering diagram, P&ID, or scanned report.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to image or PDF in workspace"},
                "instruction": {"type": "string", "description": "Specific query or inspection instruction"}
            },
            "required": ["file_path"]
        },
        func=analyze_visual_document
    )
]
