import os
from flask import request

def get_base_url():
    """
    Smart base URL detection for local vs production environments.
    
    Priority order:
    1. APP_BASE_URL environment variable (if manually set)
    2. Render environment detection (automatic)
    3. Local development fallback
    
    Returns:
        str: The appropriate base URL for the current environment
    """
    
    # Priority 1: Check if manually set environment variable
    if os.getenv('APP_BASE_URL'):
        manual_url = os.getenv('APP_BASE_URL').rstrip('/')
        print(f"🔧 Using manually set APP_BASE_URL: {manual_url}")
        return manual_url
    
    # Priority 2: Check if we're on Render
    if os.getenv('RENDER') or os.getenv('RENDER_EXTERNAL_URL'):
        # Try to get the external URL directly from Render
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        if render_url:
            print(f"🚀 Detected Render environment with external URL: {render_url}")
            return render_url.rstrip('/')
        
        # Fallback: construct from service name
        service_name = os.getenv('RENDER_SERVICE_NAME', 'hubspot-cpq-app')
        constructed_url = f"https://{service_name}.onrender.com"
        print(f"🚀 Detected Render environment, constructed URL: {constructed_url}")
        return constructed_url
    
    # Priority 3: Local development fallback
    local_url = "http://localhost:5000"
    print(f"💻 Using local development URL: {local_url}")
    return local_url

def get_current_url():
    """
    Get current request URL (useful for dynamic links).
    
    Returns:
        str: Current request URL or detected base URL
    """
    if request:
        current_url = request.url_root.rstrip('/')
        print(f"🌐 Current request URL: {current_url}")
        return current_url
    return get_base_url()

def get_environment_info():
    """
    Get detailed information about the current environment.
    
    Returns:
        dict: Environment information including detected URLs
    """
    base_url = get_base_url()
    
    return {
        'environment': 'production' if os.getenv('RENDER') else 'development',
        'base_url': base_url,
        'render_info': {
            'is_render': bool(os.getenv('RENDER')),
            'service_name': os.getenv('RENDER_SERVICE_NAME'),
            'external_url': os.getenv('RENDER_EXTERNAL_URL'),
            'render_id': os.getenv('RENDER_ID')
        },
        'detection_method': 'manual' if os.getenv('APP_BASE_URL') else 'automatic'
    }

def validate_url(url):
    """
    Basic URL validation.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if URL appears valid, False otherwise
    """
    if not url:
        return False
    
    # Basic validation - check if it starts with http:// or https://
    return url.startswith(('http://', 'https://'))

def log_environment_detection():
    """
    Log current environment detection for debugging.
    """
    info = get_environment_info()
    print("🔍 Environment Detection Results:")
    print(f"   Environment: {info['environment']}")
    print(f"   Base URL: {info['base_url']}")
    print(f"   Detection Method: {info['detection_method']}")
    print(f"   Render Environment: {info['render_info']['is_render']}")
    if info['render_info']['is_render']:
        print(f"   Service Name: {info['render_info']['service_name']}")
        print(f"   External URL: {info['render_info']['external_url']}")
    print("=" * 50)
