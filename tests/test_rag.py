"""Tests for RAG: BGE-M3 embeddings + ChromaDB retrieval."""
import pytest
from backend.rag import RAGStore, retrieve_context, chunk_text


def test_chunk_text_splits_long_text():
    text = "A" * 2500
    chunks = chunk_text(text, chunk_size=1000)
    assert len(chunks) == 3


def test_chunk_text_handles_short_text():
    text = "Hola mundo"
    chunks = chunk_text(text, chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == "Hola mundo"


def test_rag_store_initialization(tmp_path):
    store = RAGStore(persist_dir=str(tmp_path / "chroma"))
    assert store is not None
    assert store.collection_name == "techsphere_docs"


def test_rag_store_add_and_query(tmp_path):
    store = RAGStore(persist_dir=str(tmp_path / "chroma"))
    docs = [
        {"id": "d1", "text": "La apendicitis es una inflamación del apéndice.", "source": "test.pdf"},
        {"id": "d2", "text": "El dolor abdominal es síntoma común.", "source": "test2.pdf"},
    ]
    store.add_documents(docs)
    results = store.query("dolor de apéndice", k=2)
    assert len(results) == 2
    assert results[0]["id"] in ["d1", "d2"]


def test_rag_store_delete_document(tmp_path):
    store = RAGStore(persist_dir=str(tmp_path / "chroma"))
    docs = [{"id": "del1", "text": "Texto a eliminar", "source": "x.pdf"}]
    store.add_documents(docs)
    store.delete_document("del1")
    results = store.query("Texto a eliminar", k=1)
    assert len(results) == 0 or results[0]["id"] != "del1"


def test_retrieve_context_threshold(tmp_path):
    store = RAGStore(persist_dir=str(tmp_path / "chroma"))
    store.add_documents([
        {"id": "r1", "text": "Información sobre fiebre postoperatoria", "source": "a.pdf"},
    ])
    results = retrieve_context(store, "síntomas de alarma", k=3, score_threshold=0.3)
    assert isinstance(results, list)
