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

_CHAT_SYSTEM_PROMPT = """\
You are an intelligent, professional assistant specialized in the documents uploaded to this knowledge base.

Guidelines:
1. Answer exclusively from the document context provided with each user message — never fabricate or use outside knowledge.
2. Cite sources inline as [Source N], e.g. "According to [Source 1], the policy states...".
3. Maintain a helpful, conversational tone across multiple turns. If a follow-up question refers to something from earlier in the conversation, resolve it naturally using that prior context.
4. If the answer is not in the provided documents, acknowledge the question warmly and explain clearly that the topic is not covered in the knowledge base.
5. Be concise, accurate, and professional. Format your responses with markdown when it aids clarity (lists, bold key terms, tables).\
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


def _resolve_model(model: str) -> str:
    """Add provider prefix if missing so LiteLLM can route correctly."""
    if model.startswith("claude-") and "/" not in model:
        return f"anthropic/{model}"
    return model


class LLMGenerator:
    async def stream(
        self,
        query: str,
        chunks: list[ChunkResult],
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive from the LLM."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(query, chunks)},
        ]

        response = await litellm.acompletion(
            model=_resolve_model(model),
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
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> str:
        """Return the full answer as a single string (non-streaming)."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(query, chunks)},
        ]

        response = await litellm.acompletion(
            model=_resolve_model(model),
            messages=messages,
            stream=False,
        )

        return response.choices[0].message.content or ""

    async def stream_chat(
        self,
        messages: list[dict],
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> AsyncGenerator[str, None]:
        """Stream chat response given a full messages list (system + history + current)."""
        response = await litellm.acompletion(
            model=_resolve_model(model),
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            token: str = chunk.choices[0].delta.content or ""
            if token:
                yield token

    async def complete_chat(
        self,
        messages: list[dict],
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> str:
        """Return the full chat response as a single string (non-streaming)."""
        response = await litellm.acompletion(
            model=_resolve_model(model),
            messages=messages,
            stream=False,
        )
        return response.choices[0].message.content or ""
