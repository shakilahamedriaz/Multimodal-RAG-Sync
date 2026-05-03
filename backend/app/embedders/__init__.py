from app.embedders.openai_embedder import OpenAIEmbedder
from app.embedders.sentence_transformer_embedder import SentenceTransformerEmbedder

_OPENAI_MODELS = {"text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"}
_ST_MODELS = {
    "all-MiniLM-L6-v2",
    "all-mpnet-base-v2",
    "BAAI/bge-base-en-v1.5",
    "BAAI/bge-large-en-v1.5",
    "intfloat/e5-large-v2",
    "intfloat/e5-base-v2",
}


def get_embedder(model: str) -> OpenAIEmbedder | SentenceTransformerEmbedder:
    if model in _OPENAI_MODELS:
        return OpenAIEmbedder(model=model)
    if model in _ST_MODELS:
        return SentenceTransformerEmbedder(model=model)
    raise ValueError(
        f"Unsupported embedding model: {model!r}. "
        f"OpenAI: {sorted(_OPENAI_MODELS)}. "
        f"Local: {sorted(_ST_MODELS)}."
    )
