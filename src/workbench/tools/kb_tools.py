"""Knowledge base retrieval tools for industrial manuals and SOPs."""

from typing import Any, Dict, List
from workbench.rag.knowledge_base import get_knowledge_base
from workbench.tools.base import ToolDefinition


def search_kb(query: str, top_k: int = 3) -> str:
    """
    Search local knowledge base SOPs, manuals, and technical reports for relevant procedures and specs.
    Returns grounded context with source file citations.
    """
    kb = get_knowledge_base()
    results = kb.query(query_text=query, top_k=top_k)

    if not results:
        return f"No matching documents found in Knowledge Base for query: '{query}'."

    formatted = []
    formatted.append(f"Retrieved {len(results)} grounded excerpt(s) from Local Knowledge Base:")
    for i, r in enumerate(results, start=1):
        formatted.append(
            f"[{i}] SOURCE: '{r['source']}' (Relevance Score: {r['score']:.3f})\n"
            f"EXCERPT:\n{r['text']}\n"
        )

    return "\n".join(formatted)


KB_TOOLS = [
    ToolDefinition(
        name="search_kb",
        description="Search local knowledge base SOPs, technical manuals, and OEM specifications for grounded procedures and standards.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or question to retrieve context for"},
                "top_k": {"type": "integer", "description": "Number of relevant chunks to retrieve", "default": 3}
            },
            "required": ["query"]
        },
        func=search_kb
    )
]
