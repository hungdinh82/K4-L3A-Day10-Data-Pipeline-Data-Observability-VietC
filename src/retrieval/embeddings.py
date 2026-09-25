from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import re
from typing import Any

from langchain_core.embeddings import Embeddings

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised only in minimal environments
    SentenceTransformer = None  # type: ignore[assignment,misc]


_FALLBACK_DIMENSION = 384


class _HashEmbeddingModel:
    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * _FALLBACK_DIMENSION
            for token in re.findall(r"\w+", text.lower()):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                index = int.from_bytes(digest[:4], "big") % _FALLBACK_DIMENSION
                vector[index] += 1.0 if digest[4] % 2 else -1.0
            if normalize_embeddings:
                norm = math.sqrt(sum(value * value for value in vector))
                if norm:
                    vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> Any:
    if SentenceTransformer is None:
        return _HashEmbeddingModel()
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        vector = embedding[0]
        return vector.tolist() if hasattr(vector, "tolist") else vector
