#!/usr/bin/env python3
"""
Simple embedding & optional Qdrant uploader example.
Usage:
  python backend/embedding_example.py --input-dir dataset/textos --out-dir ./backend/output
"""
import argparse
import os
from pathlib import Path
import json

from sentence_transformers import SentenceTransformer
import numpy as np

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import VectorParams, Distance
except Exception:
    QdrantClient = None

CHUNK_SIZE = 1200


def extract_text_from_pdf(path: Path) -> str:
    if PdfReader is None:
        with open(path, 'rb') as f:
            return ''
    try:
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            t = p.extract_text() or ''
            pages.append(t)
        return '\n'.join(pages)
    except Exception:
        return ''


def chunk_text(txt: str, chunk_size=CHUNK_SIZE):
    txt = txt.replace('\n', ' ').strip()
    for i in range(0, len(txt), chunk_size):
        yield txt[i:i+chunk_size]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--qdrant-host', default=None)
    p.add_argument('--collection', default='techsphere_docs')
    args = p.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer('all-MiniLM-L6-v2')

    docs = []
    for pdf in sorted(input_dir.rglob('*.pdf')):
        txt = extract_text_from_pdf(pdf)
        if not txt or len(txt) < 40:
            print('Skipping (no text):', pdf)
            continue
        for i,chunk in enumerate(chunk_text(txt)):
            docs.append({'id': f"{pdf.stem}_{i}", 'text': chunk, 'source': str(pdf)})

    texts = [d['text'] for d in docs]
    print(f'Found {len(texts)} chunks, computing embeddings...')
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    # save locally
    np.save(out_dir / 'embeddings.npy', embeddings)
    with open(out_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print('Saved embeddings and metadata to', out_dir)

    # optional: push to Qdrant
    if args.qdrant_host and QdrantClient is not None:
        client = QdrantClient(host=args.qdrant_host)
        dim = embeddings.shape[1]
        try:
            client.recreate_collection(collection_name=args.collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
        except Exception:
            pass
        points = []
        for i, e in enumerate(embeddings):
            points.append({'id': i, 'vector': e.tolist(), 'payload': {'meta': docs[i]}})
        client.upsert(collection_name=args.collection, points=points)
        print('Uploaded vectors to Qdrant at', args.qdrant_host)
    elif args.qdrant_host:
        print('qdrant-client not installed in this environment; install to enable upload.')


if __name__ == '__main__':
    main()
