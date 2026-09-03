"""RAG Knowledge Base package with CPU-only embeddings and persistent vector indexing."""

from workbench.rag.embeddings import CPUEmbeddingFunction, get_embedding_function
from workbench.rag.knowledge_base import LocalKnowledgeBase, get_knowledge_base

__all__ = [
    "CPUEmbeddingFunction",
    "get_embedding_function",
    "LocalKnowledgeBase",
    "get_knowledge_base",
]
