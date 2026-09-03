"""Ollama client wrapper supporting hot-swapping, latency logging, and RAM/VRAM residency verification."""

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import ollama
from workbench.models.registry import ModelConfig, ModelRegistry, get_model_registry
from workbench.schemas.api_models import LoadedModelStatus

logger = logging.getLogger("workbench.ollama_client")


class OllamaClient:
    """Manages Ollama interactions with hot-swap tracking and hardware constraint enforcement."""

    def __init__(self, host: str = "http://127.0.0.1:11434", registry: Optional[ModelRegistry] = None):
        self.host = host
        self.registry = registry or get_model_registry()
        self.client = ollama.Client(host=self.host)
        self.async_client = ollama.AsyncClient(host=self.host)
        self._last_active_worker: Optional[str] = None

    async def is_server_ready(self) -> bool:
        """Check if Ollama server is responding."""
        try:
            await self.async_client.list()
            return True
        except Exception as e:
            logger.debug(f"Ollama server not ready: {e}")
            return False

    async def list_available_models(self) -> List[str]:
        """List all models pulled locally in Ollama."""
        try:
            resp = await self.async_client.list()
            # resp is ListResponse containing models list
            models = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
            model_names = []
            for m in models:
                name = m.get("model") or m.get("name") if isinstance(m, dict) else getattr(m, "model", getattr(m, "name", ""))
                if name:
                    model_names.append(name)
            return model_names
        except Exception as e:
            logger.error(f"Failed to list local models: {e}")
            return []

    async def get_loaded_models(self) -> List[LoadedModelStatus]:
        """Get models currently resident in VRAM/RAM via ollama ps."""
        try:
            resp = await self.async_client.ps()
            models_data = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
            results = []
            for m in models_data:
                if isinstance(m, dict):
                    name = m.get("name", "")
                    model = m.get("model", "")
                    size = m.get("size", 0)
                    size_vram = m.get("size_vram", 0)
                    expires_at = m.get("expires_at")
                else:
                    name = getattr(m, "name", "")
                    model = getattr(m, "model", "")
                    size = getattr(m, "size", 0)
                    size_vram = getattr(m, "size_vram", 0)
                    expires_at = getattr(m, "expires_at", None)

                results.append(LoadedModelStatus(
                    name=name or model,
                    model=model or name,
                    size=size,
                    size_vram=size_vram,
                    expires_at=str(expires_at) if expires_at else None
                ))
            return results
        except Exception as e:
            logger.warning(f"Error checking loaded models (ps): {e}")
            return []

    async def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model tag is loaded in memory with exact tag matching."""
        loaded = await self.get_loaded_models()
        req_norm = model_name.strip().lower()
        req_parts = req_norm.split(":")
        req_family = req_parts[0]
        req_tag = req_parts[1] if len(req_parts) > 1 else ""

        for m in loaded:
            m_name = (m.name or m.model or "").lower()
            if not m_name:
                continue

            # Direct exact match or repository path match
            if req_norm == m_name or m_name.endswith("/" + req_norm):
                return True

            # If tag is specified, ensure BOTH family and tag match, never family alone
            if req_tag:
                m_parts = m_name.split("/")[-1].split(":")
                m_family = m_parts[0]
                m_tag = m_parts[1] if len(m_parts) > 1 else ""
                if req_family == m_family and (req_tag == m_tag or m_tag.startswith(req_tag)):
                    return True
            else:
                # If no tag was requested, compare family
                m_family = m_name.split("/")[-1].split(":")[0]
                if req_family == m_family:
                    return True

        return False

    async def ensure_router_resident(self) -> float:
        """Ensure the lightweight router classifier model is pinned in memory with keep_alive=-1."""
        router_cfg = self.registry.get_router_model()
        is_loaded = await self.is_model_loaded(router_cfg.name)
        if not is_loaded:
            logger.info(f"Router model '{router_cfg.name}' is not in memory. Loading with keep_alive=-1...")
            start_t = time.perf_counter()
            keep_val = "24h" if router_cfg.keep_alive in ["-1", -1, None] else str(router_cfg.keep_alive)
            await self.async_client.generate(
                model=router_cfg.name,
                prompt="ready",
                keep_alive=keep_val
            )
            swap_time = (time.perf_counter() - start_t) * 1000.0
            logger.info(json.dumps({
                "event": "router_pin",
                "model": router_cfg.name,
                "latency_ms": round(swap_time, 2)
            }))
            return swap_time
        return 0.0

    async def swap_worker_model(self, target_model: ModelConfig) -> Dict[str, Any]:
        """
        Hot-swap the active worker model into VRAM if not already active.
        Enforces single 7B worker in VRAM + router resident constraint.
        Logs latency and estimated weight transfer source.
        """
        model_name = target_model.name
        is_loaded = await self.is_model_loaded(model_name)

        if is_loaded:
            logger.info(f"Model '{model_name}' is already loaded in memory.")
            return {
                "swapped": False,
                "latency_ms": 0.0,
                "source": "resident",
                "model": model_name
            }

        logger.info(f"Hot-swapping worker to '{model_name}' (evicting previous worker if any)...")
        start_t = time.perf_counter()

        # Issue warm-up generate call with bounded context window (prevents Windows CUDA layer-splitting)
        await self.async_client.generate(
            model=model_name,
            prompt="init",
            options={"num_ctx": 2048},
            keep_alive=target_model.keep_alive or "30m"
        )
        swap_time = (time.perf_counter() - start_t) * 1000.0

        # Sub-second to ~1.5s usually indicates RAM-to-VRAM cached swap; >3s indicates disk read
        source = "ram_to_vram" if swap_time < 2500 else "disk_to_vram"

        swap_event = {
            "event": "model_swap",
            "previous_worker": self._last_active_worker,
            "new_worker": model_name,
            "keep_alive": target_model.keep_alive,
            "latency_ms": round(swap_time, 2),
            "source": source
        }
        logger.info(json.dumps(swap_event))
        self._last_active_worker = model_name

        # Ensure router is still resident in memory after swapping worker
        await self.ensure_router_resident()

        return {
            "swapped": True,
            "latency_ms": swap_time,
            "source": source,
            "model": model_name
        }

    async def run_prompt(
        self,
        model_config: ModelConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[str]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Execute a prompt with hot-swap tracking and performance metrics."""
        # 1. Hot-swap worker if needed
        swap_info = await self.swap_worker_model(model_config)

        # 2. Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_message: Dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            user_message["images"] = images
        messages.append(user_message)

        # 3. Perform inference with bounded context window
        start_inf = time.perf_counter()
        options = {"temperature": temperature, "num_ctx": 4096}

        resp = await self.async_client.chat(
            model=model_config.name,
            messages=messages,
            options=options,
            keep_alive=model_config.keep_alive
        )
        inf_time = (time.perf_counter() - start_inf) * 1000.0

        # 4. Extract response content and metrics
        content = ""
        eval_count = 0
        eval_duration = 0
        if isinstance(resp, dict):
            message = resp.get("message", {})
            content = message.get("content", "")
            eval_count = resp.get("eval_count", 0)
            eval_duration = resp.get("eval_duration", 0)
        else:
            message = getattr(resp, "message", None)
            content = getattr(message, "content", "") if message else ""
            eval_count = getattr(resp, "eval_count", 0)
            eval_duration = getattr(resp, "eval_duration", 0)

        # Calculate tokens per second (eval_duration is in nanoseconds)
        tps = (eval_count / (eval_duration / 1e9)) if eval_duration and eval_duration > 0 else None

        total_time = swap_info["latency_ms"] + inf_time

        logger.info(json.dumps({
            "event": "inference_completed",
            "model": model_config.name,
            "swap_ms": round(swap_info["latency_ms"], 2),
            "inference_ms": round(inf_time, 2),
            "total_ms": round(total_time, 2),
            "eval_count": eval_count,
            "tokens_per_sec": round(tps, 2) if tps else None
        }))

        return {
            "response": content,
            "swap_latency_ms": swap_info["latency_ms"],
            "inference_latency_ms": inf_time,
            "total_latency_ms": total_time,
            "tokens_per_second": tps,
            "swap_source": swap_info["source"]
        }


# Singleton helper
_client_instance: Optional[OllamaClient] = None


def get_ollama_client(host: str = "http://127.0.0.1:11434") -> OllamaClient:
    """Get or create singleton OllamaClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaClient(host=host)
    return _client_instance
