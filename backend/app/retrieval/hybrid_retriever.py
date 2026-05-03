import asyncio
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ChunkResult

logger = logging.getLogger(__name__)

# ── Filter safety whitelist ───────────────────────────────────────────────────

_ALLOWED_COLUMNS: dict[str, str] = {
    "page_number": "c.page_number",
    "chunk_type": "c.chunk_type",
    "chunk_index": "c.chunk_index",
    "document_id": "c.document_id",
}

_SCALAR_OPS: dict[str, str] = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


def _build_filter_clause(filters: list[dict], filter_op: str) -> tuple[str, dict]:
    """Convert filter spec to a safe SQL fragment + parameter dict.

    Column names come from an explicit whitelist — never interpolated directly.
    All user values are bound as named parameters.
    Returns ("AND (cond1 AND/OR cond2)", {"fp_0": val, ...}) or ("", {}).
    """
    if not filters:
        return "", {}

    conditions: list[str] = []
    params: dict = {}

    for i, f in enumerate(filters):
        field: str = f.get("field", "")
        op: str = f.get("op", "")
        value = f.get("value")
        param = f"fp_{i}"

        if field not in _ALLOWED_COLUMNS:
            raise ValueError(f"Filter field {field!r} is not allowed. Allowed: {list(_ALLOWED_COLUMNS)}")

        col = _ALLOWED_COLUMNS[field]

        if op in _SCALAR_OPS:
            conditions.append(f"{col} {_SCALAR_OPS[op]} :{param}")
            params[param] = str(value) if field == "document_id" else value

        elif op == "in":
            if not isinstance(value, list) or not value:
                raise ValueError("'in' filter requires a non-empty list value")
            placeholders = [f":{param}_{j}" for j in range(len(value))]
            conditions.append(f"{col} IN ({', '.join(placeholders)})")
            for j, v in enumerate(value):
                params[f"{param}_{j}"] = v

        elif op == "nin":
            if not isinstance(value, list) or not value:
                raise ValueError("'nin' filter requires a non-empty list value")
            placeholders = [f":{param}_{j}" for j in range(len(value))]
            conditions.append(f"{col} NOT IN ({', '.join(placeholders)})")
            for j, v in enumerate(value):
                params[f"{param}_{j}"] = v

        else:
            raise ValueError(f"Unknown filter op: {op!r}")

    joiner = f" {filter_op} "
    return "AND (" + joiner.join(conditions) + ")", params


# ── Row mapper ────────────────────────────────────────────────────────────────

def _to_chunk_result(row, dense_score: float = 0.0, sparse_score: float = 0.0) -> ChunkResult:
    return ChunkResult(
        chunk_id=row.chunk_id,
        document_id=row.document_id,
        kb_id=row.kb_id,
        chunk_text=row.chunk_text,
        chunk_type=row.chunk_type,
        page_number=row.page_number,
        chunk_index=row.chunk_index,
        token_count=row.token_count,
        embedding_model=row.embedding_model,
        filename=row.filename,
        dense_score=dense_score,
        sparse_score=sparse_score,
    )


# ── Retriever ─────────────────────────────────────────────────────────────────

class HybridRetriever:
    """Dense (pgvector HNSW cosine) + Sparse (BM25s) with alpha-blend score fusion."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def retrieve(
        self,
        kb_id: UUID,
        query: str,
        query_vector: list[float],
        top_k: int = 20,
        alpha: float = 0.5,
        filters: Optional[list[dict]] = None,
        filter_op: str = "AND",
    ) -> list[ChunkResult]:
        filters = filters or []
        filter_sql, filter_params = _build_filter_clause(filters, filter_op)
        fetch_k = min(top_k * 3, 150)

        dense, sparse = await asyncio.gather(
            self._dense_retrieve(kb_id, query_vector, fetch_k, filter_sql, filter_params),
            self._sparse_retrieve(kb_id, query, fetch_k, filter_sql, filter_params),
        )

        if not dense and not sparse:
            return []

        return self._fuse(dense, sparse, alpha)[:top_k]

    # ── Dense ────────────────────────────────────────────────────────────────

    async def _dense_retrieve(
        self,
        kb_id: UUID,
        query_vector: list[float],
        k: int,
        filter_sql: str,
        filter_params: dict,
    ) -> list[ChunkResult]:
        vec_str = "[" + ",".join(map(str, query_vector)) + "]"

        sql = text(f"""
            SELECT
                c.id              AS chunk_id,
                c.document_id,
                c.kb_id,
                c.chunk_text,
                c.chunk_type,
                c.page_number,
                c.chunk_index,
                c.token_count,
                c.embedding_model,
                d.filename,
                (1.0 - (c.embedding <=> CAST(:vec AS vector))) AS similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.kb_id = CAST(:kb_id AS uuid)
              AND c.embedding IS NOT NULL
            {filter_sql}
            ORDER BY c.embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """)

        params = {"vec": vec_str, "kb_id": str(kb_id), "k": k}
        params.update(filter_params)

        rows = (await self._db.execute(sql, params)).fetchall()
        return [_to_chunk_result(r, dense_score=float(r.similarity)) for r in rows]

    # ── Sparse ───────────────────────────────────────────────────────────────

    async def _sparse_retrieve(
        self,
        kb_id: UUID,
        query: str,
        k: int,
        filter_sql: str,
        filter_params: dict,
    ) -> list[ChunkResult]:
        sql = text(f"""
            SELECT
                c.id              AS chunk_id,
                c.document_id,
                c.kb_id,
                c.chunk_text,
                c.chunk_type,
                c.page_number,
                c.chunk_index,
                c.token_count,
                c.embedding_model,
                d.filename
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.kb_id = CAST(:kb_id AS uuid)
            {filter_sql}
        """)

        params = {"kb_id": str(kb_id)}
        params.update(filter_params)

        rows = (await self._db.execute(sql, params)).fetchall()
        if not rows:
            return []

        texts = [r.chunk_text for r in rows]
        actual_k = min(k, len(texts))

        def _run_bm25() -> tuple[list[int], list[float]]:
            import bm25s  # lazy import — heavy CPU, no need at module load
            corpus_tokens = bm25s.tokenize(texts, stopwords="en")
            retriever = bm25s.BM25()
            retriever.index(corpus_tokens)
            q_tokens = bm25s.tokenize([query], stopwords="en")
            results, scores = retriever.retrieve(q_tokens, k=actual_k)
            return results[0].tolist(), scores[0].tolist()

        try:
            indices, scores = await asyncio.to_thread(_run_bm25)
        except Exception as exc:
            logger.warning("BM25 sparse retrieval failed, returning dense-only: %s", exc)
            return []

        max_score = max(scores, default=1.0) or 1.0
        normalized = [s / max_score for s in scores]

        return [
            _to_chunk_result(rows[idx], sparse_score=float(normalized[i]))
            for i, idx in enumerate(indices)
        ]

    # ── Fusion ────────────────────────────────────────────────────────────────

    @staticmethod
    def _fuse(
        dense: list[ChunkResult],
        sparse: list[ChunkResult],
        alpha: float,
    ) -> list[ChunkResult]:
        """final_score = alpha × dense_score + (1 - alpha) × sparse_score"""
        dense_map = {str(c.chunk_id): c for c in dense}
        sparse_map = {str(c.chunk_id): c for c in sparse}

        fused: list[ChunkResult] = []
        for cid in set(dense_map) | set(sparse_map):
            base = dense_map.get(cid) or sparse_map[cid]
            d = dense_map[cid].dense_score if cid in dense_map else 0.0
            s = sparse_map[cid].sparse_score if cid in sparse_map else 0.0

            fused.append(ChunkResult(
                chunk_id=base.chunk_id,
                document_id=base.document_id,
                kb_id=base.kb_id,
                chunk_text=base.chunk_text,
                chunk_type=base.chunk_type,
                page_number=base.page_number,
                chunk_index=base.chunk_index,
                token_count=base.token_count,
                embedding_model=base.embedding_model,
                filename=base.filename,
                dense_score=d,
                sparse_score=s,
                fusion_score=alpha * d + (1.0 - alpha) * s,
            ))

        return sorted(fused, key=lambda x: x.fusion_score, reverse=True)
