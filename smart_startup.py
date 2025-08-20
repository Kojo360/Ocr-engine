#!/usr/bin/env python3
"""
Smart startup script that chooses the best OCR service based on available files
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting OCR Engine - Smart Startup")
    
    # Check which files are available and start the appropriate service
    if os.path.exists('/app/minimal_ocr.py'):
        logger.info("Found minimal_ocr.py - Starting minimal OCR service")
        os.system('python /app/minimal_ocr.py')
    elif os.path.exists('/app/ocr_watcher.py'):
        logger.info("Found ocr_watcher.py - Starting full OCR service")
        os.system('python /app/ocr_watcher.py')
    elif os.path.exists('minimal_ocr.py'):
        logger.info("Found minimal_ocr.py in current directory - Starting minimal OCR service")
        os.system('python minimal_ocr.py')
    elif os.path.exists('ocr_watcher.py'):
        logger.info("Found ocr_watcher.py in current directory - Starting full OCR service")
        os.system('python ocr_watcher.py')
    else:
        logger.error("❌ No OCR service files found!")
        logger.error("Available files:")
        for file in os.listdir('.'):
            if file.endswith('.py'):
                logger.error(f"  - {file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
