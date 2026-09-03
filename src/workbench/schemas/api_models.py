"""Pydantic request and response schemas for Workbench API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or user instruction")
    task_type: Optional[str] = Field(None, description="Explicit task type hint (e.g., 'drafting', 'coding', 'vision')")
    task_hint: Optional[str] = Field(None, description="Optional user task hint alias")
    images: Optional[List[str]] = Field(default=None, description="Base64-encoded images for multimodal reasoning")
    system_prompt: Optional[str] = Field(default=None, description="Optional custom system prompt")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    stream: bool = Field(default=False, description="Whether to stream token responses")


class AgentRunResponse(BaseModel):
    response: str = Field(..., description="Generated text output")
    model_used: str = Field(..., description="Ollama model tag actually used (e.g., 'qwen3.5:4b')")
    model_key: str = Field(..., description="Registry key of the model (e.g., 'general', 'coding', 'router')")
    task_type_detected: str = Field(..., description="Detected or matched task category")
    swap_latency_ms: float = Field(default=0.0, description="Time spent swapping/loading model weights in milliseconds")
    inference_latency_ms: float = Field(default=0.0, description="Inference execution time in milliseconds")
    total_latency_ms: float = Field(default=0.0, description="Total end-to-end request latency in milliseconds")
    tokens_per_second: Optional[float] = Field(default=None, description="Generation speed (eval tokens / eval duration)")
    swap_source: Optional[str] = Field(default="resident", description="Weight transfer source: 'resident', 'ram_to_vram', 'disk_to_vram'")


class ModelInfo(BaseModel):
    key: str
    name: str
    role: str
    context_window: int
    modality: List[str]
    keep_alive: str
    task_types: List[str] = Field(default_factory=list)
    description: str


class LoadedModelStatus(BaseModel):
    name: str
    model: str
    size: int
    size_vram: int
    expires_at: Optional[str] = None


class RegistryStatusResponse(BaseModel):
    models: List[ModelInfo]
    loaded_in_memory: List[LoadedModelStatus]
    default_fallback: str
