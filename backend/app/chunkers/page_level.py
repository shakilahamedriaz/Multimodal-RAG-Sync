import tiktoken

from app.schemas import ParsedDocument, TextChunk

_MIN_TOKENS = 50


class PageLevelChunker:
    """One chunk per ParsedPage — never splits across page boundaries.

    Ideal for documents where page attribution matters (legal, academic).
    Also preserves chunk_type so table and image_caption pages stay as
    their own typed chunks.

    Note: chunk_size is intentionally ignored — page content is kept whole.
    """

    def __init__(self) -> None:
        self._enc = tiktoken.get_encoding("cl100k_base")

    def chunk(
        self,
        parsed: ParsedDocument,
        chunk_size: int = 512,   # unused — kept for interface compatibility
        overlap: int = 0,        # unused at page level
    ) -> list[TextChunk]:
        result: list[TextChunk] = []

        for page in parsed.pages:
            text = page.text.strip()
            if not text:
                continue
            token_count = len(self._enc.encode(text))
            if token_count < _MIN_TOKENS:
                continue
            result.append(
                TextChunk(
                    text=text,
                    token_count=token_count,
                    page_number=page.page_number,
                    chunk_index=len(result),
                    chunk_type=page.chunk_type,  # preserves "table" / "image_caption"
                )
            )

        return result
