import tiktoken

from app.schemas import ParsedDocument, TextChunk

_MIN_TOKENS = 50


class FixedSizeChunker:
    """Split document pages into fixed-width token windows with overlap."""

    def __init__(self) -> None:
        self._enc = tiktoken.get_encoding("cl100k_base")

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

            tokens = self._enc.encode(text)
            start = 0

            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                window = tokens[start:end]

                if len(window) >= _MIN_TOKENS:
                    result.append(
                        TextChunk(
                            text=self._enc.decode(window),
                            token_count=len(window),
                            page_number=page.page_number,
                            chunk_index=len(result),
                        )
                    )

                if end >= len(tokens):
                    break
                start = end - overlap

        return result
