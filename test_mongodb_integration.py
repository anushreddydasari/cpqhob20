#!/usr/bin/env python3
"""
Test script for MongoDB Template Builder Integration
Run this to verify that the MongoDB integration is working correctly.
"""

import requests
import json
from datetime import datetime

# Test data
test_document = {
    "id": "test_doc_001",
    "title": "Test Document",
    "created": datetime.now().isoformat(),
    "updated": datetime.now().isoformat(),
    "blocks": [
        {
            "id": "block_0",
            "type": "text",
            "content": "<div>This is a test text block</div>",
            "position": 0
        },
        {
            "id": "block_1", 
            "type": "image",
            "content": "<div>This is a test image block</div>",
            "position": 1
        }
    ],
    "metadata": {
        "totalBlocks": 2,
        "hasImages": True,
        "hasSignatures": False,
        "hasPricing": False
    }
}

def test_api_endpoints():
    """Test all the MongoDB API endpoints"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing MongoDB Template Builder Integration")
    print("=" * 50)
    
    # Test 1: Save document
    print("\n1️⃣ Testing SAVE endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/template-builder/save",
            json=test_document,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Save successful: {result['message']}")
            print(f"   Action: {result['action']}")
            print(f"   ID: {result['id']}")
        else:
            print(f"❌ Save failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Save error: {str(e)}")
        return False
    
    # Test 2: Get all documents
    print("\n2️⃣ Testing GET ALL endpoint...")
    try:
        response = requests.get(f"{base_url}/api/template-builder/documents")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Get all successful: {result['count']} documents found")
            for doc in result['documents']:
                print(f"   - {doc['title']} (ID: {doc['id']})")
        else:
            print(f"❌ Get all failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Get all error: {str(e)}")
        return False
    
    # Test 3: Load specific document
    print("\n3️⃣ Testing LOAD endpoint...")
    try:
        response = requests.get(f"{base_url}/api/template-builder/load/{test_document['id']}")
        
        if response.status_code == 200:
            result = response.json()
            doc = result['document']
            print(f"✅ Load successful: {doc['title']}")
            print(f"   Blocks: {doc['metadata']['totalBlocks']}")
            print(f"   Has Images: {doc['metadata']['hasImages']}")
        else:
            print(f"❌ Load failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Load error: {str(e)}")
        return False
    
    # Test 4: Get statistics
    print("\n4️⃣ Testing STATS endpoint...")
    try:
        response = requests.get(f"{base_url}/api/template-builder/stats")
        
        if response.status_code == 200:
            result = response.json()
            stats = result['stats']
            print(f"✅ Stats successful:")
            print(f"   Total Documents: {stats['total_documents']}")
            print(f"   With Images: {stats['documents_with_images']}")
            print(f"   With Signatures: {stats['documents_with_signatures']}")
            print(f"   With Pricing: {stats['documents_with_pricing']}")
        else:
            print(f"❌ Stats failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Stats error: {str(e)}")
        return False
    
    # Test 5: Search documents
    print("\n5️⃣ Testing SEARCH endpoint...")
    try:
        response = requests.get(f"{base_url}/api/template-builder/search?q=test")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search successful: {result['count']} documents found")
            for doc in result['documents']:
                print(f"   - {doc['title']}")
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return False
    
    # Test 6: Delete document
    print("\n6️⃣ Testing DELETE endpoint...")
    try:
        response = requests.delete(f"{base_url}/api/template-builder/delete/{test_document['id']}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Delete successful: {result['message']}")
        else:
            print(f"❌ Delete failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return False
    
    print("\n🎉 All tests passed! MongoDB integration is working correctly.")
    return True

if __name__ == "__main__":
    print("Make sure your Flask app is running on http://localhost:5000")
    print("Press Enter to start testing...")
    input()
    
    success = test_api_endpoints()
    
    if success:
        print("\n✅ MongoDB integration is ready to use!")
        print("\n📝 Next steps:")
        print("1. Start your Flask app: python app.py")
        print("2. Open template builder: http://localhost:5000/cpq/template-builder.html")
        print("3. Create and save templates - they will be stored in MongoDB!")
    else:
        print("\n❌ MongoDB integration has issues. Check the errors above.")
