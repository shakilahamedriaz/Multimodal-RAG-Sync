import asyncio

from app.parsers.docx_parser import DOCXParser, TextParser
from app.parsers.image_parser import ImageParser
from app.parsers.table_parser import TableAwarePDFParser
from app.schemas import ParsedDocument

_IMAGE_MIME_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "image/gif",
})

# PDFs use the table-aware parser by default (handles text + tables)
_PARSER_MAP: dict[str, object] = {
    "application/pdf": TableAwarePDFParser(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser(),
    "text/plain": TextParser(),
    "text/markdown": TextParser(),
    **{mime: ImageParser() for mime in _IMAGE_MIME_TYPES},
}

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(_PARSER_MAP.keys())


async def parse_document(content: bytes, mime_type: str) -> ParsedDocument:
    """Dispatch to the correct parser and run it off the event loop."""
    parser = _PARSER_MAP.get(mime_type)
    if parser is None:
        raise ValueError(
            f"Unsupported MIME type: {mime_type!r}. "
            f"Supported: {sorted(SUPPORTED_MIME_TYPES)}"
        )
    if mime_type in _IMAGE_MIME_TYPES:
        # ImageParser.parse needs the mime_type for the base64 data URL
        return await asyncio.to_thread(parser.parse, content, mime_type)
    return await asyncio.to_thread(parser.parse, content)
