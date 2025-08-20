#!/usr/bin/env python3
"""
Ultra-lightweight OCR API for DigitalOcean App Platform
Minimal resource usage, basic OCR functionality only
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Set up minimal logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Minimal configuration
class MinimalConfig:
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
    
    @classmethod
    def ensure_temp_dirs(cls):
        """Ensure temp directories exist"""
        temp_dirs = ['/tmp/ocr-uploads', '/tmp/ocr-results']
        for directory in temp_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Basic OCR function
def extract_text_simple(file_path):
    """Simple text extraction without heavy dependencies"""
    try:
        import pytesseract
        from PIL import Image
        
        # For images
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)
        
        # For PDFs - use basic conversion
        elif file_path.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path, dpi=150, first_page=1, last_page=1)  # Only first page
                if pages:
                    return pytesseract.image_to_string(pages[0])
            except ImportError:
                logger.warning("pdf2image not available, skipping PDF processing")
                return "PDF processing not available in minimal mode"
        
        return ""
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return f"OCR processing failed: {str(e)}"

# Minimal FastAPI app
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="OCR Engine - Minimal",
    description="Lightweight OCR service for basic text extraction",
    version="1.0.0-minimal"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "OCR Engine Minimal - Ready", "status": "ok"}

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ocr-minimal",
        "tesseract_available": os.path.exists(MinimalConfig.TESSERACT_CMD)
    }

@app.post("/upload")
async def upload_and_process(file: UploadFile = File(...)):
    """Upload and immediately process file with basic OCR"""
    try:
        # Validate file type
        allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg"]
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not supported. Allowed: {allowed_extensions}"
            )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Extract text
            extracted_text = extract_text_simple(temp_path)
            
            # Basic name extraction (very simple)
            lines = extracted_text.split('\n')
            potential_name = ""
            for line in lines:
                line = line.strip()
                if len(line) > 3 and len(line) < 50:  # Reasonable name length
                    potential_name = line
                    break
            
            return {
                "status": "completed",
                "filename": file.filename,
                "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
                "potential_name": potential_name,
                "text_length": len(extracted_text)
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/ocr-text")
async def extract_text_only(file: UploadFile = File(...)):
    """Simple endpoint that just returns extracted text"""
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            text = extract_text_simple(temp_path)
            return {"text": text}
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Start the minimal OCR service"""
    logger.info("🚀 Starting OCR Engine - Minimal Mode")
    
    # Ensure temp directories
    MinimalConfig.ensure_temp_dirs()
    
    # Check if tesseract is available
    if not os.path.exists(MinimalConfig.TESSERACT_CMD):
        logger.warning(f"Tesseract not found at {MinimalConfig.TESSERACT_CMD}")
    else:
        logger.info("✓ Tesseract found")
    
    # Start server
    uvicorn.run(
        app, 
        host=MinimalConfig.HOST, 
        port=MinimalConfig.PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()
