# DigitalOcean Deployment Troubleshooting Guide

## Fixed Issues in This Update

### 1. ✅ Port Mismatch Fixed
- **Problem**: `http_port: 8000` but `PORT: "8080"`
- **Solution**: Both now set to `8000`

### 2. ✅ Instance Size Increased
- **Problem**: `basic-xxs` insufficient for OCR processing
- **Solution**: Upgraded to `basic-s` (1GB RAM, 1 vCPU)

### 3. ✅ Build Command Added
- **Problem**: No dependency installation specified
- **Solution**: Added proper build command with system dependencies

### 4. ✅ Memory Optimization
- **Problem**: Heavy dependencies causing memory issues
- **Solution**: 
  - Removed numpy and opencv (memory-heavy)
  - Created `requirements.production.txt` with minimal deps
  - Reduced OCR DPI from 600 to 300
  - Used `/tmp` directories instead of `/app`

### 5. ✅ Startup Script Enhanced
- **Problem**: No graceful startup handling
- **Solution**: Created `start_production.py` with:
  - Directory creation
  - System checks
  - Error handling
  - Resource validation

## Current Configuration

### Instance Resources:
- **Size**: `basic-s` (1GB RAM, 1 vCPU)
- **Cost**: ~$24/month
- **Startup time**: 60 seconds initial delay

### Optimized Settings:
```yaml
OCR_DPI: 300          # Reduced from 600 for memory efficiency
MAX_RETRIES: 2        # Reduced from 3
PROCESS_DELAY: 2      # Reduced from 5
```

### Memory-Efficient Dependencies:
- Removed: numpy, opencv-python, django
- Kept: fastapi, pytesseract, pdf2image, pillow
- Added: python-multipart, aiofiles

## If Deployment Still Fails

### Option 1: Increase Instance Size
```yaml
instance_size_slug: basic-m  # 2GB RAM, 1 vCPU (~$48/month)
```

### Option 2: Use Professional Plan
```yaml
instance_size_slug: professional-xs  # 1GB RAM, 1 vCPU, better performance
```

### Option 3: Simplify Further
Remove image processing entirely and use text-only OCR:

```yaml
envs:
- key: OCR_DPI
  value: "150"  # Even lower DPI
- key: SIMPLE_MODE
  value: "true" # Skip image preprocessing
```

## Monitoring Commands

After deployment, check these endpoints:

```bash
# Health check
curl https://your-app.ondigitalocean.app/health

# Resource stats
curl https://your-app.ondigitalocean.app/stats

# Test upload (small file)
curl -X POST https://your-app.ondigitalocean.app/upload \
  -F "file=@small-test.pdf"
```

## Log Analysis

In DigitalOcean dashboard, look for these error patterns:

### Memory Issues:
```
MemoryError
OOMKilled
Container terminated
Exit code 137
```

### Dependency Issues:
```
ModuleNotFoundError
ImportError
No module named
```

### Timeout Issues:
```
Health check failed
Application startup timeout
Connection refused
```

## Alternative Deployment (If App Platform Fails)

Use a Droplet with Docker:

```bash
# Create 2GB droplet
doctl compute droplet create ocr-engine \
  --size s-1vcpu-2gb \
  --image ubuntu-22-04-x64 \
  --region nyc1

# SSH and deploy
ssh root@droplet-ip
git clone https://github.com/Kojo360/Ocr-engine.git
cd Ocr-engine
docker-compose up -d
```

## Performance Tuning

### For High Volume:
- Use `basic-m` or `professional-xs`
- Add Redis for job queuing
- Implement file size limits
- Add rate limiting

### For Low Resources:
- Set max file size to 5MB
- Disable background processing
- Use synchronous processing only
- Cache OCR results

## Support Escalation

If issues persist:
1. Check DigitalOcean status page
2. Contact DigitalOcean support with app logs
3. Consider alternative platforms (Heroku, Railway, etc.)
4. Use traditional VPS with manual Docker deployment
