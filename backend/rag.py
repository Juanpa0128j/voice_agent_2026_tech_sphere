"""RAG: BGE-M3 embeddings + ChromaDB persistent store."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.utils import embedding_functions


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


class RAGStore:
    def __init__(self, persist_dir: str, collection_name: str = "techsphere_docs") -> None:
        os.makedirs(persist_dir, exist_ok=True)
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3"
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, docs: List[Dict]) -> None:
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict] = []
        for doc in docs:
            chunks = chunk_text(doc["text"])
            for i, chunk in enumerate(chunks):
                ids.append(f"{doc['id']}_{i}")
                texts.append(chunk)
                metadatas.append({
                    "doc_id": doc["id"],
                    "source": doc["source"],
                    "chunk_index": i,
                })
        if ids:
            self._collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def delete_document(self, doc_id: str) -> bool:
        existing = self._collection.get(include=[], where={"doc_id": doc_id})
        if not existing.get("ids"):
            return False
        self._collection.delete(where={"doc_id": doc_id})
        return True

    def query(self, query_text: str, k: int = 5) -> List[Dict]:
        if self._collection.count() == 0:
            return []
        raw = self._collection.query(query_texts=[query_text], n_results=k)
        out: List[Dict] = []
        ids = raw.get("ids") or []
        if not ids or not ids[0]:
            return out
        for i, _ in enumerate(ids[0]):
            meta = raw["metadatas"][0][i] or {}
            distance = raw["distances"][0][i]
            out.append({
                "id": meta.get("doc_id"),
                "text": raw["documents"][0][i],
                "source": meta.get("source", ""),
                "score": 1.0 - distance,
            })
        return out


def retrieve_context(
    store: RAGStore,
    query: str,
    k: int = 5,
    score_threshold: float = 0.3,
) -> List[Dict]:
    results = store.query(query, k=k)
    return [r for r in results if r.get("score", 0.0) >= score_threshold]


def _list_documents(self):
    try:
        results = self._collection.get(include=["metadatas"])
        seen = {}
        for mid, meta in zip(results.get("ids", []), results.get("metadatas", [])):
            meta = meta or {}
            # Group chunks by source (e.g. "Appendicitis/foo.pdf") so one doc
            # in the corpus = one row in the admin list
            source = meta.get("source", mid)
            if source not in seen:
                seen[source] = {
                    "doc_id": source,
                    "source": source,
                    "name": Path(source).name if "/" in source else source,
                }
        return list(seen.values())
    except Exception:
        return []


def _retrieve_facade(self, query_text: str, k: int = 5):
    return self.query(query_text, k=k)


def _add_document_facade(self, doc_id: str, text: str, metadata: dict = None):
    meta = metadata or {}
    self.add_documents([{
        "id": doc_id,
        "text": text,
        "source": meta.get("source", doc_id),
        "doc_id": doc_id,
        "name": meta.get("filename", doc_id),
    }])
    return doc_id


RAGStore.list_documents = _list_documents
RAGStore.retrieve = _retrieve_facade
RAGStore.add_document = _add_document_facade
