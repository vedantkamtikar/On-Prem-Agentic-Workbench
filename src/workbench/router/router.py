"""Model Router: Unified routing engine for task classification and model resolution."""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from workbench.models.ollama_client import OllamaClient, get_ollama_client
from workbench.models.registry import ModelConfig, ModelRegistry, get_model_registry
from workbench.router.classifier import EmbeddingClassifier, LLMClassifier

logger = logging.getLogger("workbench.router")


class RoutingDecision(BaseModel):
    """Encapsulates the decision made by the model router."""
    target_model: ModelConfig
    model_key: str
    task_type: str
    confidence: float = 1.0
    reasoning: str = ""
    classification_latency_ms: float = 0.0
    routing_strategy: str = "llm_classifier"  # "multimodal_override" | "explicit_hint" | "llm_classifier" | "embedding_cpu"


class ModelRouter:
    """
    Intelligent Model Router.
    Selects optimal model dynamically using registry definitions with no hardcoded logic.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        self.registry = registry or get_model_registry()
        self.client = ollama_client or get_ollama_client()
        self.llm_classifier = LLMClassifier(registry=self.registry, ollama_client=self.client)
        self.embedding_classifier = EmbeddingClassifier(registry=self.registry)

    async def route(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        task_hint: Optional[str] = None,
        preferred_classifier: str = "auto"
    ) -> RoutingDecision:
        """
        Route incoming prompt + optional images to the best matching model in the registry.
        """
        start_t = time.perf_counter()
        reg_cfg = self.registry.config

        # 1. Multimodal Override (Images present -> require image-capable model)
        if images and len(images) > 0:
            for key, m in reg_cfg.models.items():
                if m.role == "worker" and "image" in m.modality:
                    latency = (time.perf_counter() - start_t) * 1000.0
                    decision = RoutingDecision(
                        target_model=m,
                        model_key=key,
                        task_type="vision",
                        confidence=1.0,
                        reasoning=f"Multimodal input detected ({len(images)} image(s)). Selected vision-capable model '{m.name}'.",
                        classification_latency_ms=latency,
                        routing_strategy="multimodal_override"
                    )
                    self._log_decision(decision)
                    return decision

        # 2. Explicit Task Hint (if user explicitly designated task type)
        if task_hint and task_hint.strip():
            hint_clean = task_hint.strip().lower()
            model_cfg = self.registry.get_model_for_task(hint_clean)
            latency = (time.perf_counter() - start_t) * 1000.0
            decision = RoutingDecision(
                target_model=model_cfg,
                model_key=model_cfg.key,
                task_type=hint_clean,
                confidence=1.0,
                reasoning=f"Explicit task hint provided: '{task_hint}'.",
                classification_latency_ms=latency,
                routing_strategy="explicit_hint"
            )
            self._log_decision(decision)
            return decision

        # 3. Dynamic Classification (Fast 15ms CPU Semantic Classifier -> 0.8B LLM Fallback)
        if preferred_classifier in ["auto", "embedding", "cpu"]:
            try:
                cls_res = self.embedding_classifier.classify(prompt)
                task_type = cls_res["task_type"]
                model_cfg = self.registry.get_model_for_task(task_type)
                latency = (time.perf_counter() - start_t) * 1000.0

                decision = RoutingDecision(
                    target_model=model_cfg,
                    model_key=model_cfg.key,
                    task_type=task_type,
                    confidence=cls_res["confidence"],
                    reasoning=cls_res["rationale"],
                    classification_latency_ms=latency,
                    routing_strategy="embedding_cpu"
                )
                self._log_decision(decision)
                return decision
            except Exception as e:
                logger.warning(f"CPU embedding classifier failed ({e}), attempting LLM classifier fallback.")

        # 4. LLM Resident Classifier (0.8B)
        try:
            if await self.client.is_server_ready():
                cls_res = await self.llm_classifier.classify(prompt, reg_cfg)
                model_key = cls_res["model_key"]
                model_cfg = reg_cfg.models.get(model_key) or self.registry.get_model_by_key(model_key)
                latency = (time.perf_counter() - start_t) * 1000.0

                decision = RoutingDecision(
                    target_model=model_cfg,
                    model_key=model_key,
                    task_type=cls_res["task_type"],
                    confidence=cls_res["confidence"],
                    reasoning=cls_res["reasoning"],
                    classification_latency_ms=latency,
                    routing_strategy="llm_classifier"
                )
                self._log_decision(decision)
                return decision
        except Exception as e:
            logger.warning(f"LLM classifier failed ({e}).")

        # 5. Default Fallback Model
        model_cfg = self.registry.get_default_model()
        latency = (time.perf_counter() - start_t) * 1000.0
        decision = RoutingDecision(
            target_model=model_cfg,
            model_key=model_cfg.key,
            task_type="general",
            confidence=0.5,
            reasoning="Default fallback model",
            classification_latency_ms=latency,
            routing_strategy="fallback_default"
        )
        self._log_decision(decision)
        return decision

    def _log_decision(self, decision: RoutingDecision):
        """Structured logging of routing decisions."""
        logger.info(json.dumps({
            "event": "model_routing_decision",
            "model_selected": decision.target_model.name,
            "model_key": decision.model_key,
            "task_type": decision.task_type,
            "confidence": round(decision.confidence, 3),
            "strategy": decision.routing_strategy,
            "latency_ms": round(decision.classification_latency_ms, 2),
            "reasoning": decision.reasoning
        }))


# Singleton
_router_instance: Optional[ModelRouter] = None


def get_model_router(
    registry: Optional[ModelRegistry] = None,
    ollama_client: Optional[OllamaClient] = None
) -> ModelRouter:
    """Get or create singleton ModelRouter."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter(registry=registry, ollama_client=ollama_client)
    return _router_instance
