import asyncio
import logging
from typing import Union

from app.schemas import ChunkResult

logger = logging.getLogger(__name__)

_LOCAL_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# ── Local cross-encoder ───────────────────────────────────────────────────────

class CrossEncoderReranker:
    """Rerank using a local cross-encoder. Model is lazy-loaded and process-cached."""

    _model = None

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder: %s", _LOCAL_MODEL)
            cls._model = CrossEncoder(_LOCAL_MODEL)
        return cls._model

    async def rerank(self, query: str, chunks: list[ChunkResult], n: int = 5) -> list[ChunkResult]:
        if not chunks:
            return []
        n = min(n, len(chunks))

        def _predict() -> list[float]:
            model = self._load_model()
            return [float(s) for s in model.predict([(query, c.chunk_text) for c in chunks])]

        try:
            scores = await asyncio.to_thread(_predict)
        except Exception as exc:
            logger.warning("Cross-encoder failed, using fusion order: %s", exc)
            return chunks[:n]

        result = []
        for chunk, score in sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:n]:
            chunk.rerank_score = score
            result.append(chunk)
        return result


# ── Cohere reranker ───────────────────────────────────────────────────────────

class CohereReranker:
    """Rerank using the Cohere Rerank API. Falls back to local on error."""

    async def rerank(self, query: str, chunks: list[ChunkResult], n: int = 5) -> list[ChunkResult]:
        from app.config import settings
        if not settings.cohere_api_key:
            logger.warning("Cohere API key not set, falling back to local reranker")
            return await CrossEncoderReranker().rerank(query, chunks, n)

        if not chunks:
            return []
        n = min(n, len(chunks))

        try:
            import cohere
            co = cohere.AsyncClientV2(api_key=settings.cohere_api_key)
            response = await co.rerank(
                model="rerank-v3.5",
                query=query,
                documents=[{"text": c.chunk_text} for c in chunks],
                top_n=n,
            )
            await co.close()

            result = []
            for item in response.results:
                chunk = chunks[item.index]
                chunk.rerank_score = float(item.relevance_score)
                result.append(chunk)
            return result

        except Exception as exc:
            logger.warning("Cohere rerank failed, falling back to local: %s", exc)
            return await CrossEncoderReranker().rerank(query, chunks, n)


# ── Factory ───────────────────────────────────────────────────────────────────

def get_reranker(backend: str = "local") -> Union[CrossEncoderReranker, CohereReranker]:
    if backend == "cohere":
        return CohereReranker()
    return CrossEncoderReranker()
