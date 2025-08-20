from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from db import quotes_collection, clients_collection
from pricing_logic import calculate_quote
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from flask import send_file

app = Flask(__name__)
CORS(app)

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/quote-calculator')
def serve_quote_calculator():
    return send_from_directory('.', 'quote-calculator.html')

@app.route('/quote-template')
def serve_quote_template():
    return send_from_directory('.', 'quote-template.html')

@app.route('/client-management')
def serve_client_management():
    return send_from_directory('.', 'client-management.html')

@app.route('/hubspot-data')
def serve_hubspot_data():
    return send_from_directory('..', 'hubspot/hubspot-data.html')

# Client Management APIs
@app.route('/api/clients', methods=['POST'])
def save_client():
    """Save a new client to MongoDB"""
    try:
        data = request.get_json()
        
        # Add timestamp
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        # Save to MongoDB
        result = clients_collection.insert_one(data)
        
        return jsonify({
            "success": True,
            "message": "Client saved successfully",
            "client_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error saving client: {str(e)}"
        }), 500

@app.route('/api/clients', methods=['GET'])
def get_all_clients():
    """Get all clients from MongoDB"""
    try:
        clients = list(clients_collection.find({}, {'_id': 0}))
        return jsonify({
            "success": True,
            "clients": clients
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching clients: {str(e)}"
        }), 500

@app.route('/api/clients/<client_id>', methods=['PUT'])
def update_client(client_id):
    """Update an existing client"""
    try:
        from bson import ObjectId
        
        data = request.get_json()
        data['updated_at'] = datetime.now()
        
        # Remove _id if present
        if '_id' in data:
            del data['_id']
        
        result = clients_collection.update_one(
            {"_id": ObjectId(client_id)},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({
                "success": False,
                "message": "Client not found"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Client updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating client: {str(e)}"
        }), 500

@app.route('/api/clients/<client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Delete a client"""
    try:
        from bson import ObjectId
        
        result = clients_collection.delete_one({"_id": ObjectId(client_id)})
        
        if result.deleted_count == 0:
            return jsonify({
                "success": False,
                "message": "Client not found"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Client deleted successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error deleting client: {str(e)}"
        }), 500

@app.route('/api/quote', methods=['POST'])
def generate_quote():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        # Client details
        client_name = data.get('clientName', '')
        phone_number = data.get('phoneNumber', '')
        email = data.get('email', '')
        company_name = data.get('companyName', '')
        service_type = data.get('serviceType', '')
        requirements = data.get('requirements', '')
        
        # CPQ configuration with validation
        try:
            users = int(data.get('users', 0))
            instances = int(data.get('instances', 0))
            duration = int(data.get('duration', 0))
            data_size = int(data.get('dataSize', 0))
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid numeric values provided"
            }), 400
        
        # Validate required fields
        if users <= 0:
            return jsonify({
                "success": False,
                "message": "Number of users must be greater than 0"
            }), 400
        
        if instances <= 0:
            return jsonify({
                "success": False,
                "message": "Number of instances must be greater than 0"
            }), 400
        
        if duration <= 0:
            return jsonify({
                "success": False,
                "message": "Duration must be greater than 0"
            }), 400
        
        if data_size < 0:
            return jsonify({
                "success": False,
                "message": "Data size cannot be negative"
            }), 400
        
        instance_type = data.get('instanceType', 'standard').lower()
        migration_type = data.get('migrationType', 'content').lower()
        
        # Validate instance type
        valid_instance_types = ['small', 'standard', 'large', 'extra_large']
        if instance_type not in valid_instance_types:
            instance_type = 'standard'  # Default to standard if invalid
        
        # Validate migration type
        valid_migration_types = ['content', 'email', 'messaging']
        if migration_type not in valid_migration_types:
            migration_type = 'content'  # Default to content if invalid

        # Use the pricing logic from separate file
        results = calculate_quote(users, instance_type, instances, duration, migration_type, data_size)

        # Save quote to MongoDB with client details
        try:
            quotes_collection.insert_one({
                "timestamp": datetime.now(),
                "client": {
                    "name": client_name,
                    "phone": phone_number,
                    "email": email,
                    "company": company_name,
                    "serviceType": service_type,
                    "requirements": requirements
                },
                "configuration": {
                    "users": users,
                    "instanceType": instance_type,
                    "instances": instances,
                    "duration": duration,
                    "migrationType": migration_type,
                    "dataSize": data_size
                },
                "quote": results
            })
        except Exception as e:
            print(f"Warning: Failed to save quote to database: {str(e)}")
            # Continue without saving if database fails

        return jsonify({
            "success": True,
            "quote": results
        })
        
    except Exception as e:
        print(f"Error in generate_quote: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        # Extract data
        client_data = data.get('client', {})
        quote_data = data.get('quote', {})
        configuration = data.get('configuration', {})
        
        # Create PDF
        pdf_buffer = create_quote_pdf(client_data, quote_data, configuration)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"quote_{client_data.get('name', 'client')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return jsonify({"success": False, "message": f"PDF generation failed: {str(e)}"}), 500

def create_quote_pdf(client_data, quote_data, configuration):
    """Create a professional PDF quote"""
    
    # Create buffer for PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#007BFF')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#007BFF')
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("PROFESSIONAL QUOTE", title_style))
    story.append(Paragraph("Migration Services & Solutions", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Client Information
    story.append(Paragraph("Client Information", heading_style))
    client_info = [
        ['Name:', client_data.get('name', 'N/A')],
        ['Company:', client_data.get('company', 'N/A')],
        ['Email:', client_data.get('email', 'N/A')],
        ['Phone:', client_data.get('phone', 'N/A')],
        ['Service Type:', client_data.get('serviceType', 'N/A')]
    ]
    
    client_table = Table(client_info, colWidths=[2*inch, 4*inch])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    story.append(client_table)
    story.append(Spacer(1, 20))
    
    # Quote Details
    story.append(Paragraph("Quote Details", heading_style))
    quote_info = [
        ['Quote Date:', datetime.now().strftime('%B %d, %Y')],
        ['Migration Type:', configuration.get('migrationType', 'N/A')],
        ['Project Duration:', f"{configuration.get('duration', 0)} months"],
        ['Number of Users:', str(configuration.get('users', 0))],
        ['Instance Type:', configuration.get('instanceType', 'N/A')],
        ['Number of Instances:', str(configuration.get('instances', 0))],
        ['Data Size:', f"{configuration.get('dataSize', 0)} GB"]
    ]
    
    quote_table = Table(quote_info, colWidths=[2*inch, 4*inch])
    quote_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    story.append(quote_table)
    story.append(Spacer(1, 20))
    
    # Pricing Table
    story.append(Paragraph("Pricing Breakdown", heading_style))
    
    if quote_data:
        pricing_data = [
            ['Service Details', 'Basic Plan', 'Standard Plan', 'Advanced Plan']
        ]
        
        # Add pricing rows
        if 'basic' in quote_data:
            pricing_data.extend([
                ['Per User Cost', f"${quote_data['basic'].get('perUserCost', 0):.2f}", 
                 f"${quote_data['standard'].get('perUserCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('perUserCost', 0):.2f}"],
                ['Total User Cost', f"${quote_data['basic'].get('totalUserCost', 0):.2f}", 
                 f"${quote_data['standard'].get('totalUserCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('totalUserCost', 0):.2f}"],
                ['Data Cost', f"${quote_data['basic'].get('dataCost', 0):.2f}", 
                 f"${quote_data['standard'].get('dataCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('dataCost', 0):.2f}"],
                ['Migration Cost', f"${quote_data['basic'].get('migrationCost', 0):.2f}", 
                 f"${quote_data['standard'].get('migrationCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('migrationCost', 0):.2f}"],
                ['Instance Cost', f"${quote_data['basic'].get('instanceCost', 0):.2f}", 
                 f"${quote_data['standard'].get('instanceCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('instanceCost', 0):.2f}"],
                ['TOTAL COST', f"${quote_data['basic'].get('totalCost', 0):.2f}", 
                 f"${quote_data['standard'].get('totalCost', 0):.2f}", 
                 f"${quote_data['advanced'].get('totalCost', 0):.2f}"]
            ])
        
        pricing_table = Table(pricing_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        pricing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007BFF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
            ('FONTSIZE', (0, -1), (-1, -1), 12)
        ]))
        story.append(pricing_table)
    
    story.append(Spacer(1, 20))
    
    # Terms and Conditions
    story.append(Paragraph("Terms & Conditions", heading_style))
    terms = [
        "• This quote is valid for 30 days from the date of issue",
        "• Payment terms: 50% upfront, 50% upon completion",
        "• Project timeline will be finalized upon acceptance",
        "• Any changes to scope may affect pricing",
        "• Support and maintenance included for 3 months post-migration"
    ]
    
    for term in terms:
        story.append(Paragraph(term, styles['Normal']))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 20))
    
    # Contact Information
    story.append(Paragraph("Contact Information", heading_style))
    contact_info = [
        ['Email:', 'sales@yourcompany.com'],
        ['Phone:', '+1 (555) 123-4567'],
        ['Website:', 'www.yourcompany.com']
    ]
    
    contact_table = Table(contact_info, colWidths=[1*inch, 5*inch])
    contact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#343a40')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#495057'))
    ]))
    story.append(contact_table)
    
    # Build PDF
    doc.build(story)
    return buffer

# HubSpot Integration APIs
@app.route('/api/hubspot/test-connection', methods=['GET'])
def test_hubspot_connection():
    """Test HubSpot API connection"""
    try:
        import sys
        import os
        # Add parent directory to path for HubSpot import
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from hubspot.hubspot_basic import HubSpotBasic
        
        hubspot = HubSpotBasic()
        result = hubspot.test_connection()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"HubSpot connection test failed: {str(e)}"
        }), 500

@app.route('/api/hubspot/fetch-contacts', methods=['GET'])
def fetch_hubspot_contacts():
    """Fetch contacts from HubSpot"""
    try:
        import sys
        import os
        # Add parent directory to path for HubSpot import
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from hubspot.hubspot_basic import HubSpotBasic
        
        hubspot = HubSpotBasic()
        result = hubspot.get_basic_contacts(limit=50)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch HubSpot contacts: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
