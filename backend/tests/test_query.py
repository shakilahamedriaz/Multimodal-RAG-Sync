"""Tests for query service helpers and retrieval utilities."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import ChunkResult, SourceCitation
from app.services.query_service import _build_sources, _sse


# ── _build_sources ────────────────────────────────────────────────────────────

def _make_chunk(**kwargs) -> ChunkResult:
    defaults = dict(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        kb_id=uuid.uuid4(),
        chunk_text="Sample text for testing purposes",
        chunk_type="text",
        page_number=1,
        chunk_index=0,
        token_count=6,
        embedding_model="text-embedding-3-small",
        filename="test.pdf",
        dense_score=0.85,
        sparse_score=0.5,
        fusion_score=0.68,
        rerank_score=None,
    )
    defaults.update(kwargs)
    return ChunkResult(**defaults)


class TestBuildSources:
    def test_returns_correct_count(self):
        chunks = [_make_chunk() for _ in range(3)]
        sources = _build_sources(chunks)
        assert len(sources) == 3

    def test_source_index_one_based(self):
        chunks = [_make_chunk() for _ in range(3)]
        sources = _build_sources(chunks)
        assert [s.source_index for s in sources] == [1, 2, 3]

    def test_excerpt_truncated_at_300(self):
        long_text = "x" * 400
        chunk = _make_chunk(chunk_text=long_text)
        sources = _build_sources([chunk])
        assert sources[0].excerpt.endswith("…")
        assert len(sources[0].excerpt) == 301  # 300 + "…"

    def test_short_text_not_truncated(self):
        chunk = _make_chunk(chunk_text="short")
        sources = _build_sources([chunk])
        assert sources[0].excerpt == "short"

    def test_rerank_score_passed_through(self):
        chunk = _make_chunk(rerank_score=0.92)
        sources = _build_sources([chunk])
        assert sources[0].rerank_score == pytest.approx(0.92, abs=1e-3)

    def test_rerank_score_none_when_absent(self):
        chunk = _make_chunk(rerank_score=None)
        sources = _build_sources([chunk])
        assert sources[0].rerank_score is None

    def test_ids_are_strings(self):
        chunk = _make_chunk()
        sources = _build_sources([chunk])
        assert isinstance(sources[0].chunk_id, str)
        assert isinstance(sources[0].document_id, str)


# ── _sse ─────────────────────────────────────────────────────────────────────

class TestSSEFormatter:
    def test_format_token_event(self):
        result = _sse("token", {"content": "hello"})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        import json
        payload = json.loads(result[6:])
        assert payload["type"] == "token"
        assert payload["content"] == "hello"

    def test_format_done_event(self):
        result = _sse("done", {"has_answer": True})
        import json
        payload = json.loads(result[6:])
        assert payload["type"] == "done"
        assert payload["has_answer"] is True

    def test_no_answer_event(self):
        result = _sse("no_answer", {"message": "Not found"})
        import json
        payload = json.loads(result[6:])
        assert payload["type"] == "no_answer"


# ── Hybrid retrieval filter builder ──────────────────────────────────────────

class TestFilterBuilder:
    def test_eq_filter(self):
        from app.retrieval.hybrid_retriever import _build_filter_clause
        clause, params = _build_filter_clause([{"field": "chunk_type", "op": "eq", "value": "table"}], "AND")
        assert "chunk_type" in str(clause)
        assert params.get("p0") == "table"

    def test_whitelist_rejects_unknown_field(self):
        from app.retrieval.hybrid_retriever import _build_filter_clause
        with pytest.raises(ValueError, match="not allowed"):
            _build_filter_clause([{"field": "injection_attempt", "op": "eq", "value": "x"}], "AND")

    def test_op_whitelist_rejects_unknown_op(self):
        from app.retrieval.hybrid_retriever import _build_filter_clause
        with pytest.raises(ValueError, match="Unknown op"):
            _build_filter_clause([{"field": "page_number", "op": "LIKE", "value": "%"}], "AND")

    def test_empty_filters_return_none(self):
        from app.retrieval.hybrid_retriever import _build_filter_clause
        clause, params = _build_filter_clause([], "AND")
        assert clause is None
        assert params == {}

    def test_in_op(self):
        from app.retrieval.hybrid_retriever import _build_filter_clause
        clause, params = _build_filter_clause(
            [{"field": "chunk_type", "op": "in", "value": ["text", "table"]}], "AND"
        )
        assert clause is not None


# ── Reranker factory ──────────────────────────────────────────────────────────

class TestRerankerFactory:
    def test_local_returns_cross_encoder(self):
        from app.retrieval.reranker import get_reranker, CrossEncoderReranker
        assert isinstance(get_reranker("local"), CrossEncoderReranker)

    def test_cohere_returns_cohere_reranker(self):
        from app.retrieval.reranker import get_reranker, CohereReranker
        assert isinstance(get_reranker("cohere"), CohereReranker)

    def test_default_is_local(self):
        from app.retrieval.reranker import get_reranker, CrossEncoderReranker
        assert isinstance(get_reranker(), CrossEncoderReranker)


# ── Storage ───────────────────────────────────────────────────────────────────

class TestStorage:
    def test_compute_hash_deterministic(self):
        from app.storage import compute_hash
        data = b"hello world"
        assert compute_hash(data) == compute_hash(data)

    def test_compute_hash_different_content(self):
        from app.storage import compute_hash
        assert compute_hash(b"aaa") != compute_hash(b"bbb")

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        from app import storage
        monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)
        data = b"test binary content"
        key = storage.save_file(data, "test.txt")
        loaded = storage.load_file(key)
        assert loaded == data

    def test_idempotent_save(self, tmp_path, monkeypatch):
        from app import storage
        monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)
        data = b"same content"
        key1 = storage.save_file(data, "file.txt")
        key2 = storage.save_file(data, "file.txt")
        assert key1 == key2

    def test_delete_file(self, tmp_path, monkeypatch):
        from app import storage
        monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)
        data = b"to delete"
        key = storage.save_file(data, "del.txt")
        storage.delete_file(key)
        assert not (tmp_path / key).exists()
