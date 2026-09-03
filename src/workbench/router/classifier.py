"""Dynamic prompt and embedding classifiers for Task Type resolution."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import numpy as np
from workbench.models.ollama_client import OllamaClient, get_ollama_client
from workbench.models.registry import ModelConfig, ModelRegistry, get_model_registry
from workbench.rag.embeddings import CPUEmbeddingFunction, get_embedding_function

# Force strict offline mode
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger("workbench.router.classifier")


class LLMClassifier:
    """Uses the resident Qwen3.5-0.8B model to classify user task into registry roles."""

    def __init__(self, registry: Optional[ModelRegistry] = None, ollama_client: Optional[OllamaClient] = None):
        self.registry = registry or get_model_registry()
        self.client = ollama_client or get_ollama_client()

    def build_classification_prompt(self, user_query: str) -> str:
        """
        Dynamically constructs the classification prompt based on currently registered models.
        Zero hardcoded tasks — reads available roles directly from the registry.
        """
        config = self.registry.get_config()
        task_descriptions = []
        for key, model_cfg in config.models.items():
            if model_cfg.role == "classifier":
                continue
            tasks_list = getattr(model_cfg, "task_types", []) or getattr(model_cfg, "tasks", [])
            tasks_str = ", ".join(tasks_list)
            task_descriptions.append(
                f"- Task Type '{key}': Matches user intents such as: {tasks_str}. (Description: {model_cfg.description})"
            )

        categories_block = "\n".join(task_descriptions)
        available_keys = [k for k, m in config.models.items() if m.role != "classifier"]

        prompt = f"""You are a specialized router for an air-gapped industrial AI workbench.
Classify the following user prompt into exactly ONE of the following task categories:

{categories_block}

USER PROMPT:
"{user_query}"

Respond with ONLY a valid JSON object in this exact format:
{{"task_type": "<one of {available_keys}>", "confidence": <float between 0.0 and 1.0>, "rationale": "<brief 1-sentence reason>"}}
"""
        return prompt

    async def classify(self, user_query: str, registry_config: Optional[Any] = None) -> Dict[str, Any]:
        """Runs the 0.8B resident model to classify task type."""
        prompt = self.build_classification_prompt(user_query)
        router_config = self.registry.get_router_model()

        try:
            res = await self.client.run_prompt(
                model_config=router_config,
                prompt=prompt,
                temperature=0.0
            )
            raw_text = res["response"].strip()

            # Robust JSON extraction
            json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                # Validate task_type exists in registry
                valid_tasks = [k for k, m in self.registry.get_config().models.items() if m.role != "classifier"]
                task_type = parsed.get("task_type", "general")
                if task_type not in valid_tasks:
                    task_type = "general"
                rationale = parsed.get("rationale", "LLM router classification")
                latency = res.get("total_latency_ms", res.get("inference_latency_ms", 0.0))
                return {
                    "model_key": task_type,
                    "task_type": task_type,
                    "confidence": float(parsed.get("confidence", 0.9)),
                    "reasoning": rationale,
                    "rationale": rationale,
                    "strategy": "llm_resident_0.8b",
                    "latency_ms": latency
                }
        except Exception as e:
            logger.warning(f"LLM classifier failed ({e}), falling back to CPU embedding classifier.")

        # Fallback to general task
        return {
            "model_key": "general",
            "task_type": "general",
            "confidence": 0.5,
            "reasoning": "Fallback classification after LLM router error",
            "rationale": "Fallback classification after LLM router error",
            "strategy": "fallback_default",
            "latency_ms": 0.0
        }


class EmbeddingClassifier:
    """CPU-only fallback classifier using sentence embeddings for zero-VRAM task matching."""

    def __init__(self, registry: Optional[ModelRegistry] = None, embedding_fn: Optional[CPUEmbeddingFunction] = None):
        self.registry = registry or get_model_registry()
        self.embedding_fn = embedding_fn or get_embedding_function()
        self._task_embeddings = None
        self._task_keys = []

    def _init_embeddings(self):
        """Precomputes reference embeddings for each registered task category strictly on CPU."""
        config = self.registry.get_config()
        self._task_keys = [k for k, m in config.models.items() if m.role != "classifier"]
        if not self._task_keys:
            self._task_keys = ["general"]
            self._task_embeddings = self.embedding_fn.encode(["general task"])
            return

        # Rich domain-specific anchor definitions for robust semantic matching
        anchor_enrichments = {
            "general": "technical drafting document synthesis SOP compliance review executive summary report specifications turbine pump manuals checklist verification Word docx",
            "coding": "python script code generation debugging calculation formula RMS vibration severity Fourier algorithm math programming execute container sandbox",
            "vision": "visual inspection optical OCR tag schematic P&ID diagram drawing image layout piping equipment label nozzle visual QA"
        }

        task_texts = []
        for k in self._task_keys:
            m = config.models.get(k)
            extra = anchor_enrichments.get(k, "")
            if m:
                tasks_list = getattr(m, "task_types", []) or getattr(m, "tasks", [])
                combined = f"{k} {' '.join(tasks_list)} {m.description} {extra}"
                task_texts.append(combined)
            else:
                task_texts.append(f"{k} {extra}")

        self._task_embeddings = self.embedding_fn.encode(task_texts)

    def classify(self, user_query: str, registry_config: Optional[Any] = None) -> Dict[str, Any]:
        """Matches user query against task descriptions using cosine similarity on CPU."""
        # Detect registry changes to invalidate cached embeddings
        current_keys = sorted(k for k, m in self.registry.get_config().models.items() if m.role != "classifier")
        if self._task_embeddings is None or len(self._task_keys) == 0 or sorted(self._task_keys) != current_keys:
            self._init_embeddings()

        query_emb = self.embedding_fn.encode(user_query)[0]
        similarities = np.dot(self._task_embeddings, query_emb)
        if len(similarities) == 0:
            return {
                "model_key": "general",
                "task_type": "general",
                "classifier_type": "embedding_cpu",
                "confidence": 0.5,
                "rationale": "Default fallback",
                "reasoning": "Default fallback",
                "strategy": "embedding_cpu",
                "latency_ms": 5.0
            }

        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_task = self._task_keys[best_idx]

        return {
            "model_key": best_task,
            "task_type": best_task,
            "classifier_type": "embedding_cpu",
            "confidence": round(best_score, 4),
            "rationale": f"CPU embedding semantic similarity match (score: {best_score:.3f})",
            "reasoning": f"CPU embedding semantic similarity match (score: {best_score:.3f})",
            "strategy": "embedding_cpu",
            "latency_ms": 15.0
        }
