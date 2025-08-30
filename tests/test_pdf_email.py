#!/usr/bin/env python3
"""
Test script to verify PDF generation and email functionality
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_pdf_generation():
    """Test PDF generation functionality"""
    try:
        print("🔍 Testing PDF generation...")
        
        # Import required modules
        from templates.pdf_generator import PDFGenerator
        
        # Create PDF generator
        pdf_generator = PDFGenerator()
        
        # Test data
        client_data = {
            'name': 'Test Client',
            'company': 'Test Company',
            'email': 'test@example.com',
            'phone': '+1-555-0123',
            'serviceType': 'Migration Services'
        }
        
        quote_data = {
            'basic': {
                'perUserCost': 30.0,
                'totalUserCost': 1500.0,
                'dataCost': 100.0,
                'migrationCost': 300.0,
                'instanceCost': 1000.0,
                'totalCost': 2900.0
            },
            'standard': {
                'perUserCost': 35.0,
                'totalUserCost': 1750.0,
                'dataCost': 150.0,
                'migrationCost': 300.0,
                'instanceCost': 1000.0,
                'totalCost': 3200.0
            },
            'advanced': {
                'perUserCost': 40.0,
                'totalUserCost': 2000.0,
                'dataCost': 180.0,
                'migrationCost': 300.0,
                'instanceCost': 1000.0,
                'totalCost': 3480.0
            }
        }
        
        configuration = {
            'users': 50,
            'instanceType': 'standard',
            'instances': 2,
            'duration': 6,
            'migrationType': 'content',
            'dataSize': 100
        }
        
        # Generate PDF
        pdf_buffer = pdf_generator.create_quote_pdf(client_data, quote_data, configuration)
        
        # Save PDF to test file
        test_filename = f"test_quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        test_filepath = os.path.join('documents', test_filename)
        
        # Ensure documents directory exists
        os.makedirs('documents', exist_ok=True)
        
        with open(test_filepath, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        print(f"✅ PDF generated successfully: {test_filepath}")
        print(f"✅ File size: {os.path.getsize(test_filepath)} bytes")
        
        return test_filepath
        
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_email_service():
    """Test email service functionality"""
    try:
        print("🔍 Testing email service...")
        
        # Import email service
        from cpq.email_service import EmailService
        
        # Create email service
        email_service = EmailService()
        
        # Test connection
        print("🔍 Testing Gmail connection...")
        connection_result = email_service.test_connection()
        print(f"Connection result: {connection_result}")
        
        if not connection_result['success']:
            print("❌ Gmail connection failed. Please check your .env file configuration.")
            return False
        
        print("✅ Gmail connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Email service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_email_with_pdf_attachment(pdf_filepath):
    """Test sending email with PDF attachment"""
    try:
        print("🔍 Testing email with PDF attachment...")
        
        # Import email service
        from cpq.email_service import EmailService
        
        # Create email service
        email_service = EmailService()
        
        # Test data
        recipient_email = "test@example.com"  # Change this to a real email for testing
        recipient_name = "Test Recipient"
        company_name = "Test Company"
        
        # Test quote data
        quote_data = {
            'basic': {'totalCost': 2900.0},
            'standard': {'totalCost': 3200.0},
            'advanced': {'totalCost': 3480.0}
        }
        
        print(f"🔍 Sending test email to {recipient_email}")
        print(f"🔍 PDF attachment: {pdf_filepath}")
        
        # Send email with PDF attachment
        result = email_service.send_quote_email(
            recipient_email, 
            recipient_name, 
            company_name, 
            quote_data, 
            pdf_filepath
        )
        
        print(f"Email result: {result}")
        
        if result['success']:
            print("✅ Email with PDF attachment sent successfully!")
        else:
            print(f"❌ Email failed: {result['message']}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Email with PDF attachment test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting PDF and Email Tests...")
    print("=" * 50)
    
    # Test 1: PDF Generation
    pdf_filepath = test_pdf_generation()
    if not pdf_filepath:
        print("❌ Cannot continue without PDF generation")
        return
    
    print("\n" + "=" * 50)
    
    # Test 2: Email Service Connection
    email_ok = test_email_service()
    if not email_ok:
        print("❌ Cannot continue without email service")
        return
    
    print("\n" + "=" * 50)
    
    # Test 3: Email with PDF Attachment
    print("⚠️ Note: Change the recipient email in the test function to test actual sending")
    email_sent = test_email_with_pdf_attachment(pdf_filepath)
    
    print("\n" + "=" * 50)
    
    if email_sent:
        print("🎉 All tests completed successfully!")
    else:
        print("⚠️ Tests completed with some issues. Check the logs above.")
    
    print(f"\n📁 Test PDF saved to: {pdf_filepath}")

if __name__ == "__main__":
    main()
