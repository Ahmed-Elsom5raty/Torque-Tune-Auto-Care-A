"""
mcp-server/rag/vector_store.py

Step 2b of the RAG pipeline: a real vector database, not a list of floats
in a Python dict. Three components, matching the lecture's "Vector
Databases" slide:

    1. Vector Index    -> hnswlib.Index (HNSW, real ANN search)
    2. Metadata Store   -> self._payloads  (chunk text + metadata, keyed by id)
    3. Metadata Index   -> self._metadata_index (inverted index: field value
                            -> set of internal ids), used to PRE-filter the
                            candidate set before similarity search runs, not
                            just to filter the results afterwards.

Why filtering matters here: a question like "what's the warranty on this
CV joint" only needs doc_type == "warranty" chunks searched, and a
question naming an exact bulletin should be restricted to chunks whose
`identifiers` contain that code. Restricting the candidate set first is
what makes hybrid search's exact-identifier matching (see hybrid_rag.py)
cheap and precise instead of relying on embedding luck.
"""

from dataclasses import dataclass

import hnswlib
import numpy as np

from chunking import Chunk
from embeddings import Embedder


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float  # cosine similarity, higher = more similar


class VectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        # cosine space: hnswlib returns *distance* = 1 - cosine_similarity
        self._index = hnswlib.Index(space="cosine", dim=dim)
        self._index.init_index(max_elements=1000, ef_construction=200, M=16)
        self._index.set_ef(50)

        self._next_id = 0
        self._payloads: dict[int, Chunk] = {}          # Metadata (payload) store
        self._metadata_index: dict[str, set[int]] = {}  # field:value -> {ids}

    # ---- indexing -------------------------------------------------
    def upsert(self, chunk: Chunk, vector: np.ndarray) -> int:
        internal_id = self._next_id
        self._next_id += 1

        self._index.add_items(vector.reshape(1, -1), np.array([internal_id]))
        self._payloads[internal_id] = chunk

        # Build the metadata index: one entry per filterable field/value.
        self._add_to_metadata_index("doc_type", chunk.doc_type, internal_id)
        self._add_to_metadata_index("source", chunk.source, internal_id)
        for ident in chunk.identifiers:
            self._add_to_metadata_index("identifier", ident, internal_id)

        return internal_id

    def _add_to_metadata_index(self, field: str, value: str, internal_id: int) -> None:
        key = f"{field}:{value}"
        self._metadata_index.setdefault(key, set()).add(internal_id)

    # ---- candidate pre-filtering -----------------------------------
    def _filtered_candidate_ids(self, filters: dict[str, str] | None) -> set[int] | None:
        """Returns None if no filter (search everything), else the set of
        internal ids matching ALL given filters -- computed purely from
        the metadata index, before any vector math happens."""
        if not filters:
            return None
        candidate_sets = []
        for field, value in filters.items():
            key = f"{field}:{value}"
            candidate_sets.append(self._metadata_index.get(key, set()))
        if not candidate_sets:
            return set()
        result = candidate_sets[0]
        for s in candidate_sets[1:]:
            result = result & s
        return result

    # ---- querying ---------------------------------------------------
    def query(
        self,
        query_vector: np.ndarray,
        top_k: int = 3,
        filters: dict[str, str] | None = None,
    ) -> list[ScoredChunk]:
        candidate_ids = self._filtered_candidate_ids(filters)

        if candidate_ids is not None:
            # Metadata-filtered path: candidate set is already restricted
            # by the metadata index, so we score only those (brute-force
            # cosine over a small candidate set is exact and still cheap --
            # this *is* the "filter before/during search" the assignment
            # asks for, versus running ANN over everything then discarding).
            if not candidate_ids:
                return []
            ids = sorted(candidate_ids)
            vectors = np.stack([self._get_vector(i) for i in ids])
            sims = vectors @ query_vector  # both L2-normalized -> cosine sim
            ranked = sorted(zip(ids, sims), key=lambda x: x[1], reverse=True)[:top_k]
            return [ScoredChunk(self._payloads[i], float(s)) for i, s in ranked]

        # Unfiltered path: real ANN search over the whole HNSW index.
        k = min(top_k, self._next_id) or 1
        labels, distances = self._index.knn_query(query_vector.reshape(1, -1), k=k)
        results = []
        for label, dist in zip(labels[0], distances[0]):
            similarity = 1.0 - float(dist)
            results.append(ScoredChunk(self._payloads[int(label)], similarity))
        return results

    def _get_vector(self, internal_id: int) -> np.ndarray:
        return np.array(self._index.get_items([internal_id])[0])


def build_vector_store(chunks: list[Chunk]) -> tuple[VectorStore, Embedder]:
    embedder = Embedder()
    embedder.fit([c.text for c in chunks])
    vectors = embedder.embed([c.text for c in chunks])

    store = VectorStore(dim=embedder.dim)
    for chunk, vector in zip(chunks, vectors):
        store.upsert(chunk, vector)
    return store, embedder


if __name__ == "__main__":
    from chunking import load_chunks

    all_chunks = load_chunks()
    store, embedder = build_vector_store(all_chunks)

    print("--- Unfiltered ANN search ---")
    q = "is my alternator still under warranty"
    qvec = embedder.embed([q])[0]
    for r in store.query(qvec, top_k=3):
        print(f"  {r.score:.3f}  [{r.chunk.doc_type}] {r.chunk.section}")

    print("\n--- Metadata-filtered search (doc_type=warranty only) ---")
    for r in store.query(qvec, top_k=3, filters={"doc_type": "warranty"}):
        print(f"  {r.score:.3f}  [{r.chunk.doc_type}] {r.chunk.section}")

    print("\n--- Metadata-filtered search (exact identifier=TSB-2024-118) ---")
    q2 = "clutch pedal soft after install"
    qvec2 = embedder.embed([q2])[0]
    for r in store.query(qvec2, top_k=3, filters={"identifier": "TSB-2024-118"}):
        print(f"  {r.score:.3f}  [{r.chunk.doc_type}] {r.chunk.section}")
