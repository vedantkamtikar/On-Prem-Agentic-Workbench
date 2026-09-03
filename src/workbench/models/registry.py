"""Model Registry module: reads, validates, and manages model configurations from YAML."""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    key: str = ""
    name: str = Field(..., description="Ollama model tag e.g. qwen3.5:4b")
    endpoint: str = Field(default="http://localhost:11434", description="Ollama API endpoint")
    context_window: int = Field(default=32768, description="Max context length")
    modality: List[str] = Field(default_factory=lambda: ["text"], description="Supported modalities (text, image)")
    keep_alive: str = Field(default="30m", description="Ollama keep_alive parameter")
    role: str = Field(default="worker", description="Model role: 'classifier', 'worker', etc.")
    task_types: List[str] = Field(default_factory=list, description="Task types handled by this model")
    description: str = Field(default="", description="Human-readable description")


class RegistryDefaults(BaseModel):
    fallback_model: str = Field(default="general")
    router_model: str = Field(default="router")
    swap_timeout_seconds: int = Field(default=120)
    max_concurrent_models: int = Field(default=2)


class RegistryConfig(BaseModel):
    models: Dict[str, ModelConfig]
    defaults: RegistryDefaults = Field(default_factory=RegistryDefaults)


class ModelRegistry:
    """Manages the model registry with auto-reloading capability."""

    def __init__(self, registry_path: Optional[str] = None):
        if registry_path is None:
            registry_path = os.getenv("MODEL_REGISTRY_PATH", "config/model_registry.yaml")
        self.registry_path = Path(registry_path)
        self._last_loaded_mtime: float = 0
        self._config: Optional[RegistryConfig] = None
        self.load(force=True)

    def load(self, force: bool = False) -> RegistryConfig:
        """Load or reload model registry from YAML file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Model registry file not found at: {self.registry_path.resolve()}")

        current_mtime = self.registry_path.stat().st_mtime
        if not force and self._config is not None and current_mtime <= self._last_loaded_mtime:
            return self._config

        with open(self.registry_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        models_dict = {}
        for key, model_data in raw_data.get("models", {}).items():
            model_data["key"] = key
            models_dict[key] = ModelConfig(**model_data)

        defaults_data = raw_data.get("defaults", {})
        defaults = RegistryDefaults(**defaults_data)

        self._config = RegistryConfig(models=models_dict, defaults=defaults)
        self._last_loaded_mtime = current_mtime
        return self._config

    def get_config(self) -> RegistryConfig:
        """Alias to load and retrieve the active registry config."""
        return self.load()

    @property
    def config(self) -> RegistryConfig:
        """Get the current configuration, automatically checking for updates on disk."""
        return self.load(force=False)

    def get_model_by_key(self, key: str) -> ModelConfig:
        """Retrieve model configuration by registry key (e.g. 'router', 'general', 'coding')."""
        cfg = self.config
        if key in cfg.models:
            return cfg.models[key]
        raise KeyError(f"Model key '{key}' not found in registry. Available keys: {list(cfg.models.keys())}")

    def get_model_for_task(self, task_type: str) -> ModelConfig:
        """Map a task type to the appropriate model config, or fallback to default."""
        cfg = self.config
        task_lower = task_type.strip().lower() if task_type else ""

        # Check if task_type is directly a model key
        if task_lower in cfg.models and cfg.models[task_lower].role == "worker":
            return cfg.models[task_lower]

        # Exact match or bidirectional substring match in task_types
        for model in cfg.models.values():
            if model.role == "worker" and any(task_lower == t.lower() or task_lower in t.lower() or t.lower() in task_lower for t in model.task_types):
                return model

        # Fallback
        fallback_key = cfg.defaults.fallback_model
        if fallback_key in cfg.models:
            return cfg.models[fallback_key]

        # First worker if fallback key missing
        for model in cfg.models.values():
            if model.role == "worker":
                return model

        # Ultimate fallback
        return list(cfg.models.values())[0]

    def get_router_model(self) -> ModelConfig:
        """Retrieve the router/classifier model config."""
        cfg = self.config
        router_key = cfg.defaults.router_model
        if router_key in cfg.models:
            return cfg.models[router_key]
        for model in cfg.models.values():
            if model.role == "classifier":
                return model
        raise KeyError("No router/classifier model defined in registry.")

    def get_default_model(self) -> ModelConfig:
        """Retrieve the default fallback worker model."""
        cfg = self.config
        fallback_key = cfg.defaults.fallback_model
        if fallback_key in cfg.models:
            return cfg.models[fallback_key]
        # First worker as fallback
        for model in cfg.models.values():
            if model.role == "worker":
                return model
        return list(cfg.models.values())[0]

    def list_models(self) -> List[ModelConfig]:
        """List all registered models."""
        return list(self.config.models.values())


# Global singleton instance
_registry_instance: Optional[ModelRegistry] = None


def get_model_registry(registry_path: Optional[str] = None) -> ModelRegistry:
    """Get or create singleton ModelRegistry instance."""
    global _registry_instance
    if _registry_instance is None or (registry_path and str(_registry_instance.registry_path) != registry_path):
        _registry_instance = ModelRegistry(registry_path=registry_path)
    return _registry_instance
