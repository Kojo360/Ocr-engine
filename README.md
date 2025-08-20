# OCR Engine API

A production-ready OCR (Optical Character Recognition) microservice built with FastAPI and Python that provides automatic document processing, file watching, and RESTful API endpoints for team collaboration.

## Features

- **RESTful API**: Upload files and trigger OCR processing via HTTP endpoints
- **Automatic folder watching**: Monitors directories for new documents
- **Multi-format support**: PDF, PNG, JPG, JPEG processing
- **Document classification**: Automatically categorizes processed files
- **Metadata extraction**: Extracts account numbers and names from documents
- **Docker support**: Full containerization for easy deployment
- **Database integration**: MySQL support for document indexing
- **Health monitoring**: Built-in health checks and statistics

## API Endpoints

- `POST /upload` - Upload files for OCR processing
- `POST /trigger-ocr` - Manually trigger OCR processing
- `GET /search?q=query` - Search processed files
- `GET /health` - Health check endpoint
- `GET /stats` - Processing statistics

## Quick Start

### Using Docker Compose (Recommended)

```bash
git clone https://github.com/Kojo360/Ocr-engine.git
cd Ocr-engine
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils

# Windows (using chocolatey)
choco install tesseract poppler
```

3. Run the service:
```bash
python ocr_watcher.py
```

## DigitalOcean Deployment

### Option 1: App Platform (Recommended for teams)

1. **Fork/Clone the repository** to your GitHub account

2. **Create a new app** in DigitalOcean App Platform:
   - Connect your GitHub repository
   - Choose `Ocr-engine` repository
   - Set build command: `pip install -r requirements.txt`
   - Set run command: `python ocr_watcher.py`

3. **Configure environment variables**:
   ```
   HOST=0.0.0.0
   PORT=8080
   TESSERACT_CMD=/usr/bin/tesseract
   POPPLER_PATH=/usr/bin
   ```

4. **Add database** (optional):
   - Add a MySQL database component
   - Configure connection strings in environment variables

5. **Deploy**: App Platform will automatically build and deploy your service

### Option 2: Droplet with Docker

1. **Create a Droplet**:
   ```bash
   # Create a Ubuntu 22.04 droplet (minimum 2GB RAM recommended)
   # SSH into your droplet
   ssh root@your-droplet-ip
   ```

2. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

3. **Install Docker Compose**:
   ```bash
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

4. **Deploy your application**:
   ```bash
   git clone https://github.com/Kojo360/Ocr-engine.git
   cd Ocr-engine
   docker-compose up -d
   ```

5. **Configure firewall**:
   ```bash
   sudo ufw allow 8000
   sudo ufw allow ssh
   sudo ufw --force enable
   ```

### Option 3: Container Registry + App Platform

1. **Build and push to DigitalOcean Container Registry**:
   ```bash
   # Install doctl
   snap install doctl
   doctl auth init
   
   # Create container registry
   doctl registry create ocr-engine-registry
   
   # Build and push image
   docker build -t ocr-engine .
   docker tag ocr-engine registry.digitalocean.com/ocr-engine-registry/ocr-engine:latest
   docker push registry.digitalocean.com/ocr-engine-registry/ocr-engine:latest
   ```

2. **Deploy from registry** in App Platform using the pushed image

## Team Access & Usage

Once deployed, your team can access the OCR engine at your DigitalOcean URL:

### Upload files via API:
```bash
curl -X POST "https://your-app-url.ondigitalocean.app/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Check processing status:
```bash
curl "https://your-app-url.ondigitalocean.app/stats"
```

### Search processed files:
```bash
curl "https://your-app-url.ondigitalocean.app/search?q=account_holder_name"
```

## Configuration

Environment variables for production deployment:

```env
# API Configuration
HOST=0.0.0.0
PORT=8080

# OCR Tools
TESSERACT_CMD=/usr/bin/tesseract
POPPLER_PATH=/usr/bin

# Directory paths (use absolute paths in production)
SCAN_DIR=/app/incoming-scan
FULLY_INDEXED_DIR=/app/fully_indexed
PARTIAL_INDEXED_DIR=/app/partially_indexed
FAILED_DIR=/app/failed

# Database (if using)
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=your-db-name

# Processing settings
OCR_DPI=600
MAX_RETRIES=3
RETRY_DELAY=1.0
BATCH_DELAY=0.5
PROCESS_DELAY=5
```

## File Structure

```
├── config.py              # Configuration settings
├── ocr_watcher.py         # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Multi-service orchestration
├── start.bat             # Windows startup script
├── start.sh              # Unix startup script
├── incoming-scan/        # Upload directory
├── fully_indexed/        # Successfully processed files
├── partially_indexed/    # Partially processed files
└── failed/              # Failed processing files
```

## Monitoring & Logs

- **Health endpoint**: `GET /health` - Check service status
- **Statistics**: `GET /stats` - View processing metrics
- **Logs**: Use `docker-compose logs ocr_watcher` to view logs

## Scaling on DigitalOcean

For high-volume processing:

1. **Vertical scaling**: Increase droplet size (more CPU/RAM)
2. **Horizontal scaling**: Use load balancer with multiple app instances
3. **Managed database**: Use DigitalOcean Managed MySQL for better performance
4. **Spaces**: Use DigitalOcean Spaces for file storage

## Cost Estimation

**App Platform**: ~$12-25/month (basic plan)
**Droplet**: ~$24/month (4GB RAM, 2 vCPUs)
**Managed Database**: ~$15/month (basic MySQL)
**Load Balancer**: ~$12/month (if needed)

## Security Considerations

- Use environment variables for sensitive data
- Enable HTTPS (automatic with App Platform)
- Configure firewall rules properly
- Regular security updates for base images
- Consider adding API authentication for production

## Troubleshooting

- **Out of memory**: Increase droplet size or limit concurrent processing
- **Slow OCR**: Reduce DPI settings or optimize image preprocessing
- **File upload issues**: Check file size limits and disk space
- **Database connection**: Verify database credentials and network access

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.