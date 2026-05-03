from openai import AsyncOpenAI

from app.config import settings

_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}
_BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs; 100 is safe for large chunks


class OpenAIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS.get(self.model, 1536)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches, preserving input order."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=self.model,
                input=batch,
            )
            # API guarantees items are returned in order, but sort by index defensively
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend(item.embedding for item in sorted_data)

        return all_embeddings
