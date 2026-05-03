import tiktoken

from app.schemas import ParsedDocument, TextChunk

_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", ", ", " "]
_MIN_TOKENS = 50


class RecursiveChunker:
    """Split text by progressively finer separators, then merge greedily up to
    chunk_size tokens. Applies token-level overlap between adjacent chunks."""

    def __init__(self) -> None:
        self._enc = tiktoken.get_encoding("cl100k_base")

    # ── Public API ───────────────────────────────────────────────────────────

    def chunk(
        self,
        parsed: ParsedDocument,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> list[TextChunk]:
        result: list[TextChunk] = []

        for page in parsed.pages:
            text = page.text.strip()
            if not text:
                continue

            splits = self._split(text, chunk_size)

            for raw in splits:
                token_count = self._count(raw)
                if token_count >= _MIN_TOKENS:
                    result.append(
                        TextChunk(
                            text=raw.strip(),
                            token_count=token_count,
                            page_number=page.page_number,
                            chunk_index=len(result),
                        )
                    )

        return self._apply_overlap(result, overlap)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _count(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _split(self, text: str, chunk_size: int, depth: int = 0) -> list[str]:
        """Recursively split text until every piece fits within chunk_size."""
        if self._count(text) <= chunk_size:
            return [text]

        if depth >= len(_SEPARATORS):
            # Hard token split as absolute fallback
            tokens = self._enc.encode(text)
            return [
                self._enc.decode(tokens[i : i + chunk_size])
                for i in range(0, len(tokens), chunk_size)
            ]

        sep = _SEPARATORS[depth]
        parts = [p for p in text.split(sep) if p.strip()]

        if len(parts) <= 1:
            # Separator not found at this level — try next
            return self._split(text, chunk_size, depth + 1)

        # Greedily merge adjacent parts into chunks ≤ chunk_size
        merged: list[str] = []
        buf: list[str] = []
        buf_tokens = 0

        for part in parts:
            part_tokens = self._count(part + sep)

            if part_tokens > chunk_size:
                # Part alone exceeds limit — flush buffer and recurse
                if buf:
                    merged.append(sep.join(buf))
                    buf, buf_tokens = [], 0
                merged.extend(self._split(part, chunk_size, depth + 1))

            elif buf_tokens + part_tokens > chunk_size:
                # Would overflow — flush buffer, start new one
                if buf:
                    merged.append(sep.join(buf))
                buf = [part]
                buf_tokens = part_tokens

            else:
                buf.append(part)
                buf_tokens += part_tokens

        if buf:
            merged.append(sep.join(buf))

        return merged if merged else [text]

    def _apply_overlap(self, chunks: list[TextChunk], overlap: int) -> list[TextChunk]:
        """Prepend the last `overlap` tokens of the previous chunk to each chunk."""
        if overlap <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_tokens = self._enc.encode(chunks[i - 1].text)
            tail_tokens = prev_tokens[-overlap:] if len(prev_tokens) > overlap else prev_tokens
            tail_text = self._enc.decode(tail_tokens).strip()

            new_text = (tail_text + " " + chunks[i].text).strip() if tail_text else chunks[i].text
            result.append(
                TextChunk(
                    text=new_text,
                    token_count=self._count(new_text),
                    page_number=chunks[i].page_number,
                    chunk_index=chunks[i].chunk_index,
                    chunk_type=chunks[i].chunk_type,
                    chunk_metadata=chunks[i].chunk_metadata,
                )
            )

        return result
