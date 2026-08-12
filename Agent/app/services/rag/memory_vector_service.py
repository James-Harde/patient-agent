# 作者：小红书@人间清醒的李某人
"""FAISS-based vector storage for memory events.

Uses ``llm_env`` for all embedding configuration.  The index engine is
still FAISS (IndexFlatIP) — Milvus migration is planned but not active.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.db.models import MemoryEvent
from app.db.session import DATA_DIR
from app.llm import llm_env
from openai import OpenAI

VECTOR_DIR = DATA_DIR / "faiss"
MAX_BATCH_SIZE = 10

try:
    import faiss
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency
    faiss = None
    np = None

logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def is_available() -> bool:
    return faiss is not None and np is not None


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------


def replace_memory_events(
    patient_id: int,
    events: list[MemoryEvent],
    source_types: Optional[list[str]] = None,
) -> None:
    if not is_available():
        logger.info("FAISS unavailable, skip vector write for patient_id=%s", patient_id)
        return

    VECTOR_DIR.mkdir(exist_ok=True)
    metadata = _load_metadata(patient_id)
    embedding_dimensions = llm_env.get_embedding_dimensions()
    logger.info(
        "Writing memory event vectors for patient_id=%s source_types=%s event_count=%s dir=%s model=%s dimensions=%s",
        patient_id,
        source_types or ["all"],
        len(events),
        VECTOR_DIR,
        llm_env.get_embedding_model(),
        embedding_dimensions,
    )
    if source_types:
        metadata = [item for item in metadata if item["source_type"] not in source_types]
    else:
        metadata = []

    for event in events:
        metadata.append(
            {
                "event_id": event.id,
                "patient_id": event.patient_id,
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat(),
                "source_type": event.source_type,
                "source_id": event.source_id or "",
                "document": _build_event_document(event),
            }
        )

    _save_metadata(patient_id, metadata)
    _rebuild_index(
        patient_id=patient_id,
        metadata=metadata,
        embeddings=_embed_documents([item["document"] for item in metadata]),
        embedding_dimensions=embedding_dimensions,
    )
    logger.info(
        "Memory event vectors written for patient_id=%s index=%s metadata=%s total_vectors=%s",
        patient_id,
        _index_path(patient_id),
        _metadata_path(patient_id),
        len(metadata),
    )


# ---------------------------------------------------------------------------
# Read / search path
# ---------------------------------------------------------------------------


def search_memory_events(
    patient_id: int,
    query: str,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    if not is_available():
        logger.info("FAISS unavailable, skip vector search for patient_id=%s", patient_id)
        return []
    if not query.strip():
        return []

    metadata = _load_metadata(patient_id)
    if not metadata:
        logger.info("No vector metadata found for patient_id=%s", patient_id)
        return []

    embedding_dimensions = llm_env.get_embedding_dimensions()
    index_path = _index_path(patient_id)
    if not index_path.exists():
        _rebuild_index(
            patient_id=patient_id,
            metadata=metadata,
            embeddings=_embed_documents([item["document"] for item in metadata]),
            embedding_dimensions=embedding_dimensions,
        )
        logger.info("Rebuilt missing FAISS index for patient_id=%s at %s", patient_id, index_path)

    index = faiss.read_index(str(index_path))
    if index.d != embedding_dimensions:
        _rebuild_index(
            patient_id=patient_id,
            metadata=metadata,
            embeddings=_embed_documents([item["document"] for item in metadata]),
            embedding_dimensions=embedding_dimensions,
        )
        index = faiss.read_index(str(index_path))
        logger.info(
            "Rebuilt FAISS index for patient_id=%s due to dimension change, new_dimensions=%s",
            patient_id,
            embedding_dimensions,
        )

    query_vector = np.array([_embed_query(query)], dtype="float32")
    scores, positions = index.search(query_vector, max(top_n, 1))

    rows: list[dict[str, Any]] = []
    for score, position in zip(scores[0], positions[0]):
        if position < 0 or position >= len(metadata):
            continue
        item = metadata[int(position)]
        rows.append(
            {
                "event_id": int(item["event_id"]),
                "vector_score": float(score),
            }
        )
    logger.info(
        "Vector search complete for patient_id=%s query=%r top_n=%s hit_count=%s",
        patient_id,
        query,
        top_n,
        len(rows),
    )
    return rows


# ---------------------------------------------------------------------------
# Internal: index & metadata I/O
# ---------------------------------------------------------------------------


def _rebuild_index(
    patient_id: int,
    metadata: list[dict[str, Any]],
    embeddings: list[list[float]],
    embedding_dimensions: int,
) -> None:
    index = faiss.IndexFlatIP(embedding_dimensions)
    if metadata:
        matrix = np.array(embeddings, dtype="float32")
        index.add(matrix)
    faiss.write_index(index, str(_index_path(patient_id)))


def _metadata_path(patient_id: int) -> Path:
    return VECTOR_DIR / f"patient_{patient_id}.json"


def _index_path(patient_id: int) -> Path:
    return VECTOR_DIR / f"patient_{patient_id}.index"


def _load_metadata(patient_id: int) -> list[dict[str, Any]]:
    path = _metadata_path(patient_id)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_metadata(patient_id: int, metadata: list[dict[str, Any]]) -> None:
    _metadata_path(patient_id).write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Internal: document building & embedding
# ---------------------------------------------------------------------------


def _build_event_document(event: MemoryEvent) -> str:
    parts = [
        event.event_type,
        event.title,
        event.summary or "",
        event.source_type,
    ]
    return "\n".join(part for part in parts if part)


def _embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _embedding_client()
    embeddings: list[list[float]] = []
    model = llm_env.get_embedding_model()
    dimensions = llm_env.get_embedding_dimensions()
    for start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[start : start + MAX_BATCH_SIZE]
        logger.info(
            "Requesting embeddings batch_size=%s model=%s dimensions=%s",
            len(batch),
            model,
            dimensions,
        )
        response = client.embeddings.create(
            model=model,
            input=batch,
            dimensions=dimensions,
        )
        embeddings.extend(_normalize_embedding(item.embedding) for item in response.data)
    return embeddings


def _embed_query(text: str) -> list[float]:
    return _embed_documents([text])[0]


def _normalize_embedding(embedding: list[float]) -> list[float]:
    vector = np.array(embedding, dtype="float32")
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


# ---------------------------------------------------------------------------
# Internal: OpenAI-compatible embedding client
# ---------------------------------------------------------------------------


def _embedding_client() -> OpenAI:
    return OpenAI(
        api_key=llm_env.get_embedding_api_key(),
        base_url=llm_env.get_embedding_base_url(),
    )
