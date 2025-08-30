#!/usr/bin/env python3
"""
Test script to verify client feedback functionality in the approval dashboard.
This script tests the client feedback endpoints and dashboard functionality.
"""

import requests
import json
import time

def test_client_feedback_endpoints():
    """Test the client feedback API endpoints."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Client Feedback Endpoints...")
    print("=" * 50)
    
    # Test 1: Get client feedback workflows
    print("\n1️⃣ Testing GET /api/client/feedback-workflows")
    try:
        response = requests.get(f"{base_url}/api/client/feedback-workflows")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Get specific client workflow
    print("\n2️⃣ Testing GET /api/client/workflow/test-workflow-id")
    try:
        response = requests.get(f"{base_url}/api/client/workflow/test-workflow-id?email=test@client.com")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Submit client feedback
    print("\n3️⃣ Testing POST /api/client/feedback")
    feedback_data = {
        "workflow_id": "test-workflow-id",
        "client_email": "test@client.com",
        "feedback_type": "approval",
        "comments": "This is a test feedback comment from the client.",
        "decision": "approved"
    }
    
    try:
        response = requests.post(f"{base_url}/api/client/feedback", json=feedback_data)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Check if dashboard route exists
    print("\n4️⃣ Testing GET /client-feedback (client feedback form)")
    try:
        response = requests.get(f"{base_url}/client-feedback")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Client feedback form is accessible")
            # Check if it contains expected content
            if "Client Feedback" in response.text:
                print("   ✅ Contains 'Client Feedback' text")
            else:
                print("   ❌ Missing 'Client Feedback' text")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_dashboard_integration():
    """Test if the approval dashboard has the client feedback section."""
    base_url = "http://localhost:5000"
    
    print("\n🧪 Testing Dashboard Integration...")
    print("=" * 50)
    
    # Test approval dashboard
    print("\n1️⃣ Testing GET /approval-dashboard")
    try:
        response = requests.get(f"{base_url}/approval-dashboard")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            
            # Check for client feedback navigation button
            if 'onclick="showSection(\'client-feedback\')"' in content:
                print("   ✅ Client feedback navigation button found")
            else:
                print("   ❌ Client feedback navigation button missing")
            
            # Check for client feedback section
            if 'id="client-feedback-section"' in content:
                print("   ✅ Client feedback section HTML found")
            else:
                print("   ❌ Client feedback section HTML missing")
            
            # Check for client feedback JavaScript functions
            if 'loadClientFeedback()' in content:
                print("   ✅ loadClientFeedback function found")
            else:
                print("   ❌ loadClientFeedback function missing")
            
            if 'displayClientFeedback(' in content:
                print("   ✅ displayClientFeedback function found")
            else:
                print("   ❌ displayClientFeedback function missing")
            
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Main test function."""
    print("🚀 Starting Client Feedback Dashboard Tests...")
    print("=" * 60)
    
    # Wait a moment for Flask to be ready
    print("⏳ Waiting for Flask app to be ready...")
    time.sleep(2)
    
    # Test endpoints
    test_client_feedback_endpoints()
    
    # Test dashboard integration
    test_dashboard_integration()
    
    print("\n" + "=" * 60)
    print("✅ Client Feedback Dashboard Tests Completed!")
    print("\n📋 Summary:")
    print("   - Check the above results for any ❌ errors")
    print("   - If all tests pass, the client feedback section should be working")
    print("   - Open http://localhost:5000/approval-dashboard to see the new section")
    print("   - Look for the '👥 Client Feedback' button in the navigation")

if __name__ == "__main__":
    main()
