import os
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

try:
    import aiofiles  # type: ignore
except ImportError:
    aiofiles = None

from config import Config


# Configure logging and ensure directories exist
Config.ensure_directories()
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ocr_watcher")


def _all_dirs() -> List[str]:
    return [
        Config.FULLY_INDEXED_DIR,
        Config.PARTIAL_INDEXED_DIR,
        Config.SCAN_DIR,
        Config.FAILED_DIR,
    ]


def _safe_path_join(root: str, filename: str) -> str:
    dest = os.path.abspath(os.path.join(root, filename))
    root_abs = os.path.abspath(root)
    if not dest.startswith(root_abs + os.sep) and dest != root_abs:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return dest


def _find_file_across_dirs(filename: str) -> Optional[str]:
    for d in _all_dirs():
        candidate = _safe_path_join(d, filename)
        if os.path.exists(candidate):
            return candidate
    return None


def _list_files_in(dir_path: str) -> List[str]:
    try:
        return [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    except FileNotFoundError:
        return []


app = FastAPI(
    title="OCR Watcher Service",
    description="FastAPI service for OCR document processing and file access",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "OCR Watcher Service is running. See /health and /api/files/list."


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
        "scan_dir": Config.SCAN_DIR,
    }


@app.post("/upload")
async def legacy_upload(file: UploadFile = File(...)):
    return await upload_file(file)


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    original_name = file.filename or "uploaded_file"
    dest_path = _safe_path_join(Config.SCAN_DIR, original_name)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        if aiofiles:
            async with aiofiles.open(dest_path, "wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    await out.write(chunk)
        else:
            with open(dest_path, "wb") as out:
                out.write(await file.read())
    finally:
        await file.close()

    logger.info(f"Uploaded file saved to {dest_path}")
    return {"status": "uploaded", "filename": file.filename}


@app.get("/api/files/list")
def list_files(status: Optional[str] = Query(None, description="Optional folder filter: fully|partial|scan|failed")):
    mapping = {
        "fully": Config.FULLY_INDEXED_DIR,
        "partial": Config.PARTIAL_INDEXED_DIR,
        "scan": Config.SCAN_DIR,
        "failed": Config.FAILED_DIR,
    }
    files: List[str] = []
    if status is None:
        for d in _all_dirs():
            files.extend(_list_files_in(d))
    else:
        files.extend(_list_files_in(mapping.get(status, Config.SCAN_DIR)))

    seen = set()
    uniq: List[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


@app.get("/api/files/{filename}")
def get_file(filename: str):
    path = _find_file_across_dirs(filename)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=os.path.basename(path))


@app.get("/api/files/{filename}/metadata")
def get_file_metadata(filename: str):
    path = _find_file_across_dirs(filename)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    st = os.stat(path)
    return {
        "filename": os.path.basename(path),
        "size": st.st_size,
        "modified": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
        "directory": os.path.dirname(path),
    }


@app.post("/trigger-ocr")
def trigger_ocr():
    return {"status": "accepted"}


@app.get("/search")
def search(q: str = Query("", description="Search substring in filenames")):
    term = q.strip().lower()
    if not term:
        return []
    results: List[str] = []
    for d in _all_dirs():
        for f in _list_files_in(d):
            if term in f.lower():
                results.append(f)
    seen = set()
    uniq: List[str] = []
    for f in results:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


@app.get("/stats")
def stats():
    return {
        "scan": len(_list_files_in(Config.SCAN_DIR)),
        "fully_indexed": len(_list_files_in(Config.FULLY_INDEXED_DIR)),
        "partially_indexed": len(_list_files_in(Config.PARTIAL_INDEXED_DIR)),
        "failed": len(_list_files_in(Config.FAILED_DIR)),
    }

@app.get("/_routes")
def list_routes():
    """Diagnostics: list all registered routes (paths & methods) to verify deployed version."""
    routes = []
    for r in app.router.routes:
        path = getattr(r, "path", None)
        if not path:
            continue
        methods = sorted(list(getattr(r, "methods", []))) if getattr(r, "methods", None) else []
        routes.append({
            "path": path,
            "name": getattr(r, "name", None),
            "methods": methods
        })
    routes.sort(key=lambda x: x["path"])
    return {"count": len(routes), "routes": routes}


def main():
    import uvicorn
    logger.info(f"Starting uvicorn on {Config.HOST}:{Config.PORT} with {len(app.router.routes)} registered routes")
    uvicorn.run("ocr_watcher:app", host=Config.HOST, port=Config.PORT, log_level="info")


if __name__ == "__main__":
    main()
