"""Administration API skeleton (FastAPI) to upload/delete documents and trigger reindexing.
This is a lightweight skeleton: it does not require running here. Use as a starting point.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil

app = FastAPI(title='Admin Console (skeleton)')

DATA_DIR = Path('dataset/textos')
UPLOADED_DIR = Path('dataset/textos_uploaded')
UPLOADED_DIR.mkdir(exist_ok=True)


@app.post('/admin/upload')
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF allowed')
    dest = UPLOADED_DIR / file.filename
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    # In a real implementation: trigger async reindex of this document
    return JSONResponse({'ok': True, 'path': str(dest)})


@app.post('/admin/delete')
async def delete_document(filename: str):
    p = UPLOADED_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail='Not found')
    p.unlink()
    # In real implementation: trigger removal from vector index
    return JSONResponse({'ok': True})


@app.post('/admin/reindex')
async def reindex():
    # placeholder: kick off reindex job
    return JSONResponse({'ok': True, 'message': 'reindex started (placeholder)'})
