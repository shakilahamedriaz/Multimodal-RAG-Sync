import asyncio
import logging
from typing import ClassVar

logger = logging.getLogger(__name__)

# Dimensions for well-known models
_KNOWN_DIMS: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
    "intfloat/e5-large-v2": 1024,
    "intfloat/e5-base-v2": 768,
}


class SentenceTransformerEmbedder:
    """Local embedding using sentence-transformers models.

    ⚠ Dimension compatibility: The default Chunk.embedding column is Vector(1536).
    Sentence-transformer models produce 384–1024 dims. Before using a local model
    as the KB's embedding_model, run:
        python backend/migrations/001_change_vector_dim.py --dim <N>
    to update the DB column and HNSW index to the matching dimension.
    """

    _cache: ClassVar[dict] = {}

    def __init__(self, model: str = "BAAI/bge-large-en-v1.5") -> None:
        self.model = model

    @property
    def dimensions(self) -> int:
        return _KNOWN_DIMS.get(self.model, 768)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return embeddings.tolist()

    def _get_model(self):
        if self.model not in self._cache:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer model: %s", self.model)
            self._cache[self.model] = SentenceTransformer(self.model)
            logger.info("Model loaded: %s (%d dims)", self.model, self.dimensions)
        return self._cache[self.model]
