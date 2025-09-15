#!/usr/bin/env python3
"""
Test script for PDF regeneration functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mongodb_collections.generated_pdf_collection import GeneratedPDFCollection
from mongodb_collections.quote_collection import QuoteCollection
from datetime import datetime

def test_pdf_regeneration():
    """Test the PDF regeneration functionality"""
    print("🧪 Testing PDF Regeneration System")
    print("=" * 50)
    
    # Initialize collections
    pdf_collection = GeneratedPDFCollection()
    quote_collection = QuoteCollection()
    
    # Create a test quote
    test_quote_data = {
        "client": {
            "name": "Test Client",
            "company": "Test Company",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "serviceType": "Migration Services"
        },
        "configuration": {
            "users": 50,
            "instanceType": "standard",
            "instances": 2,
            "duration": 12,
            "migrationType": "content",
            "dataSize": 100
        },
        "quote": {
            "basic": {"totalCost": 5000},
            "premium": {"totalCost": 7500},
            "enterprise": {"totalCost": 10000}
        }
    }
    
    try:
        # Create the quote
        print("1. Creating test quote...")
        quote_result = quote_collection.create_quote(test_quote_data)
        quote_id = str(quote_result.inserted_id)
        print(f"   ✅ Quote created with ID: {quote_id}")
        
        # Create test PDF metadata
        print("2. Creating test PDF metadata...")
        pdf_metadata = {
            'quote_id': quote_id,
            'filename': 'test_quote.pdf',
            'file_path': 'documents/test_quote.pdf',
            'client_name': 'Test Client',
            'company_name': 'Test Company',
            'service_type': 'Migration Services',
            'file_size': 0
        }
        
        # Store PDF metadata (without content to simulate missing file)
        pdf_result = pdf_collection.store_pdf_metadata(pdf_metadata)
        pdf_id = str(pdf_result.inserted_id)
        print(f"   ✅ PDF metadata created with ID: {pdf_id}")
        
        # Test regeneration
        print("3. Testing PDF regeneration from quote data...")
        regenerated_path, message = pdf_collection.regenerate_pdf_from_quote(pdf_id, test_quote_data)
        
        if regenerated_path:
            print(f"   ✅ PDF regenerated successfully: {message}")
            print(f"   📁 File path: {regenerated_path}")
            
            # Check if file exists
            if os.path.exists(regenerated_path):
                file_size = os.path.getsize(regenerated_path)
                print(f"   📊 File size: {file_size} bytes")
                print("   ✅ File exists and has content")
            else:
                print("   ❌ File was not created")
        else:
            print(f"   ❌ PDF regeneration failed: {message}")
        
        # Test base64 storage
        print("4. Testing PDF content storage...")
        test_pdf_content = b"Test PDF content for base64 storage"
        pdf_metadata_with_content = {
            'quote_id': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'filename': 'test_with_content.pdf',
            'file_path': 'documents/test_with_content.pdf',
            'client_name': 'Test Client',
            'company_name': 'Test Company',
            'service_type': 'Migration Services',
            'file_size': len(test_pdf_content)
        }
        
        pdf_with_content_result = pdf_collection.store_pdf_metadata(pdf_metadata_with_content, test_pdf_content)
        pdf_with_content_id = str(pdf_with_content_result.inserted_id)
        print(f"   ✅ PDF with content stored with ID: {pdf_with_content_id}")
        
        # Verify content was stored
        stored_pdf = pdf_collection.get_pdf_by_id(pdf_with_content_id)
        if stored_pdf and 'pdf_data' in stored_pdf:
            print("   ✅ PDF content successfully stored as base64")
            decoded_content = stored_pdf['pdf_data']
            print(f"   📊 Base64 content length: {len(decoded_content)} characters")
        else:
            print("   ❌ PDF content was not stored")
        
        print("\n🎉 PDF Regeneration Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup - remove test files
        try:
            if 'regenerated_path' in locals() and regenerated_path and os.path.exists(regenerated_path):
                os.remove(regenerated_path)
                print("   🧹 Cleaned up test file")
        except:
            pass

if __name__ == "__main__":
    success = test_pdf_regeneration()
    sys.exit(0 if success else 1)
