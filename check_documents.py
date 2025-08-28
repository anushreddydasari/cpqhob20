#!/usr/bin/env python3
"""
Simple script to check existing documents and their IDs
"""

from mongodb_collections import GeneratedPDFCollection, GeneratedAgreementCollection

def check_documents():
    print("🔍 Checking existing documents in your system...")
    print("=" * 50)
    
    # Check PDFs
    try:
        pdfs = GeneratedPDFCollection()
        all_pdfs = pdfs.get_all_pdfs()
        
        print(f"📄 PDF Documents Found: {len(all_pdfs)}")
        if all_pdfs:
            for i, doc in enumerate(all_pdfs[:5], 1):
                print(f"  {i}. ID: {doc['_id']}")
                print(f"     Filename: {doc.get('filename', 'N/A')}")
                print(f"     Created: {doc.get('created_at', 'N/A')}")
                print()
        else:
            print("  No PDF documents found")
        print()
        
    except Exception as e:
        print(f"❌ Error checking PDFs: {e}")
    
    # Check Agreements
    try:
        agreements = GeneratedAgreementCollection()
        all_agreements = agreements.get_all_agreements()
        
        print(f"📋 Agreements Found: {len(all_agreements)}")
        if all_agreements:
            for i, doc in enumerate(all_agreements[:5], 1):
                print(f"  {i}. ID: {doc['_id']}")
                print(f"     Filename: {doc.get('filename', 'N/A')}")
                print(f"     Created: {doc.get('created_at', 'N/A')}")
                print()
        else:
            print("  No agreements found")
        print()
        
    except Exception as e:
        print(f"❌ Error checking agreements: {e}")
    
    print("💡 To use these IDs in the approval workflow:")
    print("   1. Copy the ID you want to approve")
    print("   2. Go to Quote Management page")
    print("   3. Paste the ID in 'Document ID' field")
    print("   4. Select document type (PDF or Agreement)")
    print("   5. Enter manager and CEO emails")
    print("   6. Click 'Start Approval Workflow'")

if __name__ == "__main__":
    check_documents()
