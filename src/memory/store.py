"""ChromaDB-backed memory store for agent context retrieval (RAG)."""

from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

# Default collection names
CONVERSATIONS_COLLECTION = "conversations"
CODE_SNIPPETS_COLLECTION = "code_snippets"


class MemoryStore:
    """Vector store for persisting and retrieving agent conversation history and code."""

    def __init__(self, persist_dir: str = "./data/chromadb") -> None:
        self._client = chromadb.Client(
            ChromaSettings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
                is_persistent=True,
            )
        )
        self._conversations = self._client.get_or_create_collection(
            name=CONVERSATIONS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._code_snippets = self._client.get_or_create_collection(
            name=CODE_SNIPPETS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("MemoryStore initialized (persist_dir=%s)", persist_dir)

    def add_conversation(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a conversation turn."""
        meta = metadata or {}
        self._conversations.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[meta],
        )

    def add_code_snippet(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a code snippet for later retrieval."""
        meta = metadata or {}
        self._code_snippets.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[meta],
        )

    def search_conversations(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over conversation history."""
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where
        results = self._conversations.query(**kwargs)
        return self._format_results(results)

    def search_code(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over code snippets."""
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where
        results = self._code_snippets.query(**kwargs)
        return self._format_results(results)

    @staticmethod
    def _format_results(results: dict) -> list[dict[str, Any]]:
        """Convert ChromaDB query results to a flat list of dicts."""
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]
        return [
            {
                "id": ids[i],
                "content": docs[i],
                "metadata": metas[i] if metas else {},
                "distance": distances[i] if distances else None,
            }
            for i in range(len(docs))
        ]

    def clear(self) -> None:
        """Delete all collections (useful for testing)."""
        self._client.delete_collection(CONVERSATIONS_COLLECTION)
        self._client.delete_collection(CODE_SNIPPETS_COLLECTION)
        self._conversations = self._client.get_or_create_collection(
            name=CONVERSATIONS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._code_snippets = self._client.get_or_create_collection(
            name=CODE_SNIPPETS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
