import re
import logging
from typing import ClassVar

import numpy as np
import tiktoken

from app.schemas import ParsedDocument, TextChunk

logger = logging.getLogger(__name__)

# Small, fast model for LOCAL sentence grouping only — NOT for stored embeddings
_GROUPING_MODEL = "all-MiniLM-L6-v2"
_SIM_THRESHOLD = 0.40   # split group when consecutive similarity drops below this
_MIN_TOKENS = 50


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on common terminal punctuation."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


class SemanticChunker:
    """Group sentences by embedding similarity, then split at semantic valleys.

    Uses sentence-transformers/all-MiniLM-L6-v2 locally for grouping decisions.
    The stored chunk embeddings are still produced by the KB's configured model
    (OpenAI or sentence-transformer) — this model is only used for boundary detection.
    """

    _models: ClassVar[dict] = {}

    @classmethod
    def _get_grouping_model(cls):
        if _GROUPING_MODEL not in cls._models:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading semantic chunker grouping model: %s", _GROUPING_MODEL)
            cls._models[_GROUPING_MODEL] = SentenceTransformer(_GROUPING_MODEL)
        return cls._models[_GROUPING_MODEL]

    def chunk(
        self,
        parsed: ParsedDocument,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> list[TextChunk]:
        enc = tiktoken.get_encoding("cl100k_base")
        model = self._get_grouping_model()
        result: list[TextChunk] = []

        for page in parsed.pages:
            text = page.text.strip()
            if not text:
                continue

            sentences = _split_sentences(text)
            if not sentences:
                continue

            if len(sentences) == 1:
                tc = len(enc.encode(sentences[0]))
                if tc >= _MIN_TOKENS:
                    result.append(TextChunk(
                        text=sentences[0], token_count=tc,
                        page_number=page.page_number, chunk_index=len(result),
                        chunk_type=page.chunk_type,
                    ))
                continue

            # Embed all sentences with the lightweight grouping model
            embeddings = model.encode(
                sentences, normalize_embeddings=True, show_progress_bar=False
            )

            # Cosine similarity between consecutive pairs (already normalised → dot product)
            sims = [
                float(np.dot(embeddings[i], embeddings[i + 1]))
                for i in range(len(embeddings) - 1)
            ]

            # Build groups — split wherever similarity drops or chunk_size would be exceeded
            groups: list[list[str]] = []
            current: list[str] = [sentences[0]]
            current_tokens = len(enc.encode(sentences[0]))

            for sent, sim in zip(sentences[1:], sims):
                s_tok = len(enc.encode(sent))
                if sim < _SIM_THRESHOLD or current_tokens + s_tok > chunk_size:
                    groups.append(current)
                    current = [sent]
                    current_tokens = s_tok
                else:
                    current.append(sent)
                    current_tokens += s_tok
            if current:
                groups.append(current)

            # Convert groups → TextChunk, applying overlap between adjacent groups
            group_texts = [" ".join(g) for g in groups]
            for i, chunk_text in enumerate(group_texts):
                if overlap > 0 and i > 0:
                    prev_tokens = enc.encode(group_texts[i - 1])
                    tail = enc.decode(prev_tokens[-overlap:]).strip()
                    if tail:
                        chunk_text = tail + " " + chunk_text

                tc = len(enc.encode(chunk_text))
                if tc >= _MIN_TOKENS:
                    result.append(TextChunk(
                        text=chunk_text.strip(), token_count=tc,
                        page_number=page.page_number, chunk_index=len(result),
                        chunk_type=page.chunk_type,
                    ))

        return result
