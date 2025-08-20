"""
Additional API endpoints for enhanced backend integration
Add these to your ocr_watcher.py for even better backend integration
"""

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer
import jwt
import os

# Optional: Add API Key authentication
API_KEY = os.getenv('API_KEY', 'your-secret-api-key')

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Add to your FastAPI app:

@app.post("/process-sync")
async def process_file_sync(file: UploadFile = File(...), authenticated: bool = Depends(verify_api_key)):
    """
    Synchronous OCR processing - processes file immediately and returns results
    Perfect for backend integration where you need immediate results
    """
    try:
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process immediately
        text = extract_text(temp_path)
        name, name_label = parse_fields(text, temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return {
            "status": "completed",
            "extracted_text": text[:500] + "..." if len(text) > 500 else text,
            "extracted_name": name,
            "name_label": name_label,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Sync processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/status/{filename}")
async def get_file_status(filename: str, authenticated: bool = Depends(verify_api_key)):
    """
    Check the processing status of a specific file
    Returns which folder it ended up in (fully_indexed, partially_indexed, failed)
    """
    folders = {
        "fully_indexed": Config.FULLY_INDEXED_DIR,
        "partially_indexed": Config.PARTIAL_INDEXED_DIR,
        "failed": Config.FAILED_DIR,
        "pending": Config.SCAN_DIR
    }
    
    for status, folder in folders.items():
        files = os.listdir(folder)
        # Check for exact match or files that start with the original filename
        for file in files:
            if file == filename or file.startswith(os.path.splitext(filename)[0]):
                return {
                    "filename": filename,
                    "status": status,
                    "processed_filename": file,
                    "path": os.path.join(folder, file)
                }
    
    return {"filename": filename, "status": "not_found"}

@app.post("/webhook")
async def webhook_endpoint(webhook_url: str = Header(None), authenticated: bool = Depends(verify_api_key)):
    """
    Register a webhook URL to be notified when OCR processing completes
    Your backend can register to receive notifications
    """
    # Store webhook URL (in production, use a database)
    # When processing completes, send POST request to webhook_url
    return {"message": "Webhook registered", "url": webhook_url}

@app.get("/results/{filename}")
async def get_processing_results(filename: str, authenticated: bool = Depends(verify_api_key)):
    """
    Get detailed processing results for a file including extracted metadata
    """
    # Search for the file in processed folders
    folders = [
        (Config.FULLY_INDEXED_DIR, "fully_indexed"),
        (Config.PARTIAL_INDEXED_DIR, "partially_indexed")
    ]
    
    for folder, status in folders:
        try:
            files = os.listdir(folder)
            for file in files:
                if file.startswith(os.path.splitext(filename)[0]):
                    file_path = os.path.join(folder, file)
                    
                    # Extract metadata from filename (assuming format: name_account.ext)
                    base_name = os.path.splitext(file)[0]
                    parts = base_name.split('_')
                    
                    result = {
                        "original_filename": filename,
                        "processed_filename": file,
                        "status": status,
                        "file_path": file_path,
                        "processed_at": os.path.getctime(file_path)
                    }
                    
                    if len(parts) >= 2:
                        result["extracted_name"] = '_'.join(parts[:-1])
                        result["extracted_account"] = parts[-1]
                    
                    return result
        except FileNotFoundError:
            continue
    
    raise HTTPException(status_code=404, detail="File not found or not processed")
