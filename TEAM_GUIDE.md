# Quick Team Setup Guide - OCR Engine on DigitalOcean

## For Team Leaders (Deployment)

### Option 1: One-Click Deploy (Easiest)
1. Go to DigitalOcean App Platform
2. Click "Create App"
3. Connect GitHub and select `Kojo360/Ocr-engine`
4. Use the `app.yaml` spec file in the repo
5. Deploy and share the URL with your team

### Option 2: Using the Deploy Script
```bash
git clone https://github.com/Kojo360/Ocr-engine.git
cd Ocr-engine
chmod +x deploy-digitalocean.sh
./deploy-digitalocean.sh
```

## For Team Members (Usage)

Once deployed, you'll get a URL like: `https://your-app-name.ondigitalocean.app`

### 1. Upload Documents via API

**Using curl:**
```bash
curl -X POST "https://your-app-name.ondigitalocean.app/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

**Using Python:**
```python
import requests

url = "https://your-app-name.ondigitalocean.app/upload"
files = {"file": open("document.pdf", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

**Using JavaScript/Fetch:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('https://your-app-name.ondigitalocean.app/upload', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

### 2. Check Processing Status
```bash
curl "https://your-app-name.ondigitalocean.app/stats"
```

### 3. Search Processed Files
```bash
curl "https://your-app-name.ondigitalocean.app/search?q=client_name"
```

### 4. Health Check
```bash
curl "https://your-app-name.ondigitalocean.app/health"
```

## API Response Examples

### Upload Response
```json
{
    "message": "File uploaded successfully",
    "filename": "document.pdf",
    "status": "uploaded",
    "processing": "OCR processing will start automatically"
}
```

### Stats Response
```json
{
    "incoming": 2,
    "fully_indexed": 15,
    "partially_indexed": 3,
    "failed": 1
}
```

### Search Response
```json
{
    "results": [
        {
            "filename": "john_doe_12345.pdf",
            "status": "fully_indexed",
            "path": "/app/fully_indexed/john_doe_12345.pdf"
        }
    ]
}
```

## Common Issues & Solutions

**Upload fails:**
- Check file format (PDF, PNG, JPG, JPEG only)
- Ensure file size is reasonable (<50MB)

**No processing results:**
- Documents may be in "failed" folder if OCR couldn't extract text
- Check logs via App Platform dashboard

**Slow processing:**
- Processing time depends on document size and complexity
- Check stats endpoint to monitor progress

## Integration Examples

### Web Form Integration
```html
<form id="uploadForm" enctype="multipart/form-data">
    <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg" required>
    <button type="submit">Upload for OCR</button>
</form>

<script>
document.getElementById('uploadForm').onsubmit = async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    try {
        const response = await fetch('https://your-app-name.ondigitalocean.app/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        alert('Upload successful: ' + result.message);
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }
};
</script>
```

### Batch Processing Script
```python
import os
import requests
from pathlib import Path

API_BASE = "https://your-app-name.ondigitalocean.app"

def upload_folder(folder_path):
    """Upload all PDF files in a folder"""
    folder = Path(folder_path)
    for file_path in folder.glob("*.pdf"):
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{API_BASE}/upload", files=files)
            print(f"{file_path.name}: {response.json()}")

# Usage
upload_folder("/path/to/documents")
```

## Monitoring & Maintenance

- **Health Check**: Monitor `https://your-app-name.ondigitalocean.app/health`
- **Logs**: Check App Platform dashboard for detailed logs
- **Stats**: Regular monitoring of `/stats` endpoint
- **Scaling**: Increase instance size if processing is slow

## Support

- Check the main README.md for detailed documentation
- Review logs in DigitalOcean App Platform dashboard
- Contact team lead for deployment issues
