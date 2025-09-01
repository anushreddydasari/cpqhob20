#!/usr/bin/env python3
"""
Test script for the file path handler
"""

import os
import sys

# Add the utils directory to the path
sys.path.append('utils')

try:
    from file_path_handler import file_handler
    
    print("🔍 Testing File Path Handler")
    print("=" * 50)
    
    print(f"📁 Project Root: {file_handler.project_root}")
    print(f"📁 Documents Directory: {file_handler.documents_dir}")
    print(f"📁 Current Working Directory: {os.getcwd()}")
    print(f"📁 App Directory: {os.path.dirname(__file__)}")
    
    print("\n📋 Available Documents:")
    documents = file_handler.list_documents()
    for doc in documents:
        file_info = file_handler.get_file_info(doc)
        print(f"  - {doc} (exists: {file_info['exists']})")
    
    print("\n✅ File handler test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the file_path_handler.py file exists in the utils directory")
except Exception as e:
    print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n🚀 Running file handler test...")
