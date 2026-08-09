"""RAG: BGE-M3 embeddings + ChromaDB persistent store."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.utils import embedding_functions


CHUNK_SIZE = 1200


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Backward-compat: keep the original signature. Newline collapsing
    and short-chunk filtering live in the reindex path only.
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def _chunk_for_index(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Indexing-time chunker: collapses whitespace and drops tiny chunks
    so ChromaDB doesn't get noise rows from headers/footers.
    """
    txt = text.replace("\n", " ").strip()
    out: List[str] = []
    for i in range(0, len(txt), chunk_size):
        chunk = txt[i:i + chunk_size]
        if len(chunk) > 40:
            out.append(chunk)
    return out


class RAGStore:
    def __init__(self, persist_dir: str, collection_name: str = "techsphere_docs") -> None:
        os.makedirs(persist_dir, exist_ok=True)
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        try:
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
        except TypeError:
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

    def reindex(self, data_dir: str = "") -> Dict:
        """Walk the configured dataset directory and reindex every PDF.

        Returns a summary dict with counts. Clears the existing collection
        first to avoid stale chunks. Reads ``ADMIN_DATA_DIR`` env var when
        ``data_dir`` is not provided.
        """
        from pypdf import PdfReader

        data_dir = data_dir or os.environ.get("ADMIN_DATA_DIR", "dataset/textos")
        root = Path(data_dir)
        if not root.is_dir():
            return {"ok": False, "error": f"data dir not found: {data_dir}", "indexed": 0, "skipped": 0}

        # Drop existing collection so reindex is idempotent
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        indexed = 0
        skipped = 0
        errors: List[str] = []
        for pdf in sorted(root.rglob("*.pdf")):
            try:
                reader = PdfReader(str(pdf))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception as exc:
                errors.append(f"{pdf.name}: {exc}")
                skipped += 1
                continue
            if not text or len(text.strip()) < 40:
                skipped += 1
                continue
            try:
                rel = str(pdf.relative_to(root))
            except ValueError:
                rel = pdf.name
            chunks = []
            for i, chunk in enumerate(_chunk_for_index(text)):
                chunks.append({"id": f"{rel}_{i}", "text": chunk, "source": rel})
            try:
                self.add_documents(chunks)
                indexed += len(chunks)
            except Exception as exc:
                errors.append(f"{pdf.name}: add failed: {exc}")
                skipped += 1

        return {
            "ok": True,
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors[:10],
            "data_dir": data_dir,
            "total_chunks": self._collection.count(),
        }


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
RAGStore.reindex = RAGStore.reindex

