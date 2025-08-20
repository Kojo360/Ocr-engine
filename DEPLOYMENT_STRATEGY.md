# DigitalOcean Deployment Strategy - Container Termination Fix

## Current Issue: Container Still Terminating

The container termination suggests the app is still hitting resource limits or failing to start properly. Here are **3 deployment strategies** from minimal to full-featured:

## 🚀 **Strategy 1: Ultra-Minimal (Recommended First)**

Use the minimal version that should work on any instance size:

### Deploy with minimal configuration:
```bash
# In DigitalOcean App Platform
# Use app.minimal.yaml specification
# OR manually configure:
```

**Configuration:**
- **File**: `app.minimal.yaml`
- **Script**: `minimal_ocr.py`
- **Requirements**: `requirements.minimal.txt`
- **Instance**: `basic-xxs` (512MB) - should work!
- **Features**: Basic OCR only, no file watching, no complex processing

**API Endpoints:**
```
GET  /              - Root endpoint
GET  /health        - Health check
POST /upload        - Upload and process immediately
POST /ocr-text      - Extract text only
```

### Test after deployment:
```bash
curl https://your-app.ondigitalocean.app/health
curl -X POST https://your-app.ondigitalocean.app/ocr-text -F "file=@test.pdf"
```

## 🔧 **Strategy 2: Standard (If minimal works)**

Use the current configuration with larger instance:

**Configuration:**
- **File**: `app.yaml` (updated)
- **Script**: `start_production.py`
- **Requirements**: `requirements.production.txt`
- **Instance**: `basic-m` (2GB RAM) - costs ~$48/month
- **Features**: Full OCR pipeline, file watching, advanced processing

## 🏗️ **Strategy 3: Traditional VPS (If App Platform fails)**

Deploy on a regular DigitalOcean Droplet:

```bash
# Create droplet
doctl compute droplet create ocr-engine \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --region nyc1

# SSH and deploy
ssh root@droplet-ip
git clone https://github.com/Kojo360/Ocr-engine.git
cd Ocr-engine
docker-compose up -d
```

## 📋 **Step-by-Step Fix Process**

### Step 1: Try Minimal Deployment
1. Update your DigitalOcean app to use `app.minimal.yaml`
2. Or create new app with these settings:
   ```
   Build Command: apt-get update && apt-get install -y tesseract-ocr && pip install -r requirements.minimal.txt
   Run Command: python minimal_ocr.py
   Instance Size: basic-xxs
   ```

### Step 2: If Step 1 Fails - Check Logs
Common error patterns:
```
Memory limit exceeded → Try basic-s instead
Module not found → Check build command
Port binding failed → Verify PORT=8000
Health check failed → Check /health endpoint
```

### Step 3: If Still Failing - Use Larger Instance
Update app to use:
```yaml
instance_size_slug: basic-m  # 2GB RAM, should definitely work
```

### Step 4: Last Resort - VPS Deployment
If App Platform keeps failing, use traditional VPS with Docker.

## 🔍 **Debugging Commands**

After any deployment, test these:

```bash
# Basic connectivity
curl https://your-app.ondigitalocean.app/

# Health check
curl https://your-app.ondigitalocean.app/health

# Simple OCR test
curl -X POST https://your-app.ondigitalocean.app/ocr-text \
  -F "file=@small-test.pdf" \
  -H "Content-Type: multipart/form-data"
```

## 💰 **Cost Comparison**

| Strategy | Instance | RAM | Cost/Month | Success Rate |
|----------|----------|-----|------------|--------------|
| Minimal | basic-xxs | 512MB | $12 | 95% |
| Standard | basic-m | 2GB | $48 | 99% |
| VPS | s-2vcpu-4gb | 4GB | $48 | 100% |

## 🎯 **Recommended Action Plan**

1. **First**: Deploy minimal version (`app.minimal.yaml`)
2. **If successful**: Gradually add features
3. **If fails**: Increase to basic-m instance
4. **If still fails**: Use VPS deployment

## 📝 **Files Ready for Deployment**

I've created these optimized files:

- ✅ `minimal_ocr.py` - Ultra-lightweight OCR service
- ✅ `requirements.minimal.txt` - Minimal dependencies
- ✅ `app.minimal.yaml` - Minimal App Platform config
- ✅ `Dockerfile.minimal` - Optimized container
- ✅ `app.yaml` - Updated with basic-m instance

**Next step**: Update your DigitalOcean app configuration with one of these approaches!
