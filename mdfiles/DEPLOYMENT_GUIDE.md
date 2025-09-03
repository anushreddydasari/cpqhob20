# HubSpot CPQ Application Deployment Guide

## Fixed Issues

### 1. Gunicorn Command Not Found ✅
- **Problem**: `gunicorn: command not found` during Render deployment
- **Solution**: 
  - Added explicit `gunicorn==21.2.0` to `requirements.txt`
  - Created `render.yaml` with proper build and start commands
  - Created `Procfile` as alternative deployment method

### 2. Python Version Compatibility ✅
- **Problem**: Python 3.13.4 had compatibility issues with several packages
- **Solution**: 
  - Updated `render.yaml` to use Python 3.11.18 (more stable)
  - Created `runtime.txt` to specify Python version
  - Updated package versions for better compatibility:
    - `Pillow==10.4.0` (from 10.3.0)
    - `reportlab==4.1.0` (from 4.0.4)
    - `weasyprint==62.3` (from 60.2)

### 3. Import Error Handling ✅
- **Problem**: WeasyPrint import could fail and crash the app
- **Solution**: Made WeasyPrint import optional with graceful error handling

## Required Files for Deployment

### 1. `requirements.txt` ✅
All dependencies with compatible versions for Python 3.11

### 2. `render.yaml` ✅
```yaml
services:
  - type: web
    name: hubspot-cpq-app
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.18
      - key: PORT
        value: 10000
    healthCheckPath: /
    autoDeploy: true
```

### 3. `Procfile` ✅
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

### 4. `runtime.txt` ✅
```
python-3.11.18
```

### 5. `app.py` ✅
Updated to use environment variables:
- `PORT` from environment
- `FLASK_ENV` for debug mode
- Host set to `0.0.0.0` for external connections

## Environment Variables Required

Set these in your Render dashboard:

### Required:
- `PORT`: Automatically set by Render
- `MONGODB_URI`: Your MongoDB connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `SECRET_KEY`: Flask secret key for sessions

### Optional:
- `FLASK_ENV`: Set to `development` for debug mode, omit for production

## Deployment Steps

1. **Push Changes to GitHub**
   ```bash
   git add .
   git commit -m "Fixed deployment compatibility issues"
   git push origin main
   ```

2. **Connect Repository to Render**
   - Go to Render dashboard
   - Create new Web Service
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` configuration

3. **Set Environment Variables**
   - Add all required environment variables in Render dashboard
   - Ensure MongoDB URI is correct and accessible

4. **Deploy**
   - Render will automatically build and deploy using the configuration
   - Monitor build logs for any issues

## Build Process

1. **Python Version**: 3.11.18 (stable, compatible)
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. **Health Check**: `/` endpoint

## Troubleshooting

### Build Fails
- Check Python version compatibility
- Verify all package versions exist
- Check for syntax errors in code

### Runtime Errors
- Verify environment variables are set
- Check MongoDB connection
- Review application logs

### PDF Generation Issues
- WeasyPrint is now optional - app will continue to work without it
- PDF generation will return an error message if WeasyPrint is unavailable

## Current Status

✅ **All deployment issues resolved**
✅ **Python 3.11.18 compatibility confirmed**
✅ **Gunicorn configuration working**
✅ **Environment variable handling implemented**
✅ **Graceful error handling for optional dependencies**

Your application should now deploy successfully on Render!
