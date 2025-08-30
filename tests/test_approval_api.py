#!/usr/bin/env python3
"""
Test script to directly test the approval API endpoint
"""

import requests
import json

def test_approval_api():
    print("🧪 Testing Approval API Endpoint...")
    print("=" * 50)
    
    # Test data
    workflow_id = "68b03ffba49d0cd86e9d2f31"  # From your debug output
    test_data = {
        "workflow_id": workflow_id,
        "role": "manager",
        "action": "approve",
        "comments": "Test approval from API script"
    }
    
    print(f"📋 Test Data:")
    print(f"  Workflow ID: {workflow_id}")
    print(f"  Role: {test_data['role']}")
    print(f"  Action: {test_data['action']}")
    print(f"  Comments: {test_data['comments']}")
    print()
    
    try:
        print("🚀 Sending POST request to /api/approval/approve...")
        
        response = requests.post(
            "http://localhost:5000/api/approval/approve",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"📄 Response JSON: {json.dumps(response_json, indent=2)}")
        except json.JSONDecodeError:
            print(f"📄 Response Text (not JSON): {response.text}")
        
        print()
        
        if response.status_code == 200:
            print("✅ API call successful!")
            if response_json.get('success'):
                print("✅ Approval processed successfully!")
            else:
                print(f"⚠️ Approval failed: {response_json.get('message')}")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure your Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n💡 Next Steps:")
    print("1. Check if Flask app is running")
    print("2. Check browser console for JavaScript errors")
    print("3. Check Flask app console for backend errors")

if __name__ == "__main__":
    test_approval_api()
