#!/usr/bin/env python3
"""
Clean up orphaned database records for files that no longer exist
"""

from mongodb_collections.generated_pdf_collection import GeneratedPDFCollection
from mongodb_collections.generated_agreement_collection import GeneratedAgreementCollection
from utils.file_path_handler import file_handler

def cleanup_orphaned_files():
    """Remove database records for files that no longer exist"""
    print("🧹 Cleaning up orphaned database records...")
    print("=" * 50)
    
    # Get all files that actually exist
    existing_files = set(file_handler.list_documents())
    print(f"📁 Files found in documents folder: {len(existing_files)}")
    
    # Check PDFs
    pdf_collection = GeneratedPDFCollection()
    all_pdfs = pdf_collection.get_all_pdfs()
    print(f"\n📄 Checking {len(all_pdfs)} PDF records...")
    
    orphaned_pdfs = []
    for pdf in all_pdfs:
        filename = pdf.get('filename')
        if filename and filename not in existing_files:
            orphaned_pdfs.append(pdf)
            print(f"  ❌ Orphaned PDF: {filename}")
        else:
            print(f"  ✅ Valid PDF: {filename}")
    
    # Check Agreements
    agreement_collection = GeneratedAgreementCollection()
    all_agreements = agreement_collection.get_all_agreements()
    print(f"\n📋 Checking {len(all_agreements)} Agreement records...")
    
    orphaned_agreements = []
    for agreement in all_agreements:
        filename = agreement.get('filename')
        if filename and filename not in existing_files:
            orphaned_agreements.append(agreement)
            print(f"  ❌ Orphaned Agreement: {filename}")
        else:
            print(f"  ✅ Valid Agreement: {filename}")
    
    # Summary
    total_orphaned = len(orphaned_pdfs) + len(orphaned_agreements)
    print(f"\n📊 Summary:")
    print(f"  - Total orphaned records: {total_orphaned}")
    print(f"  - Orphaned PDFs: {len(orphaned_pdfs)}")
    print(f"  - Orphaned Agreements: {len(orphaned_agreements)}")
    
    if total_orphaned > 0:
        print(f"\n🗑️  Cleaning up orphaned records...")
        
        # Remove orphaned PDFs
        for pdf in orphaned_pdfs:
            try:
                pdf_collection.delete_pdf(pdf['_id'])
                print(f"  ✅ Removed orphaned PDF: {pdf['filename']}")
            except Exception as e:
                print(f"  ❌ Failed to remove PDF {pdf['filename']}: {e}")
        
        # Remove orphaned Agreements
        for agreement in orphaned_agreements:
            try:
                agreement_collection.delete_agreement(agreement['_id'])
                print(f"  ✅ Removed orphaned Agreement: {agreement['filename']}")
            except Exception as e:
                print(f"  ❌ Failed to remove Agreement {agreement['filename']}: {e}")
        
        print(f"\n🎉 Cleanup completed! Removed {total_orphaned} orphaned records.")
    else:
        print(f"\n🎉 No orphaned records found! Your database is clean.")
    
    return total_orphaned

if __name__ == "__main__":
    try:
        cleanup_orphaned_files()
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
