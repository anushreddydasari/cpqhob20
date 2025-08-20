from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from mongodb_collections import (
    EmailCollection, SMTPCollection, QuoteCollection,
    ClientCollection, PricingCollection, 
    HubSpotContactCollection, HubSpotIntegrationCollection,
    PDFTrackingCollection
)
from cpq.pricing_logic import calculate_quote
from flask import send_file
from templates import PDFGenerator

app = Flask(__name__)
CORS(app)

# Initialize collections
quotes = QuoteCollection()
clients = ClientCollection()
hubspot_contacts = HubSpotContactCollection()
hubspot_integration = HubSpotIntegrationCollection()
email_collection = EmailCollection()
smtp_collection = SMTPCollection()
pricing = PricingCollection()


# Initialize PDF generator
pdf_generator = PDFGenerator()

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
        
        # Save to MongoDB using collection
        result = clients.create_client(data)
        
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
        clients_data = clients.get_all_clients()
        return jsonify({
            "success": True,
            "clients": clients_data
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
        data = request.get_json()
        data['updated_at'] = datetime.now()
        
        # Remove _id if present
        if '_id' in data:
            del data['_id']
        
        result = clients.update_client(client_id, data)
        
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
        result = clients.delete_client(client_id)
        
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

        # Save quote to MongoDB using collection
        try:
            quote_data = {
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
            }
            result = quotes.create_quote(quote_data)
            
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
        
        # Create PDF using template
        pdf_buffer = pdf_generator.create_quote_pdf(client_data, quote_data, configuration)
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
                    "job_title": contact.get('job_title', ''),
                    "company": contact.get('company', ''),
                    "source": "HubSpot",
                    "fetched_at": datetime.now(),
                    "status": "new"
                }
                
                # Store contact using collection
                store_result = hubspot_contacts.store_contact(contact_data)
                # The store_contact method already sets the action in contact_data
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
        
        # Update quote status using collection
        result = quotes.update_quote_status(quote_id, new_status, notes)
        
        if result.matched_count == 0:
            return jsonify({
                "success": False,
                "message": "Quote not found"
            }), 404
        
        # Log status change using collection
        hubspot_integration.log_api_call({
            "quote_id": quote_id,
            "status": new_status,
            "notes": notes,
            "changed_by": "system"
        })
        
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
        
        # Get quote data using collection
        quote = quotes.get_quote_by_id(quote_id)
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
            quotes.update_quote_status(quote_id, "sent")
            
            # Log email sent
            email_collection.log_email_sent({
                "quote_id": quote_id,
                "recipient_email": recipient_email,
                "email_result": email_result
            })
            
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
            email_collection.log_email_sent({
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "company_name": company_name,
                "quote_data": quote_data,
                "sent_without_saving": True
            })
            
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
