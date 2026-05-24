"""
app/agents/rag_agent.py
───────────────────────────────────────────────────────────────────
RAG Agent — Retrieval-Augmented Generation for the Study Assistant.

Responsibilities:
  • Store PDF chunks in ChromaDB with per-user namespacing
  • Retrieve semantically relevant chunks for any query
  • Answer questions using only the retrieved context (Groq LLM)
  • Generate notes, quizzes, and flashcards from stored material

LLM  : Groq  (llama-3.1-8b-instant)
Vector DB : ChromaDB  (persistent)
Embeddings: sentence-transformers  (all-MiniLM-L6-v2)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.groq_client import groq_chat

logger = logging.getLogger(__name__)

_chroma_client: Any = None
_embed_model: Any = None
_text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def _chroma_dir() -> str:
    return (settings.CHROMA_STUDY_DIR or "./chroma_study_db").strip()


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=_chroma_dir())
    return _chroma_client


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model for Study Assistant (first use may take a moment)")
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model

# Per-user conversation turns: {user_id: [(question, answer), ...]}
_memory_store: dict[str, list[tuple[str, str]]] = {}


# ═════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _collection_name(user_id: Optional[int]) -> str:
    """Each user gets their own ChromaDB collection so PDFs don't mix."""
    return f"study_user_{user_id}" if user_id else "study_global"


def _get_collection(user_id: Optional[int]):
    return _get_chroma_client().get_or_create_collection(_collection_name(user_id))


def _history_text(user_id: Optional[int], max_turns: int = 6) -> str:
    key = str(user_id or "global")
    turns = _memory_store.get(key, [])[-max_turns:]
    if not turns:
        return "(none)"
    lines = []
    for q, a in turns:
        lines.append(f"User: {q}\nAssistant: {a}")
    return "\n\n".join(lines)


def _save_turn(user_id: Optional[int], question: str, answer: str) -> None:
    key = str(user_id or "global")
    _memory_store.setdefault(key, []).append((question, answer))
    if len(_memory_store[key]) > 20:
        _memory_store[key] = _memory_store[key][-20:]


def _embed(texts: list[str]) -> list[list[float]]:
    return _get_embed_model().encode(texts).tolist()


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API — used by routers/study.py
# ═════════════════════════════════════════════════════════════════════════════

def store_pdf_chunks(
    user_id: Optional[int],
    doc_id: str,
    filename: str,
    raw_text: str,
) -> int:
    """
    Split raw_text into chunks, embed, and upsert into ChromaDB.
    Returns the number of chunks stored.
    """
    chunks = _text_splitter.split_text(raw_text)
    if not chunks:
        return 0

    embeddings = _embed(chunks)
    collection = _get_collection(user_id)

    collection.upsert(
        ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=chunks,
        metadatas=[
            {"source": filename, "doc_id": str(doc_id), "chunk_index": i}
            for i in range(len(chunks))
        ],
    )
    return len(chunks)


def delete_pdf_chunks(user_id: Optional[int], filename: str) -> int:
    """Delete all ChromaDB chunks for a given PDF filename. Returns count deleted."""
    collection = _get_collection(user_id)
    results = collection.get()
    ids = results.get("ids") or []
    metas = results.get("metadatas") or []

    ids_to_delete = [
        ids[i]
        for i, meta in enumerate(metas)
        if meta and meta.get("source") == filename
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def get_chunk_count(user_id: Optional[int]) -> int:
    return _get_collection(user_id).count()


def list_pdf_sources(user_id: Optional[int]) -> list[str]:
    """Return unique PDF filenames stored in this user's collection."""
    results = _get_collection(user_id).get()
    metas = results.get("metadatas") or []
    return list({m["source"] for m in metas if m and m.get("source")})


def _chunks_for_pdf(
    user_id: Optional[int],
    pdf_name: Optional[str] = None,
    *,
    max_chunks: int = 40,
) -> tuple[list[str], list[str]]:
    """Return document chunks from one PDF or all PDFs (up to max_chunks)."""
    collection = _get_collection(user_id)
    if collection.count() == 0:
        return [], []

    results = collection.get()
    docs = results.get("documents") or []
    metas = results.get("metadatas") or []

    out_docs: list[str] = []
    sources: list[str] = []
    for i, doc in enumerate(docs):
        if not doc:
            continue
        meta = metas[i] if i < len(metas) else {}
        source = (meta.get("source") or "") if meta else ""
        if pdf_name and source != pdf_name:
            continue
        out_docs.append(doc)
        if source:
            sources.append(source)
        if len(out_docs) >= max_chunks:
            break

    return out_docs, list(dict.fromkeys(sources))


def gather_pdf_context(
    user_id: Optional[int],
    pdf_name: Optional[str] = None,
    specification: Optional[str] = None,
    *,
    top_k: int = 16,
    max_chars: int = 14000,
) -> tuple[str, list[str], str]:
    """
    Build context for notes/quiz/flashcards.
    - specification set → semantic search within PDF (or all PDFs)
    - specification empty → entire selected PDF (or all PDFs)
    """
    if get_chunk_count(user_id) == 0:
        return "", [], ""

    spec = (specification or "").strip()
    documents: list[str] = []
    sources: list[str] = []

    try:
        if spec:
            documents, sources = retrieve_context(
                user_id, spec, pdf_name=pdf_name, top_k=top_k
            )
            scope = f"Specification: {spec}"
            if not documents:
                documents, sources = _chunks_for_pdf(
                    user_id, pdf_name, max_chunks=max(top_k, 20)
                )
        else:
            documents, sources = _chunks_for_pdf(
                user_id, pdf_name, max_chunks=max(top_k, 30)
            )
            scope = f"Full PDF: {pdf_name}" if pdf_name else "Full content (all uploaded PDFs)"
    except Exception as exc:
        logger.exception("gather_pdf_context retrieval failed, using raw chunks")
        documents, sources = _chunks_for_pdf(user_id, pdf_name, max_chunks=30)
        scope = f"Fallback read: {pdf_name or 'all PDFs'} ({exc})"

    if not documents:
        raise ValueError(
            "No text chunks found for this PDF. Re-upload the file or pick another PDF in the sidebar."
        )

    context = "\n\n---\n\n".join(d for d in documents if d)[:max_chars]
    return context, sources, scope


def retrieve_context(
    user_id: Optional[int],
    query: str,
    pdf_name: Optional[str] = None,
    top_k: int = 4,
) -> tuple[list[str], list[str]]:
    """
    Retrieve top_k relevant chunks for a query.
    Returns (documents, sources).
    """
    collection = _get_collection(user_id)
    count = collection.count()
    if count == 0:
        return [], []

    n_results = min(max(top_k, 1), count)
    query_embedding = _embed([query or "summary"])
    kwargs: dict = {"query_embeddings": query_embedding, "n_results": n_results}
    if pdf_name:
        kwargs["where"] = {"source": pdf_name}

    try:
        results = collection.query(**kwargs)
    except Exception as exc:
        logger.warning("Chroma query failed (%s), falling back to chunk list", exc)
        return _chunks_for_pdf(user_id, pdf_name, max_chunks=n_results)

    documents = results.get("documents") or []
    documents = documents[0] if documents and isinstance(documents[0], list) else documents
    documents = [d for d in (documents or []) if d]

    meta_rows = results.get("metadatas") or []
    meta_list = meta_rows[0] if meta_rows and isinstance(meta_rows[0], list) else meta_rows
    sources = list(
        {
            m.get("source")
            for m in (meta_list or [])
            if isinstance(m, dict) and m.get("source")
        }
    )
    return documents, sources


def compute_similarity(text1: str, text2: str) -> float:
    """Cosine similarity between two texts — used by evaluation_agent."""
    from sklearn.metrics.pairwise import cosine_similarity

    model = _get_embed_model()
    emb1 = model.encode([text1])
    emb2 = model.encode([text2])
    return float(cosine_similarity(emb1, emb2)[0][0])


# ── RAG ACTIONS ───────────────────────────────────────────────────────────────

def ask_doubt(
    user_id: Optional[int],
    question: str,
    pdf_name: Optional[str] = None,
) -> dict:
    """
    RAG question-answering with conversation memory.
    Mirrors collaborator's /ask-question endpoint logic.
    """
    if get_chunk_count(user_id) == 0:
        return {"answer": "Please upload a PDF first.", "sources": [], "chunks": []}

    try:
        documents, sources = retrieve_context(user_id, question, pdf_name, top_k=5)
    except Exception as exc:
        logger.exception("retrieve_context failed in ask_doubt")
        documents, sources = _chunks_for_pdf(user_id, pdf_name, max_chunks=8)
        if not documents:
            return {
                "answer": f"Could not search your PDF: {exc}. Try re-uploading the file.",
                "sources": [],
                "chunks": [],
            }

    if not documents:
        return {
            "answer": "No relevant content found in the uploaded material for this question.",
            "sources": [],
            "chunks": [],
        }

    context = "\n".join(documents)[:10000]
    history = _history_text(user_id)

    prompt = f"""
You are an AI Study Assistant.

Use the conversation history and provided context to answer the user's question.

IMPORTANT RULES:
- Answer ONLY from the provided context.
- If the answer is not in the context say:
  "This information is not available in the uploaded PDF."
- Keep answers simple and student-friendly.
- Use bullet points where helpful.
- Do NOT make up information.

Conversation History:
{history}

Context from PDF:
{context}

Question:
{question}

Answer:
"""

    try:
        answer = groq_chat(prompt)
    except ValueError as exc:
        return {
            "answer": str(exc),
            "sources": sources,
            "chunks": documents,
        }

    _save_turn(user_id, question, answer)
    return {"answer": answer, "sources": sources, "chunks": documents}


def generate_notes(
    user_id: Optional[int],
    pdf_name: Optional[str] = None,
    specification: Optional[str] = None,
) -> str:
    try:
        context, sources, scope = gather_pdf_context(
            user_id, pdf_name, specification, top_k=18, max_chars=12000
        )
    except ValueError as exc:
        return str(exc)

    if not context.strip():
        return "Please upload a PDF first."

    source_line = f"Sources: {', '.join(sources)}" if sources else ""

    prompt = f"""
You are an AI Notes Generator.

Create well-structured study notes from the student's uploaded PDF material.

Scope: {scope}
{source_line}

Rules:
- Use ONLY the provided content — do not invent facts
- Concise, revision-friendly notes
- Clear headings and bullet points
- Highlight key terms in **bold**
- If scope is a specific section, cover only that section in depth

Content from PDF:
{context}
"""
    try:
        return groq_chat(prompt)
    except ValueError as exc:
        return str(exc)


def generate_quiz(
    user_id: Optional[int],
    pdf_name: Optional[str] = None,
    specification: Optional[str] = None,
    num_questions: int = 5,
) -> str:
    try:
        context, sources, scope = gather_pdf_context(
            user_id, pdf_name, specification, top_k=14, max_chars=10000
        )
    except ValueError as exc:
        return str(exc)

    if not context.strip():
        return "Please upload a PDF first."

    prompt = f"""
You are an AI Quiz Generator.

Generate {num_questions} multiple-choice questions from the student's PDF.

Scope: {scope}

Rules:
- Each question: exactly 4 options (A, B, C, D)
- Include correct answer and one-line explanation
- Questions must come ONLY from the context below
- Match difficulty to the material

Context:
{context}

Format for EACH question:

Q[N]: <question>
A. <option>
B. <option>
C. <option>
D. <option>
Answer: <letter>
Explanation: <one line>
---
"""
    try:
        return groq_chat(prompt)
    except ValueError as exc:
        return str(exc)


def generate_flashcards(
    user_id: Optional[int],
    pdf_name: Optional[str] = None,
    specification: Optional[str] = None,
    num_cards: int = 5,
) -> str:
    try:
        context, sources, scope = gather_pdf_context(
            user_id, pdf_name, specification, top_k=14, max_chars=10000
        )
    except ValueError as exc:
        return str(exc)

    if not context.strip():
        return "Please upload a PDF first."

    prompt = f"""
Create {num_cards} study flashcards from the student's PDF.

Scope: {scope}

Rules:
- Short answers (1-2 sentences)
- Only use the provided context
- Cover the most important concepts for the scope

Format:

CARD 1
Q: <question>
A: <answer>

(repeat for each card)

Context:
{context}
"""
    try:
        return groq_chat(prompt)
    except ValueError as exc:
        return str(exc)


def clear_memory(user_id: Optional[int]):
    """Reset conversation memory for a user."""
    key = str(user_id or "global")
    _memory_store[key] = []