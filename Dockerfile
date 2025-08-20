FROM python:3.13.4-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements*.txt ./

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (try production first, fallback to main)
RUN if [ -f requirements.production.txt ]; then \
        pip install --no-cache-dir -r requirements.production.txt; \
    elif [ -f requirements.minimal.txt ]; then \
        pip install --no-cache-dir -r requirements.minimal.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy all application files
COPY . .

# Make sure all Python files are executable
RUN chmod +x *.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD curl -f http://localhost:8000/health || exit 1

# Use smart startup that detects available files
CMD ["python", "smart_startup.py"]