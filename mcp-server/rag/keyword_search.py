"""
mcp-server/rag/keyword_search.py

Minimal BM25 keyword-search index backing the search_policy tool.

Same shape as a vector store -- upsert() to add a chunk, query() to
search -- but ranking is done by term overlap (BM25) instead of
embeddings. No embedding model, no API key, nothing external to run
besides `pip install rank_bm25`. Trade-off: it won't know that
"confirmation" and "elicitation" mean the same thing here, but it's
zero-config and easy to debug.
"""

import re
from rank_bm25 import BM25Plus


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KeywordStore:
    """A tiny in-memory keyword index: upsert() chunks, query() for the
    best-matching ones. Kept in memory, same as the RAG task allows."""

    def __init__(self):
        self.rows: list[dict] = []  # [{"text": ..., "metadata": {...}}, ...]
        self._bm25 = None
        self._dirty = True

    def upsert(self, text: str, metadata: dict | None = None) -> None:
        self.rows.append({"text": text, "metadata": metadata or {}})
        self._dirty = True

    def _rebuild_index(self) -> None:
        corpus = [_tokenize(r["text"]) for r in self.rows]
        self._bm25 = BM25Plus(corpus) if corpus else None
        self._dirty = False

    def query(self, query_text: str, top_k: int = 3) -> list[dict]:
        if not self.rows:
            return []

        if self._dirty:
            self._rebuild_index()
        if self._bm25 is None:
            return []

        tokens = _tokenize(query_text)
        scores = self._bm25.get_scores(tokens)

        # Only return chunks that actually share a keyword with the query --
        # BM25 alone will still rank *every* chunk, even ones with zero overlap.
        overlapping = [
            i for i in range(len(self.rows))
            if set(tokens) & set(_tokenize(self.rows[i]["text"]))
        ]
        ranked = sorted(overlapping, key=lambda i: scores[i], reverse=True)
        return [self.rows[i] for i in ranked[:top_k]]
