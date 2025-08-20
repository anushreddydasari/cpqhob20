#!/usr/bin/env python3
"""
MongoDB Database Structure Creation Script
Creates all necessary collections and indexes for the CPQ + PDF Tracking system
"""

import sys
import os
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_database_structure():
    """Create MongoDB database structure and collections"""
    
    try:
        print("🚀 Starting MongoDB Database Structure Creation...")
        
        # Import our collections
        from mongodb_collections import (
            PDFTrackingCollection, QuoteCollection, ClientCollection,
            EmailCollection, SMTPCollection, PricingCollection,
            HubSpotContactCollection, HubSpotIntegrationCollection
        )
        
        print("✅ All collection classes imported successfully!")
        
        # Initialize collections (this creates them in MongoDB)
        print("\n📊 Initializing Collections...")
        
        pdf_tracking = PDFTrackingCollection()
        quotes = QuoteCollection()
        clients = ClientCollection()
        email_collection = EmailCollection()
        smtp_collection = SMTPCollection()
        pricing = PricingCollection()
        hubspot_contacts = HubSpotContactCollection()
        hubspot_integration = HubSpotIntegrationCollection()
        
        print("✅ All collections initialized!")
        
        # Test creating sample data to ensure collections exist
        print("\n🧪 Testing Collection Creation...")
        
        # Test PDF Tracking Collection
        print("  📄 Testing PDF Tracking Collection...")
        test_tracking = pdf_tracking.create_tracking_record(
            quote_id="test_quote_001",
            client_data={
                "name": "Test Client",
                "email": "test@example.com",
                "company": "Test Company"
            },
            pdf_url="/quote/test_001"
        )
        print(f"    ✅ Created tracking record with ID: {test_tracking.inserted_id}")
        
        # Test Client Collection
        print("  👥 Testing Client Collection...")
        test_client = clients.create_client({
            "name": "Test Client",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "company": "Test Company",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        print(f"    ✅ Created client with ID: {test_client.inserted_id}")
        
        # Test Quote Collection
        print("  📋 Testing Quote Collection...")
        test_quote = quotes.create_quote({
            "client": {
                "name": "Test Client",
                "email": "test@example.com"
            },
            "configuration": {
                "users": 10,
                "instances": 2,
                "duration": 12
            },
            "quote": {
                "total_cost": 5000,
                "monthly_cost": 416.67
            },
            "status": "draft",
            "created_at": datetime.now()
        })
        print(f"    ✅ Created quote with ID: {test_quote.inserted_id}")
        
        # Test Email Collection
        print("  📧 Testing Email Collection...")
        test_email = email_collection.log_email_sent({
            "recipient_email": "test@example.com",
            "recipient_name": "Test Client",
            "company_name": "Test Company",
            "sent_at": datetime.now(),
            "status": "sent"
        })
        print(f"    ✅ Created email log with ID: {test_email.inserted_id}")
        
        # Test HubSpot Contact Collection
        print("  🔗 Testing HubSpot Contact Collection...")
        test_contact = hubspot_contacts.store_contact({
            "hubspot_id": "test_hubspot_001",
            "name": "Test HubSpot Contact",
            "email": "hubspot@example.com",
            "company": "Test Company",
            "source": "HubSpot",
            "fetched_at": datetime.now(),
            "status": "new"
        })
        print(f"    ✅ Created HubSpot contact record!")
        
        print("\n🎉 Database Structure Creation Complete!")
        print("\n📋 Collections Created:")
        print("  ✅ pdf_tracking - PDF interaction tracking")
        print("  ✅ quotes - Quote management")
        print("  ✅ clients - Client management")
        print("  ✅ email_logs - Email tracking")
        print("  ✅ smtp_logs - SMTP connection logs")
        print("  ✅ pricing_configs - Pricing configurations")
        print("  ✅ hubspot_contacts - HubSpot contact storage")
        print("  ✅ hubspot_integrations - HubSpot API logs")
        
        print("\n🚀 Ready for Step 2: Enhanced PDF Generator!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database structure: {str(e)}")
        print(f"🔍 Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🏗️  MongoDB Database Structure Creator")
    print("=" * 60)
    
    success = create_database_structure()
    
    if success:
        print("\n✅ SUCCESS: Database structure created!")
        print("🎯 You can now see the collections in MongoDB!")
    else:
        print("\n❌ FAILED: Database structure creation failed!")
        print("🔧 Please check the error messages above.")
    
    print("\n" + "=" * 60)
