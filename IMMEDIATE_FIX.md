# IMMEDIATE FIX for "can't open file '/app/minimal_ocr.py'" Error

## 🚨 Quick Fix Options

### Option 1: Change Run Command (FASTEST FIX)
In your DigitalOcean App Platform settings:

**Current Run Command:** `python minimal_ocr.py`
**Change to:** `python ocr_watcher.py`

This file definitely exists in your repository.

### Option 2: Use Smart Startup (RECOMMENDED)
**Change Run Command to:** `python smart_startup.py`

This will automatically detect which OCR service is available and start it.

### Option 3: Remove Run Command (Let Dockerfile handle it)
**Delete the run command** entirely and let the Dockerfile CMD handle startup.

## 📋 Step-by-Step Fix

1. **Go to your DigitalOcean App Platform dashboard**
2. **Click on your ocr-engine app**
3. **Go to Settings → Components**
4. **Click "Edit" next to your ocr-engine component**
5. **Find "Run Command" field**
6. **Change it to:** `python ocr_watcher.py`
7. **Click "Save"**
8. **Deploy the changes**

## ✅ Alternative: Update via GitHub

I've updated your Dockerfile to use smart startup, so you can also:

1. **Commit and push** the latest changes (I'll do this)
2. **In DigitalOcean, set Run Command to:** `python smart_startup.py`
3. **Or remove Run Command entirely** (let Dockerfile handle it)

## 🔍 Why This Happened

The error occurred because:
- Your run command was set to `python minimal_ocr.py`
- But you're using the main Dockerfile which includes `ocr_watcher.py`
- The `minimal_ocr.py` file exists in your repo but wasn't being copied properly

## 🎯 Recommended Settings After Fix

```
Run Command: python smart_startup.py
Instance Size: basic-s (1GB RAM)
Port: 8000
Environment Variables: (as previously configured)
```

The smart startup will automatically choose the best OCR service based on available files and resources.

## 🚀 Expected Result

After applying the fix, your deployment should:
- ✅ Start successfully
- ✅ Show "Smart Startup" logs
- ✅ Launch the appropriate OCR service
- ✅ Pass health checks at /health endpoint
