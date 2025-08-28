#!/usr/bin/env python3
"""
Check MongoDB collections for stored documents
"""

from mongodb_collections.generated_pdf_collection import GeneratedPDFCollection
from mongodb_collections.generated_agreement_collection import GeneratedAgreementCollection

def check_collections():
    """Check what's stored in our collections"""
    print("🔍 Checking MongoDB Collections...\n")
    
    # Check PDF collection
    pdf_collection = GeneratedPDFCollection()
    pdfs = pdf_collection.get_all_pdfs()
    print(f"📄 PDFs in MongoDB: {len(pdfs)}")
    for pdf in pdfs:
        print(f"   - {pdf['filename']} for {pdf['client_name']} at {pdf['company_name']}")
    
    print()
    
    # Check Agreement collection
    agreement_collection = GeneratedAgreementCollection()
    agreements = agreement_collection.get_all_agreements()
    print(f"📋 Agreements in MongoDB: {len(agreements)}")
    for agreement in agreements:
        print(f"   - {agreement['filename']} for {agreement['client_name']} at {agreement['company_name']}")

if __name__ == "__main__":
    check_collections()
