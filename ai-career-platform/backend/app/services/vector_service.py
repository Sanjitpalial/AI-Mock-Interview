"""Embeddings and similarity. Heavy deps (Chroma, sentence-transformers) load on first use."""

from __future__ import annotations

from typing import Any

from app.config import settings

_chroma_client: Any = None
_embedding_model: Any = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _chroma_client


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def get_or_create_collection(name: str):
    client = _get_chroma_client()
    return client.get_or_create_collection(name)


def store_resume_embedding(user_id: int, resume_text: str) -> None:
    collection = get_or_create_collection("resumes")
    model = _get_embedding_model()
    embedding = model.encode(resume_text).tolist()
    collection.upsert(
        ids=[f"resume_{user_id}"],
        embeddings=[embedding],
        documents=[resume_text],
        metadatas=[{"user_id": str(user_id)}],
    )


def _similarity_tfidf(text1: str, text2: str) -> float:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    a, b = text1 or "", text2 or ""
    if not a.strip() or not b.strip():
        return 0.0
    vec = TfidfVectorizer(min_df=1, analyzer="word")
    try:
        m = vec.fit_transform([a, b])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0])
    except ValueError:
        return 0.0


def compute_similarity(text1: str, text2: str) -> float:
    try:
        model = _get_embedding_model()
        from sklearn.metrics.pairwise import cosine_similarity

        emb1 = model.encode([text1 or ""])
        emb2 = model.encode([text2 or ""])
        return float(cosine_similarity(emb1, emb2)[0][0])
    except Exception:
        return _similarity_tfidf(text1, text2)
