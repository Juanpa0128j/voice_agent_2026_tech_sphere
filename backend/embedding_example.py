#!/usr/bin/env python3
"""
Index all PDFs in dataset/textos/ into ChromaDB using BGE-M3 embeddings.

Usage:
    python backend/embedding_example.py --input-dir dataset/textos --chroma-dir backend/chroma

This is what the Docker build runs to pre-populate the vector store.
"""
import argparse
import sys
from pathlib import Path

# Add parent dir to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypdf import PdfReader
from backend.rag import RAGStore

CHUNK_SIZE = 1200


def extract_text_from_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            t = p.extract_text() or ""
            pages.append(t)
        return "\n".join(pages)
    except Exception as e:
        print(f"WARN extract failed {path.name}: {e}")
        return ""


def chunk_text(txt: str, chunk_size: int = CHUNK_SIZE):
    txt = txt.replace("\n", " ").strip()
    for i in range(0, len(txt), chunk_size):
        chunk = txt[i:i + chunk_size]
        if len(chunk) > 40:
            yield chunk


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True)
    p.add_argument("--chroma-dir", required=True)
    args = p.parse_args()

    input_dir = Path(args.input_dir)
    chroma_dir = Path(args.chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    store = RAGStore(persist_dir=str(chroma_dir))
    count = 0

    for pdf in sorted(input_dir.rglob("*.pdf")):
        text = extract_text_from_pdf(pdf)
        if not text or len(text) < 40:
            print(f"skip (no text): {pdf.name}")
            continue
        rel = str(pdf.relative_to(input_dir))
        chunks = []
        for i, chunk in enumerate(chunk_text(text)):
            chunks.append({
                "id": f"{rel}_{i}",
                "text": chunk,
                "source": rel,
            })
        store.add_documents(chunks)
        count += len(chunks)
        print(f"indexed {len(chunks):>3d} chunks: {rel}")

    print(f"\nDONE: {count} chunks indexed in {chroma_dir}")


if __name__ == "__main__":
    main()
