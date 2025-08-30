#!/usr/bin/env python3
"""
Test script for the new generate-and-send endpoint
"""

import requests
import json

def test_generate_and_send():
    """Test the new generate-and-send endpoint"""
    
    # Test data
    test_data = {
        "recipient_email": "test@example.com",  # Change this to a real email for testing
        "recipient_name": "Test User",
        "company_name": "Test Company",
        "service_type": "Migration Services",
        "requirements": "Testing the new endpoint"
    }
    
    print("🚀 Testing new generate-and-send endpoint...")
    print(f"📧 Sending to: {test_data['recipient_email']}")
    print(f"👤 Recipient: {test_data['recipient_name']}")
    print(f"🏢 Company: {test_data['company_name']}")
    
    try:
        # Make the request
        response = requests.post(
            'http://127.0.0.1:5000/api/email/generate-and-send',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"📄 Message: {result.get('message', 'No message')}")
            print(f"📁 PDF Path: {result.get('pdf_path', 'No path')}")
            print(f"📄 Filename: {result.get('filename', 'No filename')}")
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_result = response.json()
                print(f"❌ Error message: {error_result.get('message', 'Unknown error')}")
            except:
                print(f"❌ Response text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure your Flask app is running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Testing New Generate-and-Send Endpoint")
    print("=" * 50)
    print("⚠️  Make sure your Flask app is running first!")
    print("⚠️  Change the email address in the script to test with a real email")
    print("=" * 50)
    
    test_generate_and_send()
    
    print("=" * 50)
    print("✅ Test completed!")
    print("=" * 50)
