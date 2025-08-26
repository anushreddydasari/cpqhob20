from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from mongodb_collections import (
    EmailCollection, SMTPCollection, QuoteCollection,
    ClientCollection, PricingCollection, 
    HubSpotContactCollection, HubSpotIntegrationCollection,
    FormTrackingCollection, TemplateCollection, HubSpotQuoteCollection
)
from cpq.pricing_logic import calculate_quote
from flask import send_file
from templates import PDFGenerator
from cpq.email_service import EmailService
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploaded_docs')
ALLOWED_DOCX_EXTENSIONS = {'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 

# Initialize collections
quotes = QuoteCollection()
clients = ClientCollection()
hubspot_contacts = HubSpotContactCollection()
hubspot_integration = HubSpotIntegrationCollection()
email_collection = EmailCollection()
smtp_collection = SMTPCollection()
pricing = PricingCollection()
form_tracking = FormTrackingCollection()
template_collection = TemplateCollection()
hubspot_quotes = HubSpotQuoteCollection()



# Initialize PDF generator
pdf_generator = PDFGenerator()

def _build_template_data_from_quote(quote: dict) -> dict:
    """Builds the template_data dict used for DOCX exports from a quote document.

    Returns a flat dict of placeholder keys → values.
    """
    client = quote.get('client', {}) if isinstance(quote, dict) else {}
    quote_block = quote.get('quote', {}) if isinstance(quote, dict) else {}
    standard_total = (quote_block.get('standard', {}) or {}).get('totalCost', 0)

    template_data = {
        'client_name': client.get('name', 'N/A'),
        'client_company': client.get('company', 'N/A'),
        'client_email': client.get('email', 'N/A'),
        'client_phone': client.get('phone', 'N/A'),
        'company_name': 'Your Company LLC',
        'company_email': 'contact@yourcompany.com',
        'company_phone': '+1-555-0123',
        'company_address': '123 Business St, City, State 12345',
        'service_type': client.get('serviceType', 'Services'),
        'total_cost': standard_total,
        'amount': standard_total,
        'start_date': datetime.now().strftime('%B %d, %Y'),
        'end_date': (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y'),
        'generation_date': datetime.now().strftime('%B %d, %Y'),
        'payment_schedule': '50% upfront, 50% upon completion',
        'payment_method': 'Bank transfer or check',
        'confidentiality_period': '5 years',
        'warranty_period': '1 year',
        'termination_notice': '30 days written notice'
    }

    return template_data

def _find_quote_by_identifier(identifier: str):
    """Find a quote by ID or by client name/company (case-insensitive). Returns the most recent match.

    identifier can be a Mongo ObjectId string or a plain name/company string.
    """
    if not identifier:
        return None
    # Try direct by ID first (manual quotes)
    try:
        q = quotes.get_quote_by_id(identifier)
        if q:
            return q
    except Exception:
        pass
    # Try HubSpot quotes by ID
    try:
        q = hubspot_quotes.get_quote_by_id(identifier)
        if q:
            return q
    except Exception:
        pass
    # Fallback: search by client name or company (lenient match)
    try:
        all_quotes = quotes.get_all_quotes(limit=1000)
        all_hs_quotes = hubspot_quotes.get_all_quotes(limit=1000)
        matches = []
        def _norm(v):
            s = str(v or "").lower().strip()
            # collapse internal whitespace
            s = " ".join(s.split())
            return s
        ident_lower = _norm(identifier)
        for q in all_quotes + all_hs_quotes:
            client = q.get('client', {})
            name = _norm(client.get('name', ''))
            company = _norm(client.get('company', ''))
            if (
                name == ident_lower or company == ident_lower or
                (ident_lower and (ident_lower in name or ident_lower in company))
            ):
                matches.append(q)
        if matches:
            # Pick the most recent by 'created_at' or 'timestamp'
            def _ts(q):
                return q.get('created_at') or q.get('timestamp') or 0
            matches.sort(key=_ts, reverse=True)
            return matches[0]
    except Exception:
        pass
    return None

@app.route('/')
def serve_frontend():
    return send_from_directory('cpq', 'index.html')

@app.route('/quote-calculator')
def serve_quote_calculator():
    return send_from_directory('cpq', 'quote-calculator.html')

@app.route('/quote-template')
def serve_quote_template():
    return send_from_directory('cpq', 'quote-template.html')

@app.route('/template-builder')
def serve_template_builder():
    return send_from_directory('cpq', 'template-builder.html')

@app.route('/client-management')
def serve_client_management():
    return send_from_directory('cpq', 'client-management.html')

@app.route('/hubspot-data')
def serve_hubspot_data():
    return send_from_directory('hubspot', 'hubspot-data.html')

@app.route('/hubspot-cpq-setup')
def serve_hubspot_cpq_setup():
    return send_from_directory('hubspot', 'hubspot-cpq-setup.html')

@app.route('/signature-form')
def serve_signature_form():
    return send_from_directory('templates', 'signature_form.html')

# Serve uploaded files (e.g., images) for use in templates
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return jsonify({'success': False, 'message': f'File not found: {str(e)}'}), 404

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

# Form Tracking APIs
@app.route('/api/form/create-session', methods=['POST'])
def create_form_session():
    """Create a new form tracking session"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        client_data = data.get('client_data')
        form_type = data.get('form_type', 'signature')
        
        if not quote_id or not client_data:
            return jsonify({"success": False, "message": "Quote ID and client data required"}), 400
        
        # Create form session
        session_id = form_tracking.create_form_session(
            quote_id=quote_id,
            client_data=client_data,
            form_type=form_type
        )
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Form session created successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating form session: {str(e)}"
        }), 500

@app.route('/api/form/track/interaction', methods=['POST'])
def track_form_interaction():
    """Track form field interactions"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        print(f"🔍 Tracking interaction - Session ID: {session_id}")
        print(f"🔍 Data received: {data}")
        
        if not session_id:
            return jsonify({"success": False, "message": "Session ID required"}), 400
        
        # Log the interaction
        result = form_tracking.log_field_interaction(
            session_id=session_id,
            action=data.get('action'),
            field_name=data.get('field_name'),
            details=data.get('details')
        )
        
        print(f"✅ Interaction tracked successfully: {result}")
        
        return jsonify({"success": True, "message": "Interaction tracked"}), 200
        
    except Exception as e:
        print(f"❌ Error tracking interaction: {str(e)}")
        print(f"❌ Exception type: {type(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Error tracking interaction: {str(e)}"
        }), 500

@app.route('/api/form/track/error', methods=['POST'])
def track_form_error():
    """Track form errors"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"success": False, "message": "Session ID required"}), 400
        
        # Log the error
        form_tracking.log_error(
            session_id=session_id,
            error_type=data.get('error_type'),
            error_details=data.get('error_details'),
            stack_trace=data.get('stack_trace')
        )
        
        return jsonify({"success": True, "message": "Error tracked"}), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error tracking error: {str(e)}"
        }), 500

@app.route('/api/form/track/page-exit', methods=['POST'])
def track_page_exit():
    """Track when user leaves the form page"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        quote_id = data.get('quote_id')
        
        if not quote_id:
            return jsonify({"success": False, "message": "Quote ID required"}), 400
        
        # Create session if not exists
        session_id = form_tracking.create_form_session(
            quote_id=quote_id,
            client_data={'email': 'unknown@example.com'}
        )
        
        # Log the page exit
        form_tracking.log_page_exit(
            session_id=session_id,
            time_spent=data.get('time_spent', 0),
            final_stats=data.get('final_stats', {})
        )
        
        return jsonify({"success": True, "message": "Page exit tracked"}), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error tracking page exit: {str(e)}"
        }), 500

@app.route('/api/form/submit-signature', methods=['POST'])
def submit_signature():
    """Submit signature form and track approval"""
    try:
        data = request.get_json()
        
        # Create form session if not exists
        quote_id = data.get('quote_id', 'unknown')
        session_id = form_tracking.create_form_session(
            quote_id=quote_id,
            client_data={
                'name': data.get('approverName'),
                'email': data.get('approverEmail'),
                'title': data.get('approverTitle')
            }
        )
        
        # Log the form submission
        approval_data = {
            'approver_name': data.get('approverName'),
            'approver_title': data.get('approverTitle'),
            'approver_email': data.get('approverEmail'),
            'approver_phone': data.get('approverPhone'),
            'terms_accepted': data.get('termsAccepted'),
            'budget_approved': data.get('budgetApproved'),
            'timeline_accepted': data.get('timelineAccepted'),
            'signature_data': data.get('signatureData'),
            'signature_text': data.get('signatureText'),
            'comments': data.get('comments'),
            'tracking': data.get('tracking', {})
        }
        
        form_tracking.log_form_submission(
            session_id=session_id,
            approval_data=approval_data,
            success=True
        )
        
        # Send confirmation email
        try:
            email_collection.send_email(
                to_email=data.get('approverEmail'),
                subject="Quote Approval Confirmation",
                body=f"""
                Thank you for approving the quote!
                
                Approver: {data.get('approverName')}
                Title: {data.get('approverTitle')}
                Company: {data.get('companyName', 'N/A')}
                
                Your approval has been recorded and the project team has been notified.
                
                Best regards,
                Migration Services Team
                """
            )
        except Exception as email_error:
            print(f"Email sending failed: {email_error}")
        
        return jsonify({
            "success": True,
            "message": "Signature submitted successfully",
            "session_id": session_id
        }), 200
        
    except Exception as e:
        print(f"Error submitting signature: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error submitting signature: {str(e)}"
        }), 500

@app.route('/api/form/analytics/<session_id>', methods=['GET'])
def get_form_analytics(session_id):
    """Get analytics for a specific form session"""
    try:
        session_data = form_tracking.get_session_by_id(session_id)
        
        if not session_data:
            return jsonify({"success": False, "message": "Session not found"}), 500
        
        return jsonify({
            "success": True,
            "analytics": session_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching analytics: {str(e)}"
        }), 500

@app.route('/api/form/analytics', methods=['GET'])
def get_all_form_analytics():
    """Get analytics for all form sessions"""
    try:
        analytics_data = form_tracking.get_tracking_stats()
        
        return jsonify({
            "success": True,
            "analytics": analytics_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching analytics: {str(e)}"
        }), 500

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

@app.route('/api/quote/send-signature-form', methods=['POST'])
def send_signature_form_email():
    """Send signature form link via email to client"""
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        signature_url = data.get('signature_url')
        quote_data = data.get('quote_data', {})
        
        if not all([recipient_email, recipient_name, company_name, signature_url]):
            return jsonify({
                "success": False,
                "message": "Recipient email, name, company, and signature URL are required"
            }), 400
        
        # Import email service
        from cpq.email_service import EmailService
        
        # Create professional email content
        subject = f"Action Required: Please Sign Your Migration Service Quote - {company_name}"
        
        # Safely format the total amount
        try:
            total_amount = quote_data.get('total', 0)
            if total_amount is None:
                total_amount = 0
            formatted_total = f"${float(total_amount):,.2f}"
        except (ValueError, TypeError):
            formatted_total = "$0.00"
        
        body = f"""
Dear {recipient_name},

Thank you for your interest in our Migration Services. We've prepared a detailed quote for your project and need your approval to proceed.

**Quote Summary:**
- Service Type: {quote_data.get('service_type', 'Migration Services')}
- Total Amount: {formatted_total}

**Next Steps:**
1. Click the link below to access your digital signature form
2. Review the quote details
3. Fill out the approval form
4. Sign digitally or type your signature
5. Submit your approval

**🔗 Click Here to Sign Your Quote:**
{signature_url}

**What Happens After Approval:**
- Your approval will be recorded in our system
- Our project team will be notified immediately
- You'll receive a confirmation email
- Project planning will begin within 24 hours

**Need Help?**
If you have any questions or need assistance, please reply to this email or contact our support team.

**Security Note:**
This link is unique to you and your quote. Please do not share it with others.

Best regards,
Migration Services Team

---
This is an automated message. Please do not reply to this email address.
        """
        
        # Send email using email service
        email_service = EmailService()
        email_result = email_service.send_signature_form_email(
            recipient_email, recipient_name, company_name, body
        )
        
        if email_result['success']:
            # Log email sent
            email_collection.log_email_sent({
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "company_name": company_name,
                "email_type": "signature_form",
                "signature_url": signature_url,
                "quote_data": quote_data
            })
            
            return jsonify({
                "success": True,
                "message": "Signature form email sent successfully",
                "email_result": email_result
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send email",
                "email_result": email_result
            }), 500
        
    except Exception as e:
        print(f"Error sending signature form email: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to send signature form email: {str(e)}"
        }), 500

# New Quote Management Routes
@app.route('/quote-management')
def serve_quote_management():
    return send_from_directory('cpq', 'quote-management.html')



@app.route('/api/email/send-quote', methods=['POST'])
def send_quote_email_new():
    try:
        data = request.json
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        client_phone = data.get('client_phone', '')
        service_type = data.get('service_type')
        requirements = data.get('requirements', '')

        if not all([recipient_email, recipient_name, company_name, service_type]):
            return jsonify({'success': False, 'message': 'Missing required fields'})

        # Create email content
        subject = f"Quote Request - {service_type}"
        body = f"""
        Dear {recipient_name},

        Thank you for your interest in our {service_type}.

        Company: {company_name}
        Phone: {client_phone}
        Requirements: {requirements}

        We will review your requirements and get back to you with a detailed quote within 24 hours.

        Best regards,
        Your Team
        """

        # Send email using your existing email service
        email_service = EmailService()
        success = email_service.send_email(recipient_email, subject, body)

        if success:
            return jsonify({'success': True, 'message': 'Quote email sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send email'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/generate-pdf-by-lookup', methods=['POST'])
def generate_pdf_by_lookup():
    try:
        data = request.json
        lookup_type = data.get('lookup_type')
        lookup_value = data.get('lookup_value')

        if not lookup_type or not lookup_value:
            return jsonify({'success': False, 'message': 'Missing lookup parameters'}), 400

        # Import quote collection to fetch real data
        from mongodb_collections.quote_collection import QuoteCollection
        quote_collection = QuoteCollection()
        
        # Find quote based on lookup type
        quote_data = None
        if lookup_type == 'quoteId':
            quote_data = quote_collection.get_quote_by_id(lookup_value)
        elif lookup_type == 'username':
            # Search by client name
            all_quotes = quote_collection.get_all_quotes(limit=1000)
            for quote in all_quotes:
                if quote.get('client', {}).get('name', '').lower() == lookup_value.lower():
                    quote_data = quote
                    break
        elif lookup_type == 'company':
            # Search by company name
            all_quotes = quote_collection.get_all_quotes(limit=1000)
            for quote in all_quotes:
                if quote.get('client', {}).get('company', '').lower() == lookup_value.lower():
                    quote_data = quote
                    break

        if not quote_data:
            return jsonify({'success': False, 'message': f'No quote found for {lookup_type}: {lookup_value}'}), 404

        # Create professional PDF with real quote data
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Header
        title = Paragraph("Professional Quote", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))

        # Client Information
        client = quote_data.get('client', {})
        client_info = [
            ['Client Name:', client.get('name', 'N/A')],
            ['Email:', client.get('email', 'N/A')],
            ['Company:', client.get('company', 'N/A')],
            ['Phone:', client.get('phone', 'N/A')],
            ['Service Type:', client.get('serviceType', 'N/A')]
        ]
        
        client_table = Table(client_info, colWidths=[100, 300])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(client_table)
        story.append(Spacer(1, 20))

        # Configuration Details
        config = quote_data.get('configuration', {})
        config_info = [
            ['Configuration', 'Value'],
            ['Number of Users:', str(config.get('users', 'N/A'))],
            ['Instance Type:', config.get('instanceType', 'N/A')],
            ['Number of Instances:', str(config.get('instances', 'N/A'))],
            ['Duration (months):', str(config.get('duration', 'N/A'))],
            ['Migration Type:', config.get('migrationType', 'N/A')],
            ['Data Size (GB):', str(config.get('dataSize', 'N/A'))]
        ]
        
        config_table = Table(config_info, colWidths=[200, 200])
        config_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(config_table)
        story.append(Spacer(1, 20))

        # Quote Results
        quote_results = quote_data.get('quote', {})
        if quote_results:
            story.append(Paragraph("Quote Results", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Add pricing details if available
            if 'basic' in quote_results:
                basic = quote_results['basic']
                story.append(Paragraph(f"Basic Plan: ${basic.get('totalCost', 0):,.2f}", styles['Normal']))
            if 'standard' in quote_results:
                standard = quote_results['standard']
                story.append(Paragraph(f"Standard Plan: ${standard.get('totalCost', 0):,.2f}", styles['Normal']))
            if 'advanced' in quote_results:
                advanced = quote_results['advanced']
                story.append(Paragraph(f"Advanced Plan: ${advanced.get('totalCost', 0):,.2f}", styles['Normal']))

        # Requirements
        if client.get('requirements'):
            story.append(Spacer(1, 20))
            story.append(Paragraph("Requirements", styles['Heading2']))
            story.append(Paragraph(client.get('requirements'), styles['Normal']))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Quote ID: {str(quote_data.get('_id', 'N/A'))}", styles['Normal']))

        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"quote_{client.get('name', 'client')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/api/quotes/list')
def list_quotes():
    try:
        from mongodb_collections.quote_collection import QuoteCollection
        quote_collection = QuoteCollection()
        
        # Get all quotes with basic info for lookup
        all_quotes = quote_collection.get_all_quotes(limit=100)
        
        # Format quotes for display
        formatted_quotes = []
        for quote in all_quotes:
            client = quote.get('client', {})
            formatted_quotes.append({
                'id': str(quote.get('_id')),
                'client_name': client.get('name', 'N/A'),
                'client_email': client.get('email', 'N/A'),
                'company': client.get('company', 'N/A'),
                'service_type': client.get('serviceType', 'N/A'),
                'status': quote.get('status', 'draft'),
                'created_at': quote.get('created_at', 'N/A'),
                'total_cost': quote.get('quote', {}).get('standard', {}).get('totalCost', 0)
            })
        
        return jsonify({
            'success': True, 
            'quotes': formatted_quotes,
            'count': len(formatted_quotes)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/agreements/generate-from-quote', methods=['POST'])
def generate_agreement_from_quote():
    """Generate personalized agreement from quote data"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        
        if not quote_id:
            return jsonify({'success': False, 'message': 'Quote ID is required'}), 400
        
        # Get quote data from database
        from mongodb_collections.quote_collection import QuoteCollection
        quote_collection = QuoteCollection()
        quote = quote_collection.get_quote_by_id(quote_id)
        
        if not quote:
            return jsonify({'success': False, 'message': 'Quote not found'}), 404
        
        # Convert ObjectId to string to avoid JSON serialization issues
        quote['_id'] = str(quote['_id'])
        

        
        # Extract quote data for agreement generation
        client = quote.get('client', {})
        quote_data = quote.get('quote', {})
        configuration = quote.get('configuration', {})
        
        # Prepare data for agreement generation
        agreement_data = {
            # Client Information
            'client_name': client.get('name', 'N/A'),
            'client_company': client.get('company', 'N/A'),
            'client_address': client.get('address', 'N/A'),
            'client_email': client.get('email', 'N/A'),
            'client_phone': client.get('phone', 'N/A'),
            'client_title': client.get('title', 'N/A'),
            
            # Service Information
            'service_type': client.get('serviceType', 'N/A'),
            'service_description': client.get('description', 'N/A'),
            'requirements': client.get('requirements', 'N/A'),
            'deliverables': client.get('deliverables', 'N/A'),
            
            # Quote Configuration Details
            'quote_date': datetime.now().strftime('%B %d, %Y'),
            'migration_type': configuration.get('migrationType', 'N/A'),
            'project_duration': configuration.get('duration', 'N/A'),
            'number_of_users': configuration.get('users', 'N/A'),
            'instance_type': configuration.get('instanceType', 'N/A'),
            'number_of_instances': configuration.get('instances', 'N/A'),
            'data_size': configuration.get('dataSize', 'N/A'),
            
            # Pricing Breakdown - Basic Plan
            'basic_per_user_cost': str(quote_data.get('basic', {}).get('perUserCost', 0)),
            'basic_user_total': str(quote_data.get('basic', {}).get('userCost', 0)),
            'basic_data_cost': str(quote_data.get('basic', {}).get('dataCost', 0)),
            'basic_migration_cost': str(quote_data.get('basic', {}).get('migrationCost', 0)),
            'basic_instance_cost': str(quote_data.get('basic', {}).get('instanceCost', 0)),
            'basic_plan_total': str(quote_data.get('basic', {}).get('totalCost', 0)),
            
            # Pricing Breakdown - Standard Plan
            'standard_per_user_cost': str(quote_data.get('standard', {}).get('perUserCost', 0)),
            'standard_user_total': str(quote_data.get('standard', {}).get('userCost', 0)),
            'standard_data_cost': str(quote_data.get('standard', {}).get('dataCost', 0)),
            'standard_migration_cost': str(quote_data.get('standard', {}).get('migrationCost', 0)),
            'standard_instance_cost': str(quote_data.get('standard', {}).get('instanceCost', 0)),
            'standard_plan_total': str(quote_data.get('standard', {}).get('totalCost', 0)),
            
            # Pricing Breakdown - Advanced Plan
            'advanced_per_user_cost': str(quote_data.get('advanced', {}).get('perUserCost', 0)),
            'advanced_user_total': str(quote_data.get('advanced', {}).get('userCost', 0)),
            'advanced_data_cost': str(quote_data.get('advanced', {}).get('dataCost', 0)),
            'advanced_migration_cost': str(quote_data.get('advanced', {}).get('migrationCost', 0)),
            'advanced_instance_cost': str(quote_data.get('advanced', {}).get('instanceCost', 0)),
            'advanced_plan_total': str(quote_data.get('advanced', {}).get('totalCost', 0)),
            
            # Company Information (you can customize these)
            'company_name': 'Your Company Name',
            'company_address': 'Your Company Address',
            'company_website': 'www.yourcompany.com',
            'company_email': 'info@yourcompany.com',
            'company_phone': '+1-555-0123',
            'provider_representative': 'Your Name',
            'provider_title': 'Project Manager',
            
            # Agreement Details
            'agreement_title': f'{client.get("serviceType", "Service")} Agreement',
            'effective_date': datetime.now().strftime('%Y-%m-%d'),
            'start_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() + timedelta(days=configuration.get("duration", 3) * 30)).strftime('%Y-%m-%d'),
            'project_duration': configuration.get("duration", 3),
            'milestone_1': 'Project Planning',
            'milestone_1_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            'milestone_2': 'Development Complete',
            'milestone_2_date': (datetime.now() + timedelta(days=configuration.get("duration", 3) * 30 // 2)).strftime('%Y-%m-%d'),
            'final_delivery_date': (datetime.now() + timedelta(days=configuration.get("duration", 3) * 30)).strftime('%Y-%m-%d'),
            
            # Payment Terms
            'payment_schedule': '50% upfront, 50% upon completion',
            'payment_method': 'Bank Transfer',
            'payment_due_dates': 'Upfront: 7 days, Final: 90 days',
            'late_payment_terms': '2% monthly fee on overdue amounts',
            'overage_charges': '$100 per additional feature',
            
            # Legal Terms (standard business terms)
            'confidentiality_period': '5 years',
            'non_disclosure_terms': 'Standard NDA terms apply',
            'data_protection_terms': 'GDPR compliant',
            'return_materials_terms': 'All materials returned upon completion',
            'warranty_period': '1 year',
            'warranty_coverage': 'Standard warranty applies',
            'liability_limitations': 'Limited to total contract value',
            'force_majeure_terms': 'Standard force majeure clauses apply',
            'service_standards': 'Industry best practices',
            'quality_assurance': 'Comprehensive testing and validation',
            'change_management': 'Change requests require written approval',
            'issue_resolution': '24-hour response time for critical issues',
            'client_responsibilities': 'Provide content, feedback, and approvals',
            'provider_responsibilities': 'Deliver quality code and documentation',
            'ip_terms': 'Client owns final deliverables, provider owns tools',
            'third_party_terms': 'Third-party services billed separately',
            'termination_notice': '30 days written notice',
            'termination_fees': 'Pro-rated based on completion',
            'data_retrieval': 'All data returned within 30 days',
            'renewal_terms': 'Annual maintenance agreement available',
            'governing_law': 'State of Delaware',
            'dispute_process': 'Mediation followed by arbitration',
            'arbitration_terms': 'Binding arbitration in Delaware',
            'legal_jurisdiction': 'Delaware State Courts',
            
            # Agreement Metadata
            'agreement_validity_period': '2 years',
            'agreement_id': f'AG-{quote_id[:8].upper()}',
            'agreement_version': '1.0',
            'generation_date': datetime.now().strftime('%Y-%m-%d'),
            
            # Dates
            'provider_signature_date': datetime.now().strftime('%Y-%m-%d'),
            'client_signature_date': 'Pending'
        }
        
        # Generate agreement content
        personalized_content = (
            f"Agreement for {agreement_data.get('client_name')} at {agreement_data.get('client_company')} "
            f"for {agreement_data.get('service_type')} services. Total: ${agreement_data.get('standard_plan_total', '0')}"
        )

        # Build structured pricing table from quote data (Standard plan)
        standard_plan = quote_data.get('standard', {}) if isinstance(quote_data, dict) else {}
        user_cost = float(standard_plan.get('userCost', 0) or 0)
        data_cost = float(standard_plan.get('dataCost', 0) or 0)
        instance_cost = float(standard_plan.get('instanceCost', 0) or 0)
        migration_cost = float(standard_plan.get('migrationCost', 0) or 0)
        total_cost = float(standard_plan.get('totalCost', 0) or (user_cost + data_cost + instance_cost + migration_cost))

        line_item_1_price = user_cost + data_cost + instance_cost
        line_items = [
            {
                'job_requirement': f"{client.get('serviceType', 'Migration')} Data Migration",
                'description': (
                    f"Up to {configuration.get('users', 'N/A')} Users | "
                    f"{configuration.get('migrationType', 'Migration').title()} | "
                    f"{configuration.get('instanceType', 'Standard').title()} | "
                    f"{configuration.get('dataSize', 'N/A')} GB"
                ),
                'migration_type': 'Managed Migration',
                'price_usd': round(line_item_1_price, 2)
            },
            {
                'job_requirement': 'Managed Migration Service',
                'description': 'Project management, consulting, post-migration support',
                'migration_type': 'Managed Migration',
                'price_usd': round(migration_cost, 2)
            }
        ]
        
        return jsonify({
            'success': True,
            'agreement': {
                'id': 'default',
                'name': 'Auto Generated',
                'type': 'agreement',
                'personalized_content': personalized_content,
                'agreement_data': agreement_data,
                'quote_id': quote_id,
                'generated_at': datetime.now().isoformat()
            },
            'pricing_table': {
                'rows': line_items,
                'total_price': round(total_cost, 2),
                'currency': 'USD'
            },
            'message': 'Personalized agreement generated successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Template Management API Endpoints
@app.route('/api/templates', methods=['GET'])
def get_all_templates():
    """Get all active templates"""
    try:
        templates = template_collection.get_all_templates(active_only=True)
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching templates: {str(e)}'
        }), 500

@app.route('/api/templates', methods=['POST'])
def create_template():
    """Create a new template"""
    try:
        # Support HTML (JSON) and DOCX (multipart/form-data) uploads
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file part'}), 400
            file = request.files['file']
            name = request.form.get('name')
            description = request.form.get('description', '')
            category = request.form.get('category', 'general')
            if not name or not file:
                return jsonify({'success': False, 'message': 'Name and file are required'}), 400
            filename = secure_filename(file.filename)
            if not filename or '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_DOCX_EXTENSIONS:
                return jsonify({'success': False, 'message': 'Only DOCX files are allowed'}), 400
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            file_size = os.path.getsize(save_path)
            payload = {
                'name': name,
                'description': description,
                'category': category,
                'type': 'docx',
                'file_name': filename,
                'file_path': save_path,
                'file_size': file_size,
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'content': '',
                'placeholders': [],
                'clauses': []
            }
            template_id = template_collection.create_template(payload)
            if template_id:
                return jsonify({'success': True, 'message': 'DOCX template uploaded', 'template_id': template_id}), 201
            return jsonify({'success': False, 'message': 'Failed to save template'}), 500
        else:
            data = request.get_json()
            if not data.get('name') or not data.get('content'):
                return jsonify({'success': False, 'message': 'Name and content are required'}), 400
            template_id = template_collection.create_template({**data, 'type': 'html'})
            if template_id:
                return jsonify({'success': True, 'message': 'Template created successfully', 'template_id': template_id}), 201
            return jsonify({'success': False, 'message': 'Failed to create template'}), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating template: {str(e)}'
        }), 500

@app.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    """Get a specific template by ID"""
    try:
        template = template_collection.get_template_by_id(template_id)
        
        if template:
            # Convert ObjectId to string for JSON serialization
            template['_id'] = str(template['_id'])
            template['created_at'] = template['created_at'].isoformat()
            template['updated_at'] = template['updated_at'].isoformat()
            
            # Hide absolute file_path from API response for file-based templates
            if template.get('type') in ('docx',) and 'file_path' in template:
                template['file_available'] = True
                template['file_path'] = None
            return jsonify({'success': True,'template': template}), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Template not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching template: {str(e)}'
        }), 500

@app.route('/api/templates/<template_id>/as-html', methods=['GET'])
def get_template_as_html(template_id):
    """For DOCX templates: convert to HTML for in-app editing"""
    try:
        template = template_collection.get_template_by_id(template_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        if template.get('type') != 'docx':
            return jsonify({'success': False, 'message': 'Template is not a DOCX type'}), 400
        file_path = template.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Template file not found'}), 404

        # Lazy import to avoid hard dependency at import-time
        try:
            import mammoth
        except Exception as e:
            return jsonify({'success': False, 'message': f'Mammoth not installed: {str(e)}'}), 500

        with open(file_path, 'rb') as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value or ''

        return jsonify({'success': True, 'html': html}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error converting template: {str(e)}'}), 500

@app.route('/api/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    """Update an existing template"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('content'):
            return jsonify({
                'success': False,
                'message': 'Name and content are required'
            }), 400
        
        # Update template
        success = template_collection.update_template(template_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Template updated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Template not found or update failed'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating template: {str(e)}'
        }), 500

@app.route('/api/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Soft delete a template"""
    try:
        success = template_collection.delete_template(template_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Template deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Template not found or delete failed'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting template: {str(e)}'
        }), 500

@app.route('/api/templates/search', methods=['GET'])
def search_templates():
    """Search templates by name, description, or content"""
    try:
        search_term = request.args.get('q', '')
        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Search term is required'
            }), 400
        
        templates = template_collection.search_templates(search_term)
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error searching templates: {str(e)}'
        }), 500

@app.route('/api/templates/category/<category>', methods=['GET'])
def get_templates_by_category(category):
    """Get templates by category"""
    try:
        templates = template_collection.get_templates_by_category(category)
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching templates by category: {str(e)}'
        }), 500
@app.route('/api/templates/<template_id>/download-docx', methods=['GET'])
def download_docx_template(template_id):
    try:
        template = template_collection.get_template_by_id(template_id)
        if not template or template.get('type') != 'docx':
            return jsonify({'success': False, 'message': 'DOCX template not found'}), 404
        file_path = template.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found on server'}), 404
        return send_file(file_path, as_attachment=True, download_name=template.get('file_name', 'template.docx'), mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error downloading file: {str(e)}'}), 500

 

@app.route('/api/templates/<template_id>/export-docx', methods=['POST'])
def export_template_as_docx(template_id):
    """Export a template as DOCX with real data"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        
        if not quote_id:
            return jsonify({
                'success': False,
                'message': 'Quote ID is required'
            }), 400
        
        # Get the template
        template = template_collection.get_template_by_id(template_id)
        if not template:
            return jsonify({
                'success': False,
                'message': 'Template not found'
            }), 404
        
        # Get quote data by id or client name/company
        quote = _find_quote_by_identifier(quote_id)
        if not quote:
            return jsonify({
                'success': False,
                'message': 'Quote not found'
            }), 404
        
        # Prepare template data (normalize from our stored quote schema)
        template_data = _build_template_data_from_quote(quote)
        
        # If the template is HTML, generate DOCX from HTML route
        if template.get('type') == 'html':
            from templates.docx_generator import generate_agreement_docx
            success, result = generate_agreement_docx(template['content'], template_data)
        else:
            # For DOCX templates, load file bytes and do placeholder replacement
            file_path = template.get('file_path')
            if not file_path or not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'Template file not found'}), 404
            with open(file_path, 'rb') as f:
                original_bytes = f.read()
            from templates.docx_template_utils import replace_placeholders_in_docx_bytes
            result_bytes = replace_placeholders_in_docx_bytes(original_bytes, template_data)
            success, result = True, result_bytes
        
        if success and isinstance(result, bytes):
            # Return DOCX file for download
            from flask import send_file
            from io import BytesIO
            
            buffer = BytesIO(result)
            buffer.seek(0)
            
            filename = f"agreement_{quote_id}_{datetime.now().strftime('%Y%m%d')}.docx"
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            return jsonify({
                'success': False,
                'message': result if isinstance(result, str) else 'Failed to generate DOCX'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error exporting template: {str(e)}'
        }), 500

@app.route('/api/templates/export-docx', methods=['POST'])
def export_template_content_as_docx():
    """Export template content directly as DOCX (for unsaved templates)"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        template_content = data.get('template_content')
        template_name = data.get('template_name', 'Template')
        
        if not template_content:
            return jsonify({
                'success': False,
                'message': 'Template content is required'
            }), 400
        
        # Prepare template data
        if quote_id:
            # Get quote data by id or client name/company
            quote = _find_quote_by_identifier(quote_id)
            if not quote:
                return jsonify({
                    'success': False,
                    'message': 'Quote not found'
                }), 404
            template_data = _build_template_data_from_quote(quote)
        else:
            # No quote provided; export with placeholders untouched (will show [placeholder] labels)
            template_data = {}
        
        # Import DOCX generator
        from templates.docx_generator import generate_agreement_docx
        success, result = generate_agreement_docx(template_content, template_data)
        
        if success and isinstance(result, bytes):
            # Return DOCX file for download
            from flask import send_file
            from io import BytesIO
            
            buffer = BytesIO(result)
            buffer.seek(0)
            
            suffix = quote_id if quote_id else 'noquote'
            filename = f"{template_name}_{suffix}_{datetime.now().strftime('%Y%m%d')}.docx"
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            return jsonify({
                'success': False,
                'message': result if isinstance(result, str) else 'Failed to generate DOCX'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error exporting template: {str(e)}'
        }), 500

@app.route('/api/templates/available-fields', methods=['GET'])
def get_available_template_fields():
    """Return available placeholder fields for templates.

    Optional query param: quote_id (can be ObjectId, client name, or company)
    When provided, returns fields based on that quote; otherwise returns defaults.
    """
    try:
        quote_id = request.args.get('quote_id')
        template_data = {}
        if quote_id:
            quote = _find_quote_by_identifier(quote_id)
            if quote:
                template_data = _build_template_data_from_quote(quote)
            else:
                return jsonify({'success': False, 'message': 'Quote not found'}), 404
        else:
            # Default set without a specific quote
            template_data = {
                'client_name': 'N/A',
                'client_company': 'N/A',
                'client_email': 'N/A',
                'client_phone': 'N/A',
                'company_name': 'Your Company LLC',
                'company_email': 'contact@yourcompany.com',
                'company_phone': '+1-555-0123',
                'company_address': '123 Business St, City, State 12345',
                'service_type': 'Services',
                'total_cost': 0,
                'amount': 0,
                'start_date': datetime.now().strftime('%B %d, %Y'),
                'end_date': (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y'),
                'generation_date': datetime.now().strftime('%B %d, %Y'),
                'payment_schedule': '50% upfront, 50% upon completion',
                'payment_method': 'Bank transfer or check',
                'confidentiality_period': '5 years',
                'warranty_period': '1 year',
                'termination_notice': '30 days written notice'
            }

        return jsonify({'success': True, 'fields': sorted(list(template_data.keys())), 'template_data': template_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching fields: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,  # Back to port 5000 since we're in root
        use_reloader=False,  # Prevents duplicate processes
        threaded=True
    )
