"""Router package for dynamic task-to-model dispatching."""

from workbench.router.classifier import EmbeddingClassifier, LLMClassifier
from workbench.router.router import ModelRouter, RoutingDecision, get_model_router

__all__ = [
    "EmbeddingClassifier",
    "LLMClassifier",
    "ModelRouter",
    "RoutingDecision",
    "get_model_router",
]
