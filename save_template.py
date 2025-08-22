#!/usr/bin/env python3
"""
Simple script to save Purchase Agreement Email Template to database
"""

import requests
import json

# Template data
template_data = {
    "name": "Purchase Agreement Email Template",
    "type": "email",
    "content": """📋 Purchase Agreement Email Template

📧 Email Subject:
Subject: Purchase Agreement - {{service_type}} Services for {{client_name}}

👋 Email Body:
Dear {{client_name}},

Thank you for choosing {{company_name}} for your {{service_type}} services. We are pleased to present you with this Purchase Agreement outlining the terms and conditions of our engagement.

Please review the agreement details below and let us know if you have any questions or require any modifications.

🏢 Company Information:
Company: {{company_name}}
Address: {{company_address}}
Website: {{company_website}}
Email: {{company_email}}
Phone: {{company_phone}}

👤 Customer Information:
Customer: {{client_name}}
Company: {{client_company}}
Address: {{client_address}}
Email: {{client_email}}
Phone: {{client_phone}}

🔧 Service Description:
Service Type: {{service_type}}
Description: {{service_description}}
Requirements: {{requirements}}

💰 Pricing Details:
Service Item: {{service_type}}
Description: {{service_description}}
Quantity: 1
Unit Price: ${{unit_price}}
Total: ${{total_cost}}

Total Agreement Value: ${{total_cost}}

📅 Project Timeline:
Effective Date: {{effective_date}}
Project Start Date: {{start_date}}
Project End Date: {{end_date}}
Duration: {{project_duration}}

💳 Payment Terms:
Payment Schedule: {{payment_schedule}}
Payment Method: {{payment_method}}
Due Dates: {{payment_due_dates}}
Late Payment: {{late_payment_terms}}

🔒 Confidentiality Clauses:
Confidentiality Period: {{confidentiality_period}}
Non-Disclosure: {{non_disclosure_terms}}
Data Protection: {{data_protection_terms}}
Return of Materials: {{return_materials_terms}}

⚖️ Warranty & Termination:
Warranty Period: {{warranty_period}}
Warranty Coverage: {{warranty_coverage}}
Termination Notice: {{termination_notice}}
Termination Fees: {{termination_fees}}

📋 In-Scope Features (Exhibit A):
Core Features:
• {{feature_1}}
• {{feature_2}}
• {{feature_3}}
• {{feature_4}}
• {{feature_5}}

Additional Services: {{additional_services}}

📝 Next Steps:
To proceed with this agreement, please:
1. Review all terms and conditions above
2. Confirm acceptance of the pricing and timeline
3. Provide any requested modifications
4. Sign and return the agreement

✍️ Agreement Acceptance:
Customer Name: {{client_name}}
Company: {{client_company}}
Date: {{acceptance_date}}
Signature: _________________________

📞 Contact Information:
If you have any questions about this agreement, please contact us:
Email: {{company_email}}
Phone: {{company_phone}}
Address: {{company_address}}

Best regards,
{{company_name}} Team""",
    "description": "Professional Purchase Agreement Email Template with all required sections including company info, customer details, service description, pricing, timeline, payment terms, legal clauses, and signature section. Uses dynamic variables that pull from quote data."
}

def save_template():
    """Save the template to the database"""
    try:
        print("🚀 Saving Purchase Agreement Email Template...")
        
        # Make request to save template
        response = requests.post(
            'http://localhost:5000/api/templates/save',
            json=template_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Template saved successfully!")
                print(f"Template ID: {result.get('template_id')}")
                return True
            else:
                print(f"❌ Failed to save: {result.get('message')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure Flask is running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_template():
    """Test that template can be loaded"""
    try:
        print("📋 Testing template loading...")
        
        response = requests.get('http://localhost:5000/api/templates/list')
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                templates = result.get('templates', [])
                print(f"✅ Found {len(templates)} templates in system")
                
                # Look for our template
                for template in templates:
                    if template.get('name') == 'Purchase Agreement Email Template':
                        print("✅ Purchase Agreement Email Template found!")
                        return True
                
                print("❌ Template not found in system")
                return False
            else:
                print(f"❌ Failed to load templates: {result.get('message')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("📧 Setting up Purchase Agreement Email Template")
    print("=" * 50)
    
    # Save template
    if save_template():
        print("\n📋 Testing template system...")
        if test_template():
            print("\n🎉 SUCCESS! Email Template is now working!")
            print("\n🎯 Next Steps:")
            print("1. Visit /template-management page")
            print("2. You'll see your new Email Template")
            print("3. Template statistics will show 1 email template")
            print("4. Ready to create PDF template next!")
        else:
            print("\n⚠️ Template saved but loading test failed")
    else:
        print("\n❌ Template saving failed")
    
    print("\n" + "=" * 50)
    print("�� Setup Complete!")
