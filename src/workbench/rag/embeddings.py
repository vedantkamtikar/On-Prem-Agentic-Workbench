"""CPU-Only Embedding Function for RAG Vector Indexing."""

import logging
import os
import time
from typing import Any, List, Optional, Union
import numpy as np
import torch

# Force strict offline mode before loading Hugging Face models
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger("workbench.rag.embeddings")


class CPUEmbeddingFunction:
    """
    Computes dense vector representations strictly on CPU.
    Guarantees zero GPU VRAM consumption to preserve GPU capacity for LLM serving.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy load model on CPU in offline mode."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            try:
                # Explicit device='cpu' enforcement with local_files_only=True
                self._model = SentenceTransformer(self.model_name, device="cpu", local_files_only=True)
            except Exception:
                # Fallback to standard CPU load if local_files_only parameter is not supported
                self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Generate normalized vector embeddings on CPU."""
        if isinstance(texts, str):
            texts = [texts]

        model = self._get_model()
        embs = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            device="cpu"
        )
        return embs

    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB compatible callable interface."""
        embs = self.encode(input)
        return embs.tolist()


# Singleton
_embedding_instance: Optional[CPUEmbeddingFunction] = None


def get_embedding_function() -> CPUEmbeddingFunction:
    """Get or create singleton CPUEmbeddingFunction."""
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = CPUEmbeddingFunction()
    return _embedding_instance
