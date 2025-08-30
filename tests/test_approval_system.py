#!/usr/bin/env python3
"""
Test script for the Approval Workflow System
This script tests the basic functionality of the approval workflow
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "test@example.com"

def test_approval_system():
    """Test the complete approval workflow system"""
    
    print("🚀 Testing Approval Workflow System")
    print("=" * 50)
    
    # Test 1: Check if approval dashboard is accessible
    print("\n1. Testing Approval Dashboard Access...")
    try:
        response = requests.get(f"{BASE_URL}/approval-dashboard")
        if response.status_code == 200:
            print("✅ Approval Dashboard is accessible")
        else:
            print(f"❌ Approval Dashboard returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing Approval Dashboard: {e}")
    
    # Test 2: Check approval stats API
    print("\n2. Testing Approval Stats API...")
    try:
        response = requests.get(f"{BASE_URL}/api/approval/stats")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Approval Stats API working")
                print(f"   - Pending: {data['stats']['pending']}")
                print(f"   - Completed Today: {data['stats']['completed_today']}")
                print(f"   - Avg Time: {data['stats']['avg_approval_time']}")
            else:
                print(f"❌ Approval Stats API error: {data.get('message')}")
        else:
            print(f"❌ Approval Stats API returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Approval Stats API: {e}")
    
    # Test 3: Check pending approvals API
    print("\n3. Testing Pending Approvals API...")
    try:
        response = requests.get(f"{BASE_URL}/api/approval/pending")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Pending Approvals API working")
                print(f"   - Found {len(data['workflows'])} pending workflows")
            else:
                print(f"❌ Pending Approvals API error: {data.get('message')}")
        else:
            print(f"❌ Pending Approvals API returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Pending Approvals API: {e}")
    
    # Test 4: Check my queue API
    print("\n4. Testing My Queue API...")
    try:
        response = requests.get(f"{BASE_URL}/api/approval/my-queue?role=manager&email={TEST_EMAIL}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ My Queue API working")
                print(f"   - Found {len(data['workflows'])} items in queue")
            else:
                print(f"❌ My Queue API error: {data.get('message')}")
        else:
            print(f"❌ My Queue API returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing My Queue API: {e}")
    
    # Test 5: Check workflow status API
    print("\n5. Testing Workflow Status API...")
    try:
        response = requests.get(f"{BASE_URL}/api/approval/workflow-status")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Workflow Status API working")
                print(f"   - Found {len(data['workflows'])} active workflows")
            else:
                print(f"❌ Workflow Status API error: {data.get('message')}")
        else:
            print(f"❌ Workflow Status API returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Workflow Status API: {e}")
    
    # Test 6: Check approval history API
    print("\n6. Testing Approval History API...")
    try:
        response = requests.get(f"{BASE_URL}/api/approval/history")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Approval History API working")
                print(f"   - Found {len(data['history'])} completed approvals")
            else:
                print(f"❌ Approval History API error: {data.get('message')}")
        else:
            print(f"❌ Approval History API returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Approval History API: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Approval Workflow System Test Complete!")
    print("\n📋 Next Steps:")
    print("1. Open your browser and go to: http://localhost:5000")
    print("2. Click on 'Approval Dashboard' to test the interface")
    print("3. Use Quote Management to start approval workflows")
    print("4. Test the complete Manager → CEO → Client workflow")

if __name__ == "__main__":
    print("⚠️  Make sure your Flask app is running on http://localhost:5000")
    print("⚠️  Run: python app.py")
    print()
    
    try:
        test_approval_system()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
