"""Memory-backed tools for agents to store and retrieve context."""

from __future__ import annotations

import uuid
from typing import Any

# Lazy init to avoid import errors when chromadb is not installed
_store = None


def _get_store():
    global _store
    if _store is None:
        from src.memory.store import MemoryStore
        _store = MemoryStore()
    return _store


def search_memory(query: str, n_results: int = 3) -> str:
    """Search past conversations and code snippets for relevant context.

    Args:
        query: Natural language description of what you're looking for.
        n_results: Number of results to return (default 3).

    Returns:
        Formatted string of relevant past context.
    """
    try:
        store = _get_store()
        conv_results = store.search_conversations(query, n_results=n_results)
        code_results = store.search_code(query, n_results=n_results)

        parts: list[str] = []
        if conv_results:
            parts.append("=== Relevant Conversations ===")
            for r in conv_results:
                parts.append(f"[{r['metadata'].get('agent', 'unknown')}] {r['content'][:500]}")

        if code_results:
            parts.append("\n=== Relevant Code ===")
            for r in code_results:
                parts.append(f"[{r['metadata'].get('filename', 'unknown')}]\n{r['content'][:800]}")

        return "\n".join(parts) if parts else "No relevant context found in memory."
    except Exception as e:
        return f"Memory search unavailable: {e}"


def save_to_memory(content: str, category: str = "conversation", metadata_str: str = "") -> str:
    """Save important context to memory for future retrieval.

    Args:
        content: The content to save.
        category: Either 'conversation' or 'code'.
        metadata_str: Optional comma-separated key=value pairs, e.g. 'agent=coder,filename=main.py'

    Returns:
        Confirmation message.
    """
    try:
        store = _get_store()
        doc_id = str(uuid.uuid4())
        meta: dict[str, Any] = {}
        if metadata_str:
            for pair in metadata_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    meta[k.strip()] = v.strip()

        if category == "code":
            store.add_code_snippet(doc_id, content, meta)
        else:
            store.add_conversation(doc_id, content, meta)

        return f"Saved to memory (id={doc_id[:8]}, category={category})."
    except Exception as e:
        return f"Memory save failed: {e}"
