from app.chunkers.fixed_size import FixedSizeChunker
from app.chunkers.page_level import PageLevelChunker
from app.chunkers.recursive import RecursiveChunker
from app.chunkers.semantic import SemanticChunker

_REGISTRY = {
    "fixed_size": FixedSizeChunker,
    "recursive": RecursiveChunker,
    "semantic": SemanticChunker,
    "page_level": PageLevelChunker,
}


def get_chunker(strategy: str):
    cls = _REGISTRY.get(strategy, RecursiveChunker)
    return cls()
