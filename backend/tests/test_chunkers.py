"""Tests for chunking strategies."""
import pytest

from app.schemas import ParsedDocument, ParsedPage
from app.chunkers.fixed_size import FixedSizeChunker
from app.chunkers.recursive import RecursiveChunker
from app.chunkers.page_level import PageLevelChunker
from app.chunkers import get_chunker


def _make_doc(text: str, pages: int = 1) -> ParsedDocument:
    size = max(1, len(text) // pages)
    return ParsedDocument(
        pages=[
            ParsedPage(
                page_number=i + 1,
                text=text[i * size : (i + 1) * size] or "x",
            )
            for i in range(pages)
        ]
    )


# ── FixedSizeChunker ──────────────────────────────────────────────────────────

class TestFixedSizeChunker:
    def setup_method(self):
        self.chunker = FixedSizeChunker()

    def test_short_text_single_chunk(self):
        doc = _make_doc("Hello world")
        chunks = self.chunker.chunk(doc, chunk_size=512, overlap=64)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"

    def test_long_text_splits(self):
        doc = _make_doc("word " * 600)
        chunks = self.chunker.chunk(doc, chunk_size=128, overlap=16)
        assert len(chunks) > 1

    def test_overlap_carries_tokens(self):
        doc = _make_doc("a b c d e f g h i j " * 50)
        chunks = self.chunker.chunk(doc, chunk_size=32, overlap=8)
        # Chunk 1 should start with overlap tokens from chunk 0
        if len(chunks) >= 2:
            tokens_0 = chunks[0].text.split()
            tokens_1 = chunks[1].text.split()
            assert tokens_0[-1] in tokens_1[:8] or len(tokens_0) <= 8

    def test_chunk_index_sequential(self):
        doc = _make_doc("word " * 300)
        chunks = self.chunker.chunk(doc, chunk_size=64, overlap=8)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_token_count_positive(self):
        doc = _make_doc("The quick brown fox")
        chunks = self.chunker.chunk(doc)
        assert all(c.token_count > 0 for c in chunks)

    def test_empty_document(self):
        doc = ParsedDocument(pages=[ParsedPage(page_number=1, text="")])
        chunks = self.chunker.chunk(doc)
        assert len(chunks) == 0


# ── RecursiveChunker ──────────────────────────────────────────────────────────

class TestRecursiveChunker:
    def setup_method(self):
        self.chunker = RecursiveChunker()

    def test_basic_split(self):
        doc = _make_doc("Para one.\n\nPara two.\n\nPara three.")
        chunks = self.chunker.chunk(doc, chunk_size=10, overlap=0)
        assert len(chunks) >= 2

    def test_no_split_for_small_text(self):
        doc = _make_doc("Short text.")
        chunks = self.chunker.chunk(doc, chunk_size=512, overlap=0)
        assert len(chunks) == 1

    def test_chunk_type_default_text(self):
        doc = _make_doc("Hello world")
        chunks = self.chunker.chunk(doc)
        assert all(c.chunk_type == "text" for c in chunks)

    def test_empty_pages_skipped(self):
        doc = ParsedDocument(pages=[
            ParsedPage(page_number=1, text=""),
            ParsedPage(page_number=2, text="Real content here"),
        ])
        chunks = self.chunker.chunk(doc)
        assert len(chunks) == 1


# ── PageLevelChunker ──────────────────────────────────────────────────────────

class TestPageLevelChunker:
    def setup_method(self):
        self.chunker = PageLevelChunker()

    def test_one_chunk_per_page(self):
        doc = _make_doc("Hello world", pages=3)
        chunks = self.chunker.chunk(doc)
        assert len(chunks) == 3

    def test_page_numbers_preserved(self):
        doc = _make_doc("Hello world", pages=3)
        chunks = self.chunker.chunk(doc)
        assert [c.page_number for c in chunks] == [1, 2, 3]

    def test_chunk_type_preserved(self):
        doc = ParsedDocument(pages=[
            ParsedPage(page_number=1, text="text content", chunk_type="text"),
            ParsedPage(page_number=2, text="| col1 | col2 |", chunk_type="table"),
        ])
        chunks = self.chunker.chunk(doc)
        assert chunks[0].chunk_type == "text"
        assert chunks[1].chunk_type == "table"

    def test_empty_pages_skipped(self):
        doc = ParsedDocument(pages=[
            ParsedPage(page_number=1, text=""),
            ParsedPage(page_number=2, text="Content"),
        ])
        chunks = self.chunker.chunk(doc)
        assert len(chunks) == 1


# ── Factory ───────────────────────────────────────────────────────────────────

class TestChunkerFactory:
    def test_recursive_default(self):
        chunker = get_chunker("recursive")
        assert isinstance(chunker, RecursiveChunker)

    def test_fixed_size(self):
        chunker = get_chunker("fixed_size")
        assert isinstance(chunker, FixedSizeChunker)

    def test_page_level(self):
        chunker = get_chunker("page_level")
        assert isinstance(chunker, PageLevelChunker)

    def test_unknown_falls_back_to_recursive(self):
        chunker = get_chunker("nonexistent_strategy")
        assert isinstance(chunker, RecursiveChunker)
