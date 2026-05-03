import logging
from typing import AsyncGenerator

import litellm

from app.schemas import ChunkResult

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose startup logging
litellm.suppress_debug_info = True

_SYSTEM_PROMPT = """\
You are a precise, factual assistant that answers questions using only the provided document excerpts.

Rules:
1. Base your answer exclusively on the context below — never add knowledge from outside it.
2. Cite sources inline using [Source N] notation, e.g. "According to [Source 1]...".
3. If the context does not contain enough information, respond with exactly:
   "I cannot find a relevant answer in the available documents."
4. Be concise, accurate, and direct.\
"""


def _build_user_message(query: str, chunks: list[ChunkResult]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        page_info = f", Page {chunk.page_number}" if chunk.page_number else ""
        parts.append(
            f"[Source {i}] (Document: {chunk.filename}{page_info})\n{chunk.chunk_text}"
        )
    context = "\n\n---\n\n".join(parts)
    return f"Context:\n\n{context}\n\nQuestion: {query}"


class LLMGenerator:
    async def stream(
        self,
        query: str,
        chunks: list[ChunkResult],
        model: str = "gpt-4o",
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive from the LLM."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(query, chunks)},
        ]

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
        )

        async for chunk in response:
            token: str = chunk.choices[0].delta.content or ""
            if token:
                yield token

    async def complete(
        self,
        query: str,
        chunks: list[ChunkResult],
        model: str = "gpt-4o",
    ) -> str:
        """Return the full answer as a single string (non-streaming)."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(query, chunks)},
        ]

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=False,
        )

        return response.choices[0].message.content or ""
