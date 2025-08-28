# 🚀 Render Deployment Guide

## ✅ **Issues Fixed:**

1. **Missing gunicorn version** - Added `requests==2.31.0` to requirements.txt
2. **Created render.yaml** - Proper deployment configuration
3. **Created Procfile** - Alternative deployment method
4. **Updated app.py** - Made it deployment-friendly with environment variables

## 🔧 **Required Environment Variables in Render:**

Set these in your Render dashboard under Environment Variables:

```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/hubspot_cpq
MONGODB_DATABASE=hubspot_cpq
FLASK_ENV=production
GOOGLE_OAUTH_CLIENT_SECRET_PATH=path/to/client_secret.json
OAUTH_REDIRECT_URI=https://your-app-name.onrender.com/oauth/callback
OAUTH_SCOPES=https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents
GOOGLE_OAUTH_TOKEN_PATH=token.json
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📋 **Deployment Steps:**

1. **Push your code** to GitHub with the new files
2. **Connect to Render** and select your repository
3. **Set environment variables** as listed above
4. **Deploy** - Render will use the `render.yaml` configuration

## 🐛 **Why gunicorn was "not found":**

- **Missing version** for `requests` dependency
- **No deployment configuration** files
- **App not configured** for production environment

## ✅ **What's Fixed Now:**

- ✅ Proper dependency versions
- ✅ Render deployment configuration
- ✅ Production-ready app.py
- ✅ Environment variable support
- ✅ Health check endpoint

## 🚀 **Deploy Again:**

After pushing these changes, your Render deployment should work correctly!
