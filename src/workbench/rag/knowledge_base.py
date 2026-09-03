"""Persistent Local RAG Knowledge Base with CPU Embeddings and Cosine Similarity Index."""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pypdf
from workbench.rag.embeddings import CPUEmbeddingFunction, get_embedding_function
WORKSPACE_ROOT = Path(os.getenv("WORKBENCH_WORKSPACE_ROOT", os.getcwd())).resolve()

logger = logging.getLogger("workbench.rag.kb")


class LocalKnowledgeBase:
    """
    Air-gapped, CPU-only local vector index for industrial SOPs, technical manuals, and specs.
    Provides semantic search with document citations.
    """

    def __init__(
        self,
        kb_dir: Optional[str] = None,
        index_file: Optional[str] = None,
        embedding_fn: Optional[CPUEmbeddingFunction] = None
    ):
        self.kb_dir = Path(kb_dir or (WORKSPACE_ROOT / "data" / "kb"))
        self.index_file = Path(index_file or (WORKSPACE_ROOT / "data" / "kb_index.json"))
        self.embedding_fn = embedding_fn or get_embedding_function()
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None
        self._load_index()

    def _chunk_text(self, text: str, source_file: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        """Split document into overlapping semantic chunks with metadata."""
        chunks = []
        # Split by section headers or double newlines first
        sections = re.split(r"\n(?=#{1,3}\s|\d+\.\s+[A-Z])", text)

        for sec_idx, sec in enumerate(sections):
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            if len(sec_clean) <= chunk_size:
                chunks.append({
                    "id": f"{source_file}_sec_{sec_idx}",
                    "source": source_file,
                    "text": sec_clean,
                    "char_count": len(sec_clean)
                })
            else:
                # Sub-chunk long sections
                start = 0
                sub_idx = 0
                while start < len(sec_clean):
                    end = min(start + chunk_size, len(sec_clean))
                    sub_text = sec_clean[start:end].strip()
                    if sub_text:
                        chunks.append({
                            "id": f"{source_file}_sec_{sec_idx}_sub_{sub_idx}",
                            "source": source_file,
                            "text": sub_text,
                            "char_count": len(sub_text)
                        })
                    start += (chunk_size - overlap)
                    sub_idx += 1

        return chunks

    def ingest_documents(self) -> int:
        """Scan kb_dir, parse text from Markdown/TXT/PDF, generate CPU embeddings, and save index."""
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        all_chunks = []

        doc_files = list(self.kb_dir.glob("*.md")) + list(self.kb_dir.glob("*.txt")) + list(self.kb_dir.glob("*.pdf"))
        logger.info(f"Found {len(doc_files)} document(s) in '{self.kb_dir}' for ingestion.")

        for doc_path in doc_files:
            try:
                if doc_path.suffix.lower() == ".pdf":
                    reader = pypdf.PdfReader(str(doc_path))
                    raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
                else:
                    with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
                        raw_text = f.read()

                doc_chunks = self._chunk_text(raw_text, source_file=doc_path.name)
                all_chunks.extend(doc_chunks)
                logger.info(f"Ingested '{doc_path.name}': created {len(doc_chunks)} chunks.")
            except Exception as e:
                logger.error(f"Error ingesting document '{doc_path.name}': {e}")

        if not all_chunks:
            logger.warning("No document chunks created during ingestion.")
            return 0

        # Compute embeddings on CPU
        texts = [c["text"] for c in all_chunks]
        embs = self.embedding_fn.encode(texts)

        # Save to persistent JSON index
        self.chunks = all_chunks
        self.vectors = embs

        index_payload = {
            "version": "1.0",
            "chunk_count": len(all_chunks),
            "chunks": all_chunks,
            "vectors": embs.tolist()
        }

        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index_payload, f)

        logger.info(f"Knowledge Base index successfully built and saved to '{self.index_file}' ({len(all_chunks)} chunks).")
        return len(all_chunks)

    def _load_index(self):
        """Load cached index from disk if present."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = data.get("chunks", [])
                vectors_list = data.get("vectors", [])
                if vectors_list:
                    self.vectors = np.array(vectors_list, dtype=np.float32)
                logger.info(f"Loaded existing KB index with {len(self.chunks)} chunks from '{self.index_file}'.")
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents present in data/kb directory with metadata."""
        if not self.kb_dir.exists():
            return []
        doc_files = list(self.kb_dir.glob("*.md")) + list(self.kb_dir.glob("*.txt")) + list(self.kb_dir.glob("*.pdf"))
        docs = []
        for df in doc_files:
            docs.append({
                "filename": df.name,
                "size_kb": round(df.stat().st_size / 1024, 1),
                "type": df.suffix.upper().replace(".", ""),
                "chunks": sum(1 for c in self.chunks if c.get("source") == df.name)
            })
        return docs

    def reindex(self) -> int:
        """Force re-ingestion and vectorization of data/kb/ documents."""
        self.chunks = []
        self.vectors = None
        return self.ingest_documents()

    def _get_kb_mtime_hash(self) -> str:
        """Compute quick signature of files in kb_dir to detect changes."""
        if not self.kb_dir.exists():
            return ""
        doc_files = sorted(list(self.kb_dir.glob("*.md")) + list(self.kb_dir.glob("*.txt")) + list(self.kb_dir.glob("*.pdf")))
        sig_parts = [f"{f.name}:{f.stat().st_mtime}:{f.stat().st_size}" for f in doc_files]
        return ";".join(sig_parts)

    def _is_index_stale(self) -> bool:
        """Check if documents on disk have changed compared to loaded index."""
        current_sig = self._get_kb_mtime_hash()
        indexed_sources = set(c.get("source") for c in self.chunks)
        disk_sources = set(f.name for f in (list(self.kb_dir.glob("*.md")) + list(self.kb_dir.glob("*.txt")) + list(self.kb_dir.glob("*.pdf"))))
        return indexed_sources != disk_sources

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Query vector index using cosine similarity on CPU and return top_k grounded excerpts.
        Automatically syncs index if new documents are detected.
        """
        if self.vectors is None or len(self.chunks) == 0 or self._is_index_stale():
            # Attempt automatic ingestion
            self.ingest_documents()

        if self.vectors is None or len(self.chunks) == 0:
            return []

        # Encode query on CPU
        query_vec = self.embedding_fn.encode(query_text)[0]

        # Cosine similarity (vectors are L2-normalized)
        sims = np.dot(self.vectors, query_vec)

        # Get top-k indices
        top_indices = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(sims[idx])
            chunk = self.chunks[idx]
            results.append({
                "source": chunk["source"],
                "text": chunk["text"],
                "score": round(score, 4),
                "id": chunk["id"]
            })

        return results


# Singleton
_kb_instance: Optional[LocalKnowledgeBase] = None


def get_knowledge_base() -> LocalKnowledgeBase:
    """Get or create singleton LocalKnowledgeBase."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = LocalKnowledgeBase()
    return _kb_instance
