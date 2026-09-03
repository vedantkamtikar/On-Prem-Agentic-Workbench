"""Multimodal Document and Diagram Analyzer combining CPU OCR and Qwen3.5-4B Vision."""

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from workbench.models.ollama_client import OllamaClient, get_ollama_client
from workbench.models.registry import ModelConfig, ModelRegistry, get_model_registry
from workbench.tools.base import resolve_safe_path, WORKSPACE_ROOT
from workbench.vision.ocr_engine import CPUOCREngine, get_ocr_engine

logger = logging.getLogger("workbench.vision.analyzer")


class VisionDocumentAnalyzer:
    """
    Combines CPU-only OCR preprocessing with Qwen3.5-4B Multimodal Vision understanding.
    """

    def __init__(
        self,
        ocr_engine: Optional[CPUOCREngine] = None,
        ollama_client: Optional[OllamaClient] = None,
        registry: Optional[ModelRegistry] = None
    ):
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self.client = ollama_client or get_ollama_client()
        self.registry = registry or get_model_registry()

    def _encode_image_base64(self, image_path: Path) -> str:
        """Read and encode an image file to Base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def analyze_visual_document(
        self,
        file_path: str,
        user_query: str = "Analyze this document/diagram and extract key equipment tags, findings, and operational specs."
    ) -> Dict[str, Any]:
        """
        Full multimodal analysis pipeline:
        1. CPU OCR Pre-Processing pass
        2. Base64 visual encoding
        3. Multimodal inference via Qwen3.5-4B
        """
        start_t = time.perf_counter()
        safe_path = resolve_safe_path(file_path, must_exist=True)

        # 1. CPU OCR Preprocessing
        logger.info(f"Running CPU OCR pass on '{file_path}'...")
        ocr_result = self.ocr_engine.extract(file_path)
        ocr_text = ocr_result.get("text", "")

        # 2. Prepare Base64 Image
        images_b64 = []
        ext = safe_path.suffix.lower()
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
            b64_str = self._encode_image_base64(safe_path)
            images_b64.append(b64_str)

        # 3. Assemble Hybrid Context Prompt
        hybrid_prompt = (
            f"USER QUERY:\n{user_query}\n\n"
            f"PRE-EXTRACTED OCR TEXT (from CPU pass):\n"
            f"```\n{ocr_text}\n```\n\n"
            "Please analyze the visual structure, symbols, connections, and extracted text to provide a thorough engineering assessment."
        )

        # 4. Resolve Vision Model (Qwen3.5-4B) from registry
        vision_model_cfg = self.registry.get_model_for_task("vision")

        # 5. Execute Multimodal Inference
        logger.info(f"Dispatching multimodal query to vision model '{vision_model_cfg.name}'...")
        res = await self.client.run_prompt(
            model_config=vision_model_cfg,
            prompt=hybrid_prompt,
            images=images_b64 if images_b64 else None,
            temperature=0.2
        )

        total_duration = (time.perf_counter() - start_t) * 1000.0

        return {
            "file_path": file_path,
            "ocr_text": ocr_text,
            "ocr_duration_ms": ocr_result.get("duration_ms", 0.0),
            "vision_analysis": res["response"],
            "model_used": vision_model_cfg.name,
            "total_duration_ms": total_duration,
            "cuda_allocated_bytes": ocr_result.get("cuda_allocated_bytes", 0)
        }


# Singleton
_analyzer_instance: Optional[VisionDocumentAnalyzer] = None


def get_vision_analyzer() -> VisionDocumentAnalyzer:
    """Get or create singleton VisionDocumentAnalyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = VisionDocumentAnalyzer()
    return _analyzer_instance
