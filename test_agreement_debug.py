#!/usr/bin/env python3
"""
Test script to debug agreement generation and placeholder replacement
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import _build_template_data_from_quote, generate_pdf_from_template
from mongodb_collections.quote_collection import QuoteCollection
from mongodb_collections.template_builder_collection import TemplateBuilderCollection

def test_agreement_generation():
    print("🔍 Testing Agreement Generation Debug")
    print("=" * 50)
    
    # Get the latest quote
    quote_collection = QuoteCollection()
    quotes = quote_collection.get_all_quotes()
    
    if not quotes:
        print("❌ No quotes found in database")
        return
    
    latest_quote = quotes[-1]  # Get the most recent quote
    print(f"📋 Testing with quote ID: {latest_quote['_id']}")
    print(f"📋 Quote data: {latest_quote}")
    
    # Build template data
    template_data = _build_template_data_from_quote(latest_quote)
    print(f"\n🔧 Template Data Built:")
    print(f"  config_users: {template_data.get('config_users', 'NOT FOUND')}")
    print(f"  config_duration_months: {template_data.get('config_duration_months', 'NOT FOUND')}")
    print(f"  config_migration_type: {template_data.get('config_migration_type', 'NOT FOUND')}")
    print(f"  basic_migration_cost_formatted: {template_data.get('basic_migration_cost_formatted', 'NOT FOUND')}")
    print(f"  basic_total_cost_formatted: {template_data.get('basic_total_cost_formatted', 'NOT FOUND')}")
    print(f"  standard_migration_cost_formatted: {template_data.get('standard_migration_cost_formatted', 'NOT FOUND')}")
    print(f"  standard_total_cost_formatted: {template_data.get('standard_total_cost_formatted', 'NOT FOUND')}")
    
    # Get template
    template_collection = TemplateBuilderCollection()
    templates = template_collection.get_all_documents()
    
    if not templates:
        print("❌ No templates found")
        return
    
    template = templates[0]  # Use first template
    print(f"\n📄 Using template: {template.get('_id', 'NO_ID')}")
    print(f"📄 Template content preview: {template.get('content', '')[:200]}...")
    print(f"📄 Template keys: {list(template.keys())}")
    
    # Test placeholder replacement
    test_content = """
    <table>
        <tr>
            <td>CloudFuze X-Change Data Migration</td>
            <td>{up to i want to keep here no of users}</td>
            <td>{i want to mention total cost - (migrationcost+if instancecost}</td>
        </tr>
        <tr>
            <td>Managed Migration Service</td>
            <td>Valid for how m,any Months i want tomention here</td>
            <td>{i want to mention here cost of only migration cost here}</td>
        </tr>
        <tr>
            <td>total</td>
            <td>price</td>
            <td>{i want to mention here total amount}</td>
        </tr>
    </table>
    """
    
    print(f"\n🔄 Testing placeholder replacement:")
    print(f"  Original: {test_content}")
    
    # Apply the same replacement logic as in the app
    processed_content = test_content
    
    # Replace specific placeholders
    processed_content = processed_content.replace('{up to i want to keep here no of users}', str(template_data.get('config_users', 1)))
    processed_content = processed_content.replace('{i want to mention total cost - (migrationcost+if instancecost}', template_data.get('standard_total_cost_formatted', '$0.00'))
    processed_content = processed_content.replace('Valid for how m,any Months i want tomention here', str(template_data.get('config_duration_months', '3')))
    processed_content = processed_content.replace('{i want to mention here cost of only migration cost here}', template_data.get('standard_migration_cost_formatted', '$0.00'))
    processed_content = processed_content.replace('{i want to mention here total amount}', template_data.get('standard_total_cost_formatted', '$0.00'))
    
    print(f"  Processed: {processed_content}")
    
    # Check if placeholders were replaced
    if '{up to i want to keep here no of users}' in processed_content:
        print("❌ User count placeholder NOT replaced")
    else:
        print("✅ User count placeholder replaced")
        
    if '{i want to mention total cost - (migrationcost+if instancecost}' in processed_content:
        print("❌ Total cost placeholder NOT replaced")
    else:
        print("✅ Total cost placeholder replaced")

if __name__ == "__main__":
    test_agreement_generation()
