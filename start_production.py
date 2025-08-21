#!/usr/bin/env python3
"""
Production startup script for OCR Engine on DigitalOcean App Platform
Handles resource constraints and graceful startup
"""

import os
import sys
import logging
import time
from pathlib import Path

def setup_logging():
    """Configure logging for production"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        os.getenv('SCAN_DIR', '/tmp/incoming-scan'),
        os.getenv('FULLY_INDEXED_DIR', '/tmp/fully_indexed'),
        os.getenv('PARTIAL_INDEXED_DIR', '/tmp/partially_indexed'),
        os.getenv('FAILED_DIR', '/tmp/failed'),
        '/tmp/logs'
    ]
    
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def check_system_resources():
    """Check if required system tools are available"""
    import shutil
    
    required_tools = {
        'tesseract': os.getenv('TESSERACT_CMD', '/usr/bin/tesseract'),
        'pdfinfo': '/usr/bin/pdfinfo'  # From poppler-utils
    }
    
    for tool, path in required_tools.items():
        if not shutil.which(tool) and not os.path.exists(path):
            logger.error(f"Required tool '{tool}' not found at {path}")
            return False
        logger.info(f"✓ {tool} found")
    
    return True

def start_application():
    """Start the OCR application with error handling"""
    try:
        # Import after ensuring dependencies are ready
        from ocr_watcher import main
        port = os.getenv('PORT', '8000')
        host = os.getenv('HOST', '0.0.0.0')
        logger.info(f"Starting OCR Watcher Service on {host}:{port}...")
        main()
    except ImportError as e:
        logger.error(f"Failed to import OCR modules: {e}")
        logger.error("Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Set up logging first
    logger = setup_logging()
    
    logger.info("🚀 Starting OCR Engine on DigitalOcean...")
    
    # Wait a bit for system to stabilize
    time.sleep(2)
    
    # Ensure directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        sys.exit(1)
    
    # Check system resources
    if not check_system_resources():
        logger.error("System resource check failed")
        sys.exit(1)
    
    # Start the application
    start_application()
