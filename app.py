from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from mongodb_collections import (
    EmailCollection, SMTPCollection, QuoteCollection,
    ClientCollection, PricingCollection, 
    HubSpotContactCollection, HubSpotIntegrationCollection,
    FormTrackingCollection
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
form_tracking = FormTrackingCollection()


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

@app.route('/signature-form')
def serve_signature_form():
    return send_from_directory('templates', 'signature_form.html')

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

if __name__ == '__main__':
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5010,  # Back to port 5000 since we're in root
        use_reloader=False,  # Prevents duplicate processes
        threaded=True
    )
