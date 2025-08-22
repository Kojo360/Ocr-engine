import os
import time
import shutil
import re
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import logging
from pathlib import Path
from config import Config

# Configure logging
Config.ensure_directories()
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE) if hasattr(Config, 'LOG_FILE') and Config.LOG_FILE else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure OCR tools
pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

# === Retry-safe file move ===
def safe_move_file(src, dest, max_retries=None, delay=None):
    max_retries = max_retries or Config.MAX_RETRIES
    delay = delay or Config.RETRY_DELAY
    
    for attempt in range(1, max_retries + 1):
        try:
            if not os.path.exists(src):
                logger.error(f"Source file {src} does not exist at move attempt {attempt}.")
                return False
            shutil.move(src, dest)
            logger.info(f"Successfully moved {src} to {dest}")
            return True
        except Exception as e:
            logger.error(f"Attempt {attempt} failed moving {src} to {dest}: {e}")
            time.sleep(delay)
    logger.warning(f"Failed to move {src} to {dest} after {max_retries} attempts.")
    return False

# === OCR & Parsing ===
def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            pages = convert_from_path(path, poppler_path=Config.POPPLER_PATH, dpi=Config.DPI)
            return "\n".join(pytesseract.image_to_string(p) for p in pages)
        else:
            img = Image.open(path).convert("RGB")
            return pytesseract.image_to_string(img)
    except Exception as e:
        logger.error(f"Text extraction failed for {path}: {e}")
        return ""

def normalize(val):
    # Lowercase, remove underscores, spaces, punctuation
    return re.sub(r'[^a-z0-9]', '', val.lower())

def parse_fields(text, img_path=None):
    # All possible labels (case-insensitive, with/without colon, underscore, etc.)
    labels = [
        "Name of Account Holder", "First name", "First names", "Surname", "Surnames",
        "Other name", "Other names", "Print name", "Account Name", "Institution Name",
        "Account Number", "Account number", "Account no", "CSD Number", "Client CSD Securities Account No",
        "ID number", "UMB-IHL ID Number", "Name", "Name of Organisation", "Name of Organization"
    ]
    label_norms = set([normalize(l) for l in labels])
    # Build regex for label matching (with/without colon, case-insensitive)
    label_regex = re.compile(rf"({'|'.join([re.escape(l) for l in labels])})\s*:?", re.IGNORECASE)

    # Strong blacklist: all label variants, generic words, and normalized forms
    blacklist = set(label_norms)
    blacklist.update([normalize(x) for x in [
        "Branch", "Account", "Name", "Surname", "Other", "Print", "Institution", "Organization", "Organisation", "No", "Number", "Holder", "CSD", "ID", "Client", "Details", "Purpose", "Period", "Address", "Tel", "E-Mail", "PHOTO", "Reference", "Date", "Relationship", "Employer", "Spouse", "Failed", "Partial", "Indexed", "Fully", "Of", "The", "And", "Or", "As", "It", "Is", "Are", "Was", "Be", "On", "In", "At", "To", "For", "By", "With", "From", "This", "That", "These", "Those", "A", "An", "PDF", "JPG", "PNG", "Doc", "File", "Scan", "Image", "Document", "Page", "Test", "Sample", "Unknown", "Unnamed", "Blank", "Empty", "None", "Null", "Untitled", "Failed", "Partial", "Indexed", "Fully", "Of", "The", "And", "Or", "As", "It", "Is", "Are", "Was", "Be", "On", "In", "At", "To", "For", "By", "With", "From", "This", "That", "These", "Those", "A", "An"]])

    # If image path is provided, use simplified color analysis (no numpy for memory efficiency)
    if img_path:
        try:
            img = Image.open(img_path).convert("RGB")
            # Skip heavy numpy operations for memory efficiency in cloud deployment
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        except Exception as e:
            logger.warning(f"Could not analyze color data for {img_path}: {e}")
            ocr_data = None
    else:
        ocr_data = None
        
    # Split text into lines for context
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        match = label_regex.search(line)
        if match:
            label = match.group(1)
            after_label = line[match.end():].strip()
            # If value is on same line, try to extract all words after label up to next label or end
            value_words = []
            for word in after_label.split():
                nword = normalize(word)
                if nword in label_norms or nword in blacklist:
                    break
                value_words.append(word)
            # If not found, check next line(s) for value
            if not value_words and idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                for word in next_line.split():
                    nword = normalize(word)
                    if nword in label_norms or nword in blacklist:
                        break
                    value_words.append(word)
            # Join all value words
            value = " ".join(value_words).strip()
            
            logger.debug(f"Matched label '{label}' in line: '{line}' -> Value: '{value}'")
            # Final validation: value must not be empty, must not be a label, must not be in blacklist
            nval = normalize(value)
            if value and nval not in blacklist and len(nval) > 2:
                return value, label
            else:
                logger.debug(f"Value '{value}' rejected by blacklist or is empty.")
                
    # If nothing valid found, fail
    logger.debug("No valid value found for any label. Failing job.")
    return None, None

def is_valid_account(val):
    # Only accept if at least 10 digits, and mostly 13 digits
    digits = ''.join([c for c in val if c.isdigit()])
    return len(digits) >= 10 and (len(digits) == 13 or len(digits) >= 10)

# === Routing Logic ===
def route_file(src_path):
    logger.info(f"Starting to route file: {src_path}")
    filename = os.path.basename(src_path)
    ext = os.path.splitext(filename)[1].lower()
    logger.info(f"Processing file: {filename}, extension: {ext}")
    
    text = extract_text(src_path)
    logger.info(f"Extracted text length: {len(text)} characters")
    
    name, name_label = parse_fields(text, src_path)
    account, account_label = None, None
    
    # Try to extract account number if not already found as name
    account_labels = [
        "Account Number", "Account number", "Account no", "CSD Number", "Client CSD Securities Account No", "ID number", "UMB-IHL ID Number"
    ]
    
    # Blacklist from parse_fields
    labels = [
        "Name of Account Holder", "First name", "First names", "Surname", "Surnames",
        "Other name", "Other names", "Print name", "Account Name", "Institution Name",
        "Account Number", "Account number", "Account no", "CSD Number", "Client CSD Securities Account No",
        "ID number", "UMB-IHL ID Number", "Name", "Name of Organisation", "Name of Organization"
    ]
    label_norms = set([normalize(l) for l in labels])
    blacklist = set(label_norms)
    
    for label in account_labels:
        regex = re.compile(rf"{re.escape(label)}\s*:?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
        for line in text.splitlines():
            m = regex.search(line)
            if m:
                val = m.group(1).strip()
                nval = normalize(val)
                if val and nval not in blacklist and len(nval) > 2 and is_valid_account(val):
                    account = val
                    account_label = label
                    logger.debug(f"Account candidate '{val}' from label '{label}' accepted as valid account number.")
                    break
                else:
                    logger.debug(f"Account candidate '{val}' from label '{label}' rejected (blacklist or not valid account number).")
        if account:
            break
            
    # Only fail if both name and account are missing
    if not name and not account:
        logger.error(f"{filename} → {filename} (No valid name or account number found)")
        dest_path = os.path.join(Config.FAILED_DIR, filename)
        safe_move_file(src_path, dest_path)
        return
        
    is_image = ext in [".png", ".jpg", ".jpeg"]
    
    if name and account:
        safe_name = re.sub(r'[\\/:*?"<>|]', '', name)
        safe_account = re.sub(r'[\\/:*?"<>|]', '', account)
        new_filename = f"{safe_name}_{safe_account}.pdf" if is_image else f"{safe_name}_{safe_account}{ext}"
        dest_dir = Config.FULLY_INDEXED_DIR
    elif name or account:
        key = name or account
        safe_key = re.sub(r'[\\/:*?"<>|]', '', key)
        new_filename = f"{safe_key}.pdf" if is_image else f"{safe_key}{ext}"
        dest_dir = Config.PARTIAL_INDEXED_DIR
    else:
        # This should not be reached, but fallback to failed
        new_filename = filename
        dest_dir = Config.FAILED_DIR
        
    dest_path = os.path.join(dest_dir, new_filename)
    base, extn = os.path.splitext(new_filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_dir, f"{base}_{counter}{extn}")
        counter += 1
        
    if dest_dir == Config.FAILED_DIR:
        if safe_move_file(src_path, dest_path):
            logger.info(f"[{dest_dir.upper()}] {filename} → {new_filename}")
        return
        
    if is_image:
        try:
            img = Image.open(src_path).convert("RGB")
            img.save(dest_path, "PDF", resolution=100.0)
            if os.path.exists(src_path):
                os.remove(src_path)
            logger.info(f"[{dest_dir.upper()}] {filename} → {new_filename} (converted to PDF)")
        except Exception as e:
            logger.error(f"Failed to convert {filename} to PDF: {e}")
            if os.path.exists(src_path):
                fallback = os.path.join(Config.FAILED_DIR, filename)
                safe_move_file(src_path, fallback)
                logger.info(f"[FAILED] {filename} → {filename}")
    else:
        if safe_move_file(src_path, dest_path):
            logger.info(f"[{dest_dir.upper()}] {filename} → {new_filename}")

# === Watcher Handler ===
class ScanHandler(FileSystemEventHandler):
    _lock = threading.Lock()
    _timer = None

    def _delayed_batch_process(self):
        with self._lock:
            ScanHandler._timer = None
        logger.info("Starting delayed batch process...")
        time.sleep(Config.PROCESS_DELAY)
        
        files = [f for f in os.listdir(Config.SCAN_DIR) if f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))]
        logger.info(f"Found {len(files)} files to process: {files}")
        
        for fname in files:
            fpath = os.path.join(Config.SCAN_DIR, fname)
            logger.info(f"Processing file: {fpath}")
            if not os.path.isfile(fpath):
                logger.warning(f"File {fpath} is not a file, skipping")
                continue
                
            for attempt in range(10):
                try:
                    if not os.path.isfile(fpath):
                        logger.warning(f"File {fpath} no longer exists at attempt {attempt}")
                        break
                    with open(fpath, 'rb') as f:
                        f.read(1)
                    logger.info(f"Routing file: {fpath}")
                    route_file(fpath)
                    logger.info(f"Successfully processed: {fpath}")
                    break
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed for {fpath}: {e}")
                    time.sleep(0.5)
            else:
                logger.error(f"Failed to process {fpath} after multiple attempts.")

    def _schedule_batch(self):
        with self._lock:
            if ScanHandler._timer is not None:
                ScanHandler._timer.cancel()
            ScanHandler._timer = threading.Timer(Config.BATCH_DELAY, self._delayed_batch_process)
            ScanHandler._timer.start()

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            self._schedule_batch()

    def on_moved(self, event):
        if not event.is_directory:
            logger.info(f"File moved: {event.src_path}")
            self._schedule_batch()

def start_watcher():
    abs_path = os.path.abspath(Config.SCAN_DIR)
    logger.info(f"[WATCHING] {abs_path} → (fully|partial|failed)")
    
    # Process existing files on startup
    existing_files = [f for f in os.listdir(Config.SCAN_DIR) if f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))]
    if existing_files:
        logger.info(f"Processing {len(existing_files)} existing files on startup: {existing_files}")
        for fname in existing_files:
            fpath = os.path.join(Config.SCAN_DIR, fname)
            if os.path.isfile(fpath):
                try:
                    logger.info(f"Processing existing file: {fpath}")
                    route_file(fpath)
                    logger.info(f"Successfully processed existing file: {fpath}")
                except Exception as e:
                    logger.error(f"Failed to process existing file {fpath}: {e}")
    
    obs = Observer()
    obs.schedule(ScanHandler(), path=Config.SCAN_DIR, recursive=False)
    obs.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()

# === FastAPI App ===
from fastapi import FastAPI, Query, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import urllib.parse
import mimetypes

# Import aiofiles conditionally
try:
    import aiofiles
except ImportError:
    logger.warning("aiofiles not available, using synchronous file operations")

app = FastAPI(
    title="OCR Watcher Service",
    description="Microservice for OCR document processing and file watching",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the incoming-scan directory for OCR processing"""
    try:
        # Validate file type
        allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg"]
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not supported. Allowed: {allowed_extensions}"
            )
        
        # Save file to incoming-scan directory
        file_path = os.path.join(Config.SCAN_DIR, file.filename)
        
        # Handle duplicate filenames
        if os.path.exists(file_path):
            base, ext = os.path.splitext(file.filename)
            counter = 1
            while os.path.exists(file_path):
                new_filename = f"{base}_{counter}{ext}"
                file_path = os.path.join(Config.SCAN_DIR, new_filename)
                counter += 1
        
        # Save file (async if aiofiles available, otherwise sync)
        try:
            if 'aiofiles' in globals():
                async with aiofiles.open(file_path, 'wb') as f:
                    content = await file.read()
                    await f.write(content)
            else:
                # Fallback to synchronous file operations
                content = await file.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
        except Exception as e:
            logger.error(f"File save failed: {e}")
            raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")
        
        logger.info(f"File uploaded successfully: {file_path}")
        
        return JSONResponse(content={
            "message": "File uploaded successfully",
            "filename": os.path.basename(file_path),
            "status": "uploaded",
            "processing": "OCR processing will start automatically"
        })
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# --- Compatibility API expected by the Java backend ---
@app.post("/api/files/upload")
async def api_files_upload(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    """Endpoint used by backend: POST /api/files/upload (multipart form, field name 'file')
    This wraps the existing /upload handler and accepts an optional Authorization header.
    """
    if authorization:
        logger.debug(f"Incoming API upload with Authorization header present (len={len(authorization)}).")
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
def api_files_list(authorization: str | None = Header(default=None)):
    """Return a simple JSON array of filenames. The backend expects a String[] by default.
    It returns files from fully_indexed and partially_indexed folders.
    """
    if authorization:
        logger.debug("List called with Authorization header present.")
    results = []
    for folder in [Config.FULLY_INDEXED_DIR, Config.PARTIAL_INDEXED_DIR]:
        try:
            for fname in os.listdir(folder):
                # Only include files (skip directories)
                fpath = os.path.join(folder, fname)
                if os.path.isfile(fpath):
                    results.append(fname)
        except FileNotFoundError:
            logger.debug(f"Directory not found while listing: {folder}")
    # Return unique, sorted list
    unique_sorted = sorted(list(dict.fromkeys(results)))
    return JSONResponse(content=unique_sorted)


@app.get("/api/files/{filename}")
def api_files_download(filename: str, authorization: str | None = Header(default=None)):
    """Download/serve a file by filename. The filename is URL-encoded by the caller; we will unquote it.
    Searches fully_indexed then partially_indexed.
    """
    if authorization:
        logger.debug("Download called with Authorization header present.")
    try:
        safe_name = urllib.parse.unquote(filename)
    except Exception:
        safe_name = filename

    # Look in fully then partial
    candidates = [os.path.join(Config.FULLY_INDEXED_DIR, safe_name), os.path.join(Config.PARTIAL_INDEXED_DIR, safe_name)]
    found = None
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            found = p
            break

    if not found:
        raise HTTPException(status_code=404, detail="file not found")

    # Guess mime type
    mtype, _ = mimetypes.guess_type(found)
    media_type = mtype or "application/octet-stream"
    # Use FileResponse which sets appropriate headers and streams file
    return FileResponse(found, media_type=media_type, filename=os.path.basename(found))


@app.get("/api/files/{filename}/metadata")
def api_files_metadata(filename: str, authorization: str | None = Header(default=None)):
    """Return simple metadata for a file (filename, size, status: fully/partial).
    """
    try:
        safe_name = urllib.parse.unquote(filename)
    except Exception:
        safe_name = filename

    for folder, status in [(Config.FULLY_INDEXED_DIR, "fully_indexed"), (Config.PARTIAL_INDEXED_DIR, "partially_indexed")]:
        p = os.path.join(folder, safe_name)
        if os.path.exists(p) and os.path.isfile(p):
            return JSONResponse(content={
                "filename": safe_name,
                "status": status,
                "size": os.path.getsize(p)
            })
    raise HTTPException(status_code=404, detail="file not found")

@app.post("/trigger-ocr")
async def trigger_ocr():
    """Manually trigger OCR processing for all files in incoming-scan"""
    try:
        files = [f for f in os.listdir(Config.SCAN_DIR) if f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))]
        
        if not files:
            return JSONResponse(content={
                "message": "No files found to process",
                "files_processed": 0
            })
        
        # Process files in background thread
        def process_files():
            for fname in files:
                fpath = os.path.join(Config.SCAN_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        logger.info(f"Manual processing triggered for: {fpath}")
                        route_file(fpath)
                        logger.info(f"Successfully processed: {fpath}")
                    except Exception as e:
                        logger.error(f"Failed to process {fpath}: {e}")
        
        # Start processing in background
        threading.Thread(target=process_files, daemon=True).start()
        
        return JSONResponse(content={
            "message": "OCR processing triggered successfully",
            "files_found": len(files),
            "files": files,
            "status": "processing_started"
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger OCR: {e}")
        raise HTTPException(status_code=500, detail=f"OCR trigger failed: {str(e)}")

@app.get("/search")
def search_files(q: str = Query(..., min_length=1)):
    """Search for processed files by name"""
    results = []
    for folder, status in [
        (Config.FULLY_INDEXED_DIR,   "fully_indexed"),
        (Config.PARTIAL_INDEXED_DIR, "partially_indexed"),
    ]:
        try:
            for fname in os.listdir(folder):
                if q.lower() in fname.lower():
                    results.append({
                        "filename": fname,
                        "status": status,
                        "path": os.path.join(folder, fname)
                    })
        except FileNotFoundError:
            logger.warning(f"Directory {folder} not found")
    return {"results": results}

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "ocr-watcher",
        "tesseract_path": Config.TESSERACT_CMD,
        "poppler_path": Config.POPPLER_PATH
    }

@app.get("/stats")
def get_stats():
    """Get processing statistics"""
    stats = {}
    try:
        stats["incoming"] = len([f for f in os.listdir(Config.SCAN_DIR) if f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))])
        stats["fully_indexed"] = len(os.listdir(Config.FULLY_INDEXED_DIR))
        stats["partially_indexed"] = len(os.listdir(Config.PARTIAL_INDEXED_DIR))
        stats["failed"] = len(os.listdir(Config.FAILED_DIR))
    except FileNotFoundError as e:
        logger.error(f"Directory not found: {e}")
        stats["error"] = str(e)
    return stats
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
    """Main application entry point"""
    logger.info("Starting OCR Watcher Microservice")
    
    # Start watcher in background thread
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    
    # Start FastAPI server
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)

if __name__ == "__main__":
    main()
