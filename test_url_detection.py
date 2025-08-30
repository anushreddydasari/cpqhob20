#!/usr/bin/env python3
"""
Test script for the Automatic URL Detection System
This script tests the smart URL detection functionality
"""

import os
import sys
import requests
import json

def test_url_detection():
    """Test the URL detection system"""
    
    print("🚀 Testing Automatic URL Detection System")
    print("=" * 60)
    
    # Test 1: Check if the system info endpoint is accessible
    print("\n1. Testing System Info Endpoint...")
    try:
        response = requests.get('http://localhost:5000/api/system/info')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ System Info endpoint working")
                env_info = data['data']
                print(f"   Environment: {env_info['environment']}")
                print(f"   Base URL: {env_info['base_url']}")
                print(f"   Detection Method: {env_info['detection_method']}")
                print(f"   Render Environment: {env_info['render_info']['is_render']}")
            else:
                print(f"❌ System Info endpoint error: {data.get('message')}")
        else:
            print(f"❌ System Info endpoint returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing System Info endpoint: {e}")
    
    # Test 2: Check if URL helper module is accessible
    print("\n2. Testing URL Helper Module...")
    try:
        # Add the utils directory to the path
        sys.path.append('utils')
        from url_helper import get_base_url, get_environment_info, log_environment_detection
        
        print("✅ URL Helper module imported successfully")
        
        # Test base URL detection
        base_url = get_base_url()
        print(f"   Detected Base URL: {base_url}")
        
        # Test environment info
        env_info = get_environment_info()
        print(f"   Environment: {env_info['environment']}")
        print(f"   Render Info: {env_info['render_info']}")
        
        # Test logging
        print("   Testing environment detection logging...")
        log_environment_detection()
        
    except ImportError as e:
        print(f"❌ URL Helper module import failed: {e}")
    except Exception as e:
        print(f"❌ Error testing URL Helper module: {e}")
    
    # Test 3: Check if email service can use the URL helper
    print("\n3. Testing Email Service Integration...")
    try:
        # Test if email service can import URL helper
        sys.path.append('cpq')
        from email_service import EmailService
        
        print("✅ Email Service imported successfully")
        
        # Create a test workflow data
        test_workflow = {
            '_id': 'test_workflow_123',
            'document_type': 'PDF',
            'document_id': 'test_doc_456',
            'client_name': 'Test Client',
            'company_name': 'Test Company',
            'created_at': '2024-01-01',
            'priority': 'Normal'
        }
        
        # Test the email body creation (this will test URL detection)
        email_service = EmailService()
        html_body = email_service._create_approval_email_body('manager', test_workflow, 'test@example.com')
        
        if 'localhost' in html_body:
            print("⚠️ Email contains localhost links (expected in local development)")
        else:
            print("✅ Email contains production URLs")
            
        print("   Email service integration working")
        
    except ImportError as e:
        print(f"❌ Email Service import failed: {e}")
    except Exception as e:
        print(f"❌ Error testing Email Service integration: {e}")
    
    print("\n🎯 URL Detection System Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_url_detection()
