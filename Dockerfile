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

# Health check (respects PORT env, falls back to 8000)
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD sh -c "curl -fsS http://localhost:${PORT:-8000}/health || exit 1"

# Expose default port (App Platform sets PORT env at runtime)
EXPOSE 8000

# Start production server (binds to HOST/PORT from env)
CMD ["python", "start_production.py"]