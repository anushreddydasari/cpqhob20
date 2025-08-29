#!/usr/bin/env python3
"""
Test script for client feedback functionality
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "test@example.com"

def test_client_feedback_endpoints():
    """Test all client feedback related endpoints"""
    
    print("🧪 Testing Client Feedback Functionality")
    print("=" * 50)
    
    # Test 1: Get client feedback workflows
    print("\n1️⃣ Testing GET /api/client/feedback-workflows")
    try:
        response = requests.get(f"{BASE_URL}/api/client/feedback-workflows")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('message', 'No message')}")
            workflows = data.get('workflows', [])
            print(f"📊 Found {len(workflows)} workflows awaiting client feedback")
            for workflow in workflows:
                print(f"   - {workflow.get('document_type')} for {workflow.get('client_name')}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Test client feedback form page
    print("\n2️⃣ Testing GET /client-feedback")
    try:
        response = requests.get(f"{BASE_URL}/client-feedback")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Client feedback form page loaded successfully")
            print(f"📄 Content length: {len(response.text)} characters")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Test client workflow endpoint (should fail without email)
    print("\n3️⃣ Testing GET /api/client/workflow/<id> (without email)")
    try:
        response = requests.get(f"{BASE_URL}/api/client/workflow/test123")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 400:
            print("✅ Correctly rejected request without email parameter")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 4: Test client workflow endpoint (with email)
    print("\n4️⃣ Testing GET /api/client/workflow/<id> (with email)")
    try:
        response = requests.get(f"{BASE_URL}/api/client/workflow/test123?email={TEST_EMAIL}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 404:
            print("✅ Correctly rejected invalid workflow ID")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 5: Test submit client feedback (should fail without valid workflow)
    print("\n5️⃣ Testing POST /api/client/feedback (invalid workflow)")
    try:
        feedback_data = {
            "workflow_id": "invalid_id",
            "client_email": TEST_EMAIL,
            "decision": "accepted",
            "comments": "Test feedback"
        }
        response = requests.post(
            f"{BASE_URL}/api/client/feedback",
            json=feedback_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 404:
            print("✅ Correctly rejected invalid workflow ID")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Client Feedback Testing Complete!")
    print("\n📝 To test with real data:")
    print("1. Start a real approval workflow")
    print("2. Have CEO approve it")
    print("3. Use the client feedback form link from the email")
    print("4. Submit feedback through the form")

if __name__ == "__main__":
    test_client_feedback_endpoints()
