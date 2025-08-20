from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from cpq.db import quotes_collection, clients_collection, hubspot_contacts_collection, quote_status_collection
from cpq.pricing_logic import calculate_quote
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
    return send_from_directory('cpq', 'index.html')

@app.route('/quote-calculator')
def serve_quote_calculator():
    return send_from_directory('cpq', 'quote-calculator.html')

@app.route('/quote-template')
def serve_quote_template():
    return send_from_directory('cpq', 'quote-template.html')

@app.route('/client-management')
def serve_client_management():
    return send_from_directory('cpq', 'client-management.html')

@app.route('/hubspot-data')
def serve_hubspot_data():
    return send_from_directory('hubspot', 'hubspot-data.html')

@app.route('/hubspot-cpq-setup')
def serve_hubspot_cpq_setup():
    return send_from_directory('hubspot', 'hubspot-cpq-setup.html')

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
        
        # Debug logging
        print(f"Received data: {data}")
        
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
            
            # Debug logging for numeric values
            print(f"Parsed values - users: {users}, instances: {instances}, duration: {duration}, data_size: {data_size}")
            
        except (ValueError, TypeError) as e:
            print(f"Validation error: {e}")
            return jsonify({
                "success": False,
                "message": f"Invalid numeric values provided: {str(e)}"
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
            result = quotes_collection.insert_one({
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
            
            # Return the quote ID for email sending
            return jsonify({
                "success": True,
                "quote": results,
                "quote_id": str(result.inserted_id)
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
    """Fetch contacts from HubSpot and store in MongoDB"""
    try:
        from hubspot.hubspot_basic import HubSpotBasic
        
        hubspot = HubSpotBasic()
        result = hubspot.get_basic_contacts(limit=50)
        
        # If contacts fetched successfully, store them in MongoDB
        if result.get('success') and result.get('contacts'):
            stored_contacts = []
            for contact in result['contacts']:
                # Prepare contact data for MongoDB
                contact_data = {
                    "hubspot_id": contact.get('id'),
                    "name": contact.get('name', ''),
                    "email": contact.get('email', ''),
                    "phone": contact.get('phone', ''),
                    "company": contact.get('company', ''),
                    "job_title": contact.get('job_title', ''),
                    "source": "HubSpot",
                    "fetched_at": datetime.now(),
                    "status": "new"
                }
                
                # Check if contact already exists (by HubSpot ID)
                existing_contact = hubspot_contacts_collection.find_one({"hubspot_id": contact.get('id')})
                
                if existing_contact:
                    # Update existing contact
                    hubspot_contacts_collection.update_one(
                        {"hubspot_id": contact.get('id')},
                        {"$set": contact_data}
                    )
                    contact_data['action'] = 'updated'
                else:
                    # Insert new contact
                    hubspot_contacts_collection.insert_one(contact_data)
                    contact_data['action'] = 'inserted'
                
                stored_contacts.append(contact_data)
            
            # Add storage info to result
            result['stored_contacts'] = stored_contacts
            result['message'] = f"Successfully fetched and stored {len(stored_contacts)} contacts in MongoDB"
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch HubSpot contacts: {str(e)}"
        }), 500

# Quote Status Tracking & Email APIs
@app.route('/api/quote/status', methods=['POST'])
def update_quote_status():
    """Update quote status"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not quote_id or not new_status:
            return jsonify({
                "success": False,
                "message": "Quote ID and status are required"
            }), 400
        
        # Update quote status
        result = quotes_collection.update_one(
            {"_id": quote_id},
            {"$set": {"status": new_status, "updated_at": datetime.now()}}
        )
        
        if result.matched_count == 0:
            return jsonify({
                "success": False,
                "message": "Quote not found"
            }), 404
        
        # Log status change
        status_log = {
            "quote_id": quote_id,
            "status": new_status,
            "notes": notes,
            "changed_at": datetime.now(),
            "changed_by": "system"  # You can add user authentication later
        }
        
        quote_status_collection.insert_one(status_log)
        
        return jsonify({
            "success": True,
            "message": f"Quote status updated to {new_status}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to update quote status: {str(e)}"
        }), 500

@app.route('/api/quote/send-email', methods=['POST'])
def send_quote_email():
    """Send quote via email"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        
        if not all([quote_id, recipient_email, recipient_name, company_name]):
            return jsonify({
                "success": False,
                "message": "Quote ID, recipient email, name, and company are required"
            }), 500
        
        # Get quote data
        quote = quotes_collection.find_one({"_id": quote_id})
        if not quote:
            return jsonify({
                "success": False,
                "message": "Quote not found"
            }), 404
        
        # Import email service
        from cpq.email_service import EmailService
        
        # Send email
        email_service = EmailService()
        email_result = email_service.send_quote_email(
            recipient_email, recipient_name, company_name, quote.get('quote', {})
        )
        
        if email_result['success']:
            # Update quote status to 'sent'
            quotes_collection.update_one(
                {"_id": quote_id},
                {"$set": {"status": "sent", "email_sent_at": datetime.now()}}
            )
            
            # Log email sent
            email_log = {
                "quote_id": quote_id,
                "recipient_email": recipient_email,
                "sent_at": datetime.now(),
                "email_result": email_result
            }
            quote_status_collection.insert_one(email_log)
            
            return jsonify({
                "success": True,
                "message": "Quote email sent successfully",
                "email_result": email_result
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send email",
                "email_result": email_result
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to send quote email: {str(e)}"
        }), 500

@app.route('/api/email/test-connection', methods=['GET'])
def test_email_connection():
    """Test Gmail SMTP connection"""
    try:
        from cpq.email_service import EmailService
        
        email_service = EmailService()
        result = email_service.test_connection()
        
        return jsonify({
            "success": True,
            "message": "Email connection test successful",
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Email connection test failed: {str(e)}"
        }), 500

@app.route('/api/quote/send-email-direct', methods=['POST'])
def send_quote_email_direct():
    """Send quote email directly without saving quote first"""
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        quote_data = data.get('quote_data', {})
        quote_results = data.get('quote_results', {})
        
        if not all([recipient_email, recipient_name, company_name]):
            return jsonify({
                "success": False,
                "message": "Recipient email, name, and company are required"
            }), 400
        
        # Import email service
        from cpq.email_service import EmailService
        
        # Send email directly
        email_service = EmailService()
        email_result = email_service.send_quote_email(
            recipient_email, recipient_name, company_name, quote_results
        )
        
        if email_result['success']:
            # Log email sent (optional - for tracking)
            email_log = {
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "company_name": company_name,
                "sent_at": datetime.now(),
                "email_result": email_result,
                "quote_data": quote_data,
                "sent_without_saving": True
            }
            quote_status_collection.insert_one(email_log)
            
            return jsonify({
                "success": True,
                "message": "Quote email sent successfully",
                "email_result": email_result
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send email",
                "email_result": email_result
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to send quote email: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,  # Back to port 5000 since we're in root
        use_reloader=False,  # Prevents duplicate processes
        threaded=True
    )
