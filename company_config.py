#!/usr/bin/env python3
"""
🏢 Company Configuration for Client Emails

This file contains company branding and contact information
that will be used in client delivery emails.

Customize these values to match your company's branding.
"""

# Company Information
COMPANY_CONFIG = {
    # Company Details
    "company_name": "Your Company Name",  # Replace with your actual company name
    "company_website": "https://yourcompany.com",  # Replace with your actual website
    "company_logo": "🏢",  # You can use emoji or leave empty for text-only
    
    # Support Contact Information
    "support_email": "support@yourcompany.com",  # Replace with your actual support email
    "support_phone": "+1 (555) 123-4567",  # Replace with your actual support phone
    "support_hours": "Monday - Friday, 9:00 AM - 6:00 PM EST",  # Replace with your actual hours
    
    # Email Branding
    "email_header_color": "linear-gradient(135deg, #28a745 0%, #20c997 100%)",  # Green gradient for success
    "email_accent_color": "#28a745",  # Green accent color
    "email_secondary_color": "#007bff",  # Blue for contact info
    
    # Footer Information
    "footer_text": "Thank you for choosing Your Company Name",  # Replace with your actual footer
    "footer_copyright": f"© {__import__('datetime').datetime.now().year} Your Company Name. All rights reserved.",
    
    # Document Instructions
    "document_review_instructions": [
        "Review the attached document carefully",
        "Verify all information is correct",
        "Sign the document if required",
        "Save a copy for your records",
        "Contact us with any questions"
    ],
    
    # Important Notes
    "important_notes": [
        "This document has been reviewed and approved by our management team",
        "Please review all terms and conditions carefully",
        "Contact us immediately if you notice any errors or have concerns",
        "Keep this email and document for your records"
    ]
}

def get_company_config():
    """Get the company configuration"""
    return COMPANY_CONFIG

def update_company_config(new_config):
    """Update company configuration with new values"""
    global COMPANY_CONFIG
    COMPANY_CONFIG.update(new_config)
    return COMPANY_CONFIG

# Example usage:
if __name__ == "__main__":
    print("🏢 Company Configuration")
    print("=" * 40)
    
    config = get_company_config()
    for key, value in config.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")
    
    print("\n💡 To customize:")
    print("1. Edit the values in this file")
    print("2. Replace placeholder text with your actual company information")
    print("3. Update colors and branding to match your company style")
    print("4. Save the file and restart your application")
