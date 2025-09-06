from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from utils.file_path_handler import file_handler
from mongodb_collections import (
    EmailCollection, SMTPCollection, QuoteCollection,
    ClientCollection, PricingCollection, 
    HubSpotContactCollection, HubSpotIntegrationCollection,
    HubSpotDealCollection,
    FormTrackingCollection, TemplateCollection, HubSpotQuoteCollection,
    GeneratedPDFCollection, GeneratedAgreementCollection,
    ApprovalWorkflowCollection
)
from mongodb_collections.template_builder_collection import TemplateBuilderCollection
from mongodb_collections.signature_certificate_collection import SignatureCertificateCollection
from cpq.pricing_logic import calculate_quote
from flask import send_file
from templates import PDFGenerator
from cpq.email_service import EmailService
from werkzeug.utils import secure_filename
from mongodb_collections.signature_collection import SignatureCollection
from integrations.google_docs import upsert_doc_from_template, export_doc_as_pdf
try:
    from googleapiclient.errors import HttpError as GHttpError
except Exception:  # pragma: no cover
    GHttpError = Exception

load_dotenv()
# Enable OAuth over http for local development if not already set
if not os.getenv('OAUTHLIB_INSECURE_TRANSPORT'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
try:
    from template_builder import template_builder_bp
    app.register_blueprint(template_builder_bp)
except Exception:
    # Blueprint is optional during partial environments/tests
    pass
# OAuth endpoints for Google
@app.route('/oauth/login')
def oauth_login():
    try:
        from google_auth_oauthlib.flow import Flow
        from flask import request, redirect
        client_path = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET_PATH')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/oauth/callback')
        scopes = (os.getenv('OAUTH_SCOPES') or 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents').split()
        flow = Flow.from_client_secrets_file(client_path, scopes=scopes)
        flow.redirect_uri = redirect_uri
        auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        # If the user wants a JSON payload add ?raw=1, otherwise redirect to Google
        if request.args.get('raw'):
            return jsonify({'success': True, 'auth_url': auth_url, 'state': state})
        return redirect(auth_url)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/oauth/callback')
def oauth_callback():
    try:
        from google_auth_oauthlib.flow import Flow
        from google.auth.transport.requests import Request
        client_path = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET_PATH')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/oauth/callback')
        scopes = (os.getenv('OAUTH_SCOPES') or 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents').split()
        flow = Flow.from_client_secrets_file(client_path, scopes=scopes)
        flow.redirect_uri = redirect_uri
        # full URL with query string
        import flask
        authorization_response = flask.request.url
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json')
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        return jsonify({'success': True, 'message': 'OAuth token saved.', 'token_path': token_path})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
CORS(app)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploaded_docs')
ALLOWED_DOCX_EXTENSIONS = {'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 

# Initialize collections
quotes = QuoteCollection()
clients = ClientCollection()
hubspot_contacts = HubSpotContactCollection()
hubspot_integration = HubSpotIntegrationCollection()
hubspot_deals = HubSpotDealCollection()
email_collection = EmailCollection()
smtp_collection = SMTPCollection()
pricing = PricingCollection()
form_tracking = FormTrackingCollection()
template_collection = TemplateCollection()
hubspot_quotes = HubSpotQuoteCollection()
signatures = SignatureCollection()
generated_pdfs = GeneratedPDFCollection()
generated_agreements = GeneratedAgreementCollection()
signature_certificate_collection = SignatureCertificateCollection()
approval_workflows = ApprovalWorkflowCollection()




# Initialize PDF generator
pdf_generator = PDFGenerator()

def _build_template_data_from_quote(quote: dict) -> dict:
    """Builds the template_data dict used for DOCX exports from a quote document.

    Returns a flat dict of placeholder keys → values.
    """
    client = quote.get('client', {}) if isinstance(quote, dict) else {}
    configuration = quote.get('configuration', {}) if isinstance(quote, dict) else {}
    quote_block = quote.get('quote', {}) if isinstance(quote, dict) else {}
    # Pricing blocks (may be missing)
    basic = (quote_block.get('basic') or {}) if isinstance(quote_block, dict) else {}
    standard = (quote_block.get('standard') or {}) if isinstance(quote_block, dict) else {}
    advanced = (quote_block.get('advanced') or {}) if isinstance(quote_block, dict) else {}
    standard_total = (standard or {}).get('totalCost', 0)

    def _money(val):
        try:
            return f"${float(val or 0):,.2f}"
        except Exception:
            return "$0.00"

    # Subtotals (user + data + instance) per plan
    def _subtotal(plan: dict):
        try:
            return float(plan.get('totalUserCost', 0) or 0) + float(plan.get('dataCost', 0) or 0) + float(plan.get('instanceCost', 0) or 0)
        except Exception:
            return 0.0
    basic_subtotal = _subtotal(basic)
    standard_subtotal = _subtotal(standard)
    advanced_subtotal = _subtotal(advanced)

    template_data = {
        'client_name': client.get('name', 'N/A'),
        'client_company': client.get('company', 'N/A'),
        'client_email': client.get('email', 'N/A'),
        'client_phone': client.get('phone', 'N/A'),
        'client_title': client.get('title', client.get('job_title', '')),  # support HubSpot job title
        'company_name': 'Your Company LLC',
        'company_email': 'contact@yourcompany.com',
        'company_phone': '+1-555-0123',
        'company_address': '123 Business St, City, State 12345',
        'service_type': client.get('serviceType', 'Services'),
        'total_cost': standard_total,
        'amount': standard_total,
        'total_cost_formatted': _money(standard_total),
        'amount_formatted': _money(standard_total),
        'start_date': datetime.now().strftime('%B %d, %Y'),
        'end_date': (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y'),
        'generation_date': datetime.now().strftime('%B %d, %Y'),
        'payment_schedule': '50% upfront, 50% upon completion',
        'payment_method': 'Bank transfer or check',
        'confidentiality_period': '5 years',
        'warranty_period': '1 year',
        'termination_notice': '30 days written notice',



        # CPQ configuration placeholders
        'config_users': configuration.get('users', ''),
        'config_instance_type': configuration.get('instanceType', ''),
        'config_instances': configuration.get('instances', ''),
        'config_duration_months': configuration.get('duration', ''),
        'config_migration_type': configuration.get('migrationType', ''),
        'config_data_size_gb': configuration.get('dataSize', ''),

        # Quote results - Basic plan
        'basic_per_user_cost': basic.get('perUserCost', 0),
        'basic_total_user_cost': basic.get('totalUserCost', 0),
        'basic_data_cost': basic.get('dataCost', 0),
        'basic_migration_cost': basic.get('migrationCost', 0),
        'basic_instance_cost': basic.get('instanceCost', 0),
        'basic_total_cost': basic.get('totalCost', 0),
        'basic_subtotal_cost': basic_subtotal,
        'basic_subtotal_cost_formatted': _money(basic_subtotal),
        'basic_per_user_cost_formatted': _money(basic.get('perUserCost', 0)),
        'basic_total_user_cost_formatted': _money(basic.get('totalUserCost', 0)),
        'basic_data_cost_formatted': _money(basic.get('dataCost', 0)),
        'basic_migration_cost_formatted': _money(basic.get('migrationCost', 0)),
        'basic_instance_cost_formatted': _money(basic.get('instanceCost', 0)),
        'basic_total_cost_formatted': _money(basic.get('totalCost', 0)),

        # Quote results - Standard plan
        'standard_per_user_cost': standard.get('perUserCost', 0),
        'standard_total_user_cost': standard.get('totalUserCost', 0),
        'standard_data_cost': standard.get('dataCost', 0),
        'standard_migration_cost': standard.get('migrationCost', 0),
        'standard_instance_cost': standard.get('instanceCost', 0),
        'standard_total_cost': standard.get('totalCost', 0),
        'standard_subtotal_cost': standard_subtotal,
        'standard_subtotal_cost_formatted': _money(standard_subtotal),
        'standard_per_user_cost_formatted': _money(standard.get('perUserCost', 0)),
        'standard_total_user_cost_formatted': _money(standard.get('totalUserCost', 0)),
        'standard_data_cost_formatted': _money(standard.get('dataCost', 0)),
        'standard_migration_cost_formatted': _money(standard.get('migrationCost', 0)),
        'standard_instance_cost_formatted': _money(standard.get('instanceCost', 0)),
        'standard_total_cost_formatted': _money(standard.get('totalCost', 0)),

        # Quote results - Advanced plan
        'advanced_per_user_cost': advanced.get('perUserCost', 0),
        'advanced_total_user_cost': advanced.get('totalUserCost', 0),
        'advanced_data_cost': advanced.get('dataCost', 0),
        'advanced_migration_cost': advanced.get('migrationCost', 0),
        'advanced_instance_cost': advanced.get('instanceCost', 0),
        'advanced_total_cost': advanced.get('totalCost', 0),
        'advanced_subtotal_cost': advanced_subtotal,
        'advanced_subtotal_cost_formatted': _money(advanced_subtotal),
        'advanced_per_user_cost_formatted': _money(advanced.get('perUserCost', 0)),
        'advanced_total_user_cost_formatted': _money(advanced.get('totalUserCost', 0)),
        'advanced_data_cost_formatted': _money(advanced.get('dataCost', 0)),
        'advanced_migration_cost_formatted': _money(advanced.get('migrationCost', 0)),
        'advanced_instance_cost_formatted': _money(advanced.get('instanceCost', 0)),
        'advanced_total_cost_formatted': _money(advanced.get('totalCost', 0))
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
    return send_from_directory('template_builder', 'template-builder.html')

@app.route('/client-management')
def serve_client_management():
    return send_from_directory('cpq', 'client-management.html')

@app.route('/hubspot-data')
def serve_hubspot_data():
    return send_from_directory('deal_pages', 'hubspot-data.html')

@app.route('/hubspot-cpq-setup')
def serve_hubspot_cpq_setup():
    return send_from_directory('deal_pages', 'hubspot-cpq-setup.html')

@app.route('/hubspot-deals')
def serve_hubspot_deals():
    return send_from_directory('deal_pages', 'hubspot-deals.html')

@app.route('/debug-pdf')
def serve_debug_pdf():
    return send_from_directory('.', 'debug_pdf_viewing.html')

@app.route('/api/system/info')
def get_system_info():
    """API endpoint to check current environment and URLs"""
    try:
        from utils.url_helper import get_environment_info, log_environment_detection
        
        # Log environment detection for debugging
        log_environment_detection()
        
        # Get environment information
        env_info = get_environment_info()
        
        return jsonify({
            'success': True,
            'message': 'System information retrieved successfully',
            'data': env_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'message': 'URL helper module not available',
            'error': str(e),
            'fallback_info': {
                'environment': 'unknown',
                'base_url': 'http://localhost:5000',
                'render_info': {
                    'is_render': bool(os.getenv('RENDER')),
                    'service_name': os.getenv('RENDER_SERVICE_NAME'),
                    'external_url': os.getenv('RENDER_EXTERNAL_URL')
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error retrieving system information',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })



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

        # Serialize MongoDB documents for JSON (ObjectId, datetime)
        serialized_clients = []
        for client_doc in clients_data:
            try:
                safe_doc = dict(client_doc)

                # Normalize field names expected by the frontend
                safe_doc['clientName'] = safe_doc.get('clientName') or safe_doc.get('name')
                safe_doc['companyName'] = safe_doc.get('companyName') or safe_doc.get('company')
                safe_doc['phoneNumber'] = safe_doc.get('phoneNumber') or safe_doc.get('phone')

                if '_id' in safe_doc:
                    safe_doc['_id'] = str(safe_doc['_id'])

                # Convert datetimes to ISO strings if present
                created_at = safe_doc.get('created_at')
                updated_at = safe_doc.get('updated_at')
                if hasattr(created_at, 'isoformat'):
                    safe_doc['created_at'] = created_at.isoformat()
                if hasattr(updated_at, 'isoformat'):
                    safe_doc['updated_at'] = updated_at.isoformat()

                serialized_clients.append(safe_doc)
            except Exception:
                # If serialization fails for a document, skip it rather than 500 the whole request
                continue

        return jsonify({
            "success": True,
            "clients": serialized_clients
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
        form_type = data.get('form_type', 'form_interaction')
        
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
        # Fetch most recently updated contacts for freshness
        result = hubspot.get_recent_contacts(limit=50)
        
        # If contacts fetched successfully, store them in MongoDB (side-effect)
        contacts_list = result.get('contacts', []) if result.get('success') else []
        if contacts_list:
            for contact in contacts_list:
                contact_data = {
                    "hubspot_id": contact.get('id'),
                    "name": contact.get('name', ''),
                    "email": contact.get('email', ''),
                    "phone": contact.get('phone', ''),
                    "job_title": contact.get('job_title', ''),
                    "company": contact.get('company', ''),
                    "source": "HubSpot",
                    # Datetimes are stored in MongoDB but not returned in the API response
                    "fetched_at": datetime.now(),
                    "status": "new"
                }
                hubspot_contacts.store_contact(contact_data)

        # Return a sanitized JSON payload containing only serializable data
        return jsonify({
            "success": bool(result.get('success')),
            "contacts": contacts_list,
            "total": len(contacts_list)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch HubSpot contacts: {str(e)}"
        }), 500

@app.route('/api/hubspot/sync-client', methods=['POST'])
def sync_client_from_hubspot():
    """Update a local client using latest data from HubSpot by email."""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        client_id = data.get('client_id')  # optional

        if not email:
            return jsonify({"success": False, "message": "email is required"}), 400

        from hubspot.hubspot_basic import HubSpotBasic
        hubspot = HubSpotBasic()
        hs = hubspot.get_contact_by_email(email)

        if not hs.get('success'):
            message = 'HubSpot contact not found' if hs.get('error') == 'not_found' else f"HubSpot error: {hs.get('error')}"
            status = 404 if hs.get('error') == 'not_found' else 502
            return jsonify({"success": False, "message": message}), status

        contact = hs['contact']

        update_payload = {
            'clientName': contact.get('name'),
            'companyName': contact.get('company'),
            'email': contact.get('email'),
            'phoneNumber': contact.get('phone'),
            'serviceType': 'HubSpot',
        }

        updated = False
        if client_id:
            result = clients.update_client(client_id, update_payload)
            updated = result.matched_count > 0
        else:
            existing = clients.get_client_by_email(email)
            if existing:
                result = clients.update_client(str(existing['_id']), update_payload)
                updated = result.matched_count > 0
                client_id = str(existing['_id'])
            else:
                insert_result = clients.create_client(update_payload)
                client_id = str(insert_result.inserted_id)
                updated = True

        return jsonify({
            'success': True,
            'message': 'Client synced from HubSpot',
            'client_id': client_id,
            'updated': updated,
            'hubspot': contact
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to sync client from HubSpot: {str(e)}'
        }), 500

# HubSpot Deal APIs
@app.route('/api/hubspot/fetch-deals', methods=['GET'])
def fetch_hubspot_deals():
    """Fetch deals from HubSpot and store in MongoDB"""
    try:
        from hubspot.hubspot_basic import HubSpotBasic
        
        hubspot = HubSpotBasic()
        # Fetch most recently updated deals for freshness
        result = hubspot.get_recent_deals(limit=50)
        
        # If deals fetched successfully, store them in MongoDB
        deals_list = result.get('deals', []) if result.get('success') else []
        if deals_list:
            for deal in deals_list:
                deal_data = {
                    "hubspot_id": deal.get('id'),
                    "dealname": deal.get('dealname', ''),
                    "amount": deal.get('amount', ''),
                    "closedate": deal.get('closedate', ''),
                    "dealstage": deal.get('dealstage', ''),
                    "dealtype": deal.get('dealtype', ''),
                    "pipeline": deal.get('pipeline', ''),
                    "hubspot_owner_id": deal.get('hubspot_owner_id', ''),
                    "company": deal.get('company', ''),
                    "source": "HubSpot",
                    "fetched_at": datetime.now(),
                    "status": "new"
                }
                hubspot_deals.store_deal(deal_data)

        # Return a sanitized JSON payload containing only serializable data
        return jsonify({
            "success": bool(result.get('success')),
            "deals": deals_list,
            "total": len(deals_list)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch HubSpot deals: {str(e)}"
        }), 500

@app.route('/api/hubspot/deal/<deal_id>', methods=['GET'])
def get_hubspot_deal(deal_id):
    """Get a specific HubSpot deal by ID"""
    try:
        from hubspot.hubspot_basic import HubSpotBasic
        
        hubspot = HubSpotBasic()
        result = hubspot.get_deal_by_id(deal_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Deal not found')
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch deal: {str(e)}"
        }), 500

@app.route('/api/hubspot/deals/search', methods=['POST'])
def search_hubspot_deals():
    """Search deals by company name"""
    try:
        data = request.get_json() or {}
        company_name = data.get('company_name')
        
        if not company_name:
            return jsonify({"success": False, "message": "company_name is required"}), 400

        from hubspot.hubspot_basic import HubSpotBasic
        hubspot = HubSpotBasic()
        result = hubspot.get_deals_by_company(company_name, limit=20)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to search deals: {str(e)}"
        }), 500

# Signature APIs
@app.route('/api/signatures', methods=['POST'])
def save_signature():
    try:
        data = request.get_json() or {}
        data['signed_ip'] = request.headers.get('X-Forwarded-For', request.remote_addr)
        data['signed_user_agent'] = request.headers.get('User-Agent')
        new_id = signatures.save_signature(data)
        return jsonify({'success': True, 'signature_id': new_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving signature: {str(e)}'}), 500

@app.route('/api/signatures/latest', methods=['GET'])
def get_latest_signature():
    try:
        role = request.args.get('role')
        email = request.args.get('email')
        if not role or not email:
            return jsonify({'success': False, 'message': 'role and email are required'}), 400
        sig = signatures.get_latest_signature(role, email)
        return jsonify({'success': True, 'signature': sig}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching signature: {str(e)}'}), 500

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
        
        # Generate PDF first if not exists
        pdf_path = None
        try:
            # Check if PDF already exists for this quote
            existing_pdfs = generated_pdfs.get_pdfs_by_quote_id(quote_id)
            if existing_pdfs:
                pdf_path = existing_pdfs[0].get('file_path')
            
            # If no PDF exists, generate one
            if not pdf_path or not os.path.exists(pdf_path):
                pdf_buffer = pdf_generator.create_quote_pdf(
                    quote.get('client', {}), 
                    quote.get('quote', {}), 
                    quote.get('configuration', {})
                )
                pdf_buffer.seek(0)
                
                # Save PDF to documents directory
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"quote_{quote.get('client', {}).get('name', 'client')}_{timestamp}.pdf"
                file_path = os.path.join('documents', filename)
                
                # Ensure documents directory exists
                os.makedirs('documents', exist_ok=True)
                
                # Save PDF file
                with open(file_path, 'wb') as f:
                    f.write(pdf_buffer.getvalue())
                
                # Store PDF metadata in MongoDB
                pdf_metadata = {
                    'quote_id': quote_id,
                    'filename': filename,
                    'file_path': file_path,
                    'client_name': quote.get('client', {}).get('name', 'N/A'),
                    'company_name': quote.get('client', {}).get('company', 'N/A'),
                    'service_type': quote.get('client', {}).get('serviceType', 'N/A'),
                    'file_size': len(pdf_buffer.getvalue())
                }
                
                try:
                    generated_pdfs.store_pdf_metadata(pdf_metadata)
                    pdf_path = file_path
                except Exception as e:
                    print(f"Warning: Failed to store PDF metadata: {e}")
        except Exception as e:
            print(f"Warning: Failed to generate PDF: {e}")
        
        # Send email with PDF attachment
        email_service = EmailService()
        email_result = email_service.send_quote_email(
            recipient_email, recipient_name, company_name, quote.get('quote', {}), pdf_path
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
        
        # Generate PDF for the quote data
        pdf_path = None
        try:
            # Create PDF using template
            pdf_buffer = pdf_generator.create_quote_pdf(
                {
                    'name': recipient_name,
                    'company': company_name,
                    'email': recipient_email,
                    'serviceType': quote_data.get('serviceType', 'Migration Services')
                }, 
                quote_results, 
                quote_data.get('configuration', {})
            )
            pdf_buffer.seek(0)
            
            # Save PDF to documents directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"quote_{recipient_name}_{timestamp}.pdf"
            file_path = os.path.join('documents', filename)
            
            # Ensure documents directory exists
            os.makedirs('documents', exist_ok=True)
            
            # Save PDF file
            with open(file_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            
            pdf_path = file_path
        except Exception as e:
            print(f"Warning: Failed to generate PDF: {e}")
        
        # Send email with PDF attachment
        email_service = EmailService()
        email_result = email_service.send_quote_email(
            recipient_email, recipient_name, company_name, quote_results, pdf_path
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



# New Quote Management Routes
@app.route('/quote-management')
def serve_quote_management():
    return send_from_directory('cpq', 'quote-management.html')

@app.route('/debug-documents')
def serve_debug_documents():
    return send_from_directory('.', 'debug_document_loading.html')


@app.route('/approval-dashboard')
def serve_approval_dashboard():
    return send_from_directory('approval_workflow', 'approval-dashboard.html')



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
    """Generate PDF from quote lookup and store it"""
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

        # Save PDF to documents directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quote_{client.get('name', 'client')}_{timestamp}.pdf"
        file_path = os.path.join('documents', filename)
        
        # Ensure documents directory exists
        os.makedirs('documents', exist_ok=True)
        
        # Save PDF file
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Store PDF metadata in MongoDB
        pdf_metadata = {
            'quote_id': str(quote_data.get('_id')),
            'filename': filename,
            'file_path': file_path,
            'client_name': client.get('name', 'N/A'),
            'company_name': client.get('company', 'N/A'),
            'service_type': client.get('serviceType', 'N/A'),
            'file_size': len(buffer.getvalue())
        }
        
        try:
            generated_pdfs.store_pdf_metadata(pdf_metadata)
        except Exception as e:
            print(f"Warning: Failed to store PDF metadata: {e}")
        
        # Return the PDF for download
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/api/quotes/list')
def list_quotes():
    """Get all quotes with basic info for lookup"""
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
        template_id = data.get('template_id')
        
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
            'agreement_date': datetime.now().strftime('%Y-%m-%d'),
            'effective_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Generate agreement content
        personalized_content = (
            f"Agreement for {agreement_data.get('client_name')} at {agreement_data.get('client_company')} "
            f"for {agreement_data.get('service_type')} services. Total: ${agreement_data.get('standard_plan_total', '0')}"
        )
        
        # If template_id is provided, use the template structure
        template_content = None
        if template_id:
            try:
                from mongodb_collections.template_builder_collection import TemplateBuilderCollection
                template_collection = TemplateBuilderCollection()
                template = template_collection.get_template_by_id(template_id)
                
                if template and template.get('blocks'):
                    # Build template content from blocks
                    template_content = ""
                    for block in template.get('blocks', []):
                        if block.get('type') == 'text':
                            template_content += f"<div class='text-block'>{block.get('content', '')}</div>"
                        elif block.get('type') == 'image':
                            template_content += f"<div class='image-block'>{block.get('content', '')}</div>"
                        elif block.get('type') == 'table':
                            template_content += f"<div class='table-block'>{block.get('content', '')}</div>"
                        elif block.get('type') == 'toc':
                            template_content += f"<div class='toc-block'>{block.get('content', '')}</div>"
                        else:
                            template_content += f"<div class='block'>{block.get('content', '')}</div>"
                    
                    # Replace placeholders in template content
                    for key, value in agreement_data.items():
                        placeholder = f'[{key}]'
                        template_content = template_content.replace(placeholder, str(value))
                        
                    # Replace common placeholders
                    template_content = template_content.replace('[client_name]', agreement_data.get('client_name', 'N/A'))
                    template_content = template_content.replace('[client_company]', agreement_data.get('client_company', 'N/A'))
                    template_content = template_content.replace('[service_type]', agreement_data.get('service_type', 'N/A'))
                    template_content = template_content.replace('[quote_total]', f"${agreement_data.get('standard_plan_total', '0')}")
                    template_content = template_content.replace('[agreement_id]', agreement_data.get('agreement_id', 'N/A'))
                    template_content = template_content.replace('[effective_date]', agreement_data.get('effective_date', 'N/A'))
                    
            except Exception as e:
                print(f"Warning: Failed to load template {template_id}: {e}")
                template_content = None

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
        
        # Store agreement metadata in MongoDB
        agreement_metadata = {
            'quote_id': quote_id,
            'filename': f"agreement_{client.get('name', 'client')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            'file_path': f"documents/agreement_{client.get('name', 'client')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            'client_name': client.get('name', 'N/A'),
            'company_name': client.get('company', 'N/A'),
            'service_type': client.get('serviceType', 'N/A'),
            'file_size': len(personalized_content.encode('utf-8')),
            'content': personalized_content,
            'agreement_data': agreement_data
        }
        
        try:
            # Ensure documents directory exists
            os.makedirs('documents', exist_ok=True)
            
            # Generate PDF from the agreement content
            try:
                from weasyprint import HTML
                from io import BytesIO
                
                # Create a simple HTML template for the agreement
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Agreement - {client.get('name', 'Client')}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .header {{ text-align: center; border-bottom: 2px solid #667eea; padding-bottom: 20px; margin-bottom: 30px; }}
                        .content {{ white-space: pre-wrap; font-size: 14px; }}
                        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }}
                        .company-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                        .company-info strong {{ color: #667eea; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>📋 Service Agreement</h1>
                        <div class="company-info">
                            <strong>Client:</strong> {client.get('name', 'N/A')}<br>
                            <strong>Company:</strong> {client.get('company', 'N/A')}<br>
                            <strong>Service Type:</strong> {client.get('serviceType', 'N/A')}<br>
                            <strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}
                        </div>
                    </div>
                    <div class="content">{personalized_content}</div>
                    <div class="footer">
                        <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>
                </body>
                </html>
                """
                
                # Create PDF
                html_doc = HTML(string=html_content)
                pdf_bytes = html_doc.write_pdf()
                
                # Save PDF file
                with open(agreement_metadata['file_path'], 'wb') as f:
                    f.write(pdf_bytes)
                
                # Update file size to actual PDF size
                agreement_metadata['file_size'] = len(pdf_bytes)
                
                print(f"✅ PDF Agreement generated: {agreement_metadata['filename']}")
                
            except ImportError:
                print("⚠️ WeasyPrint not available, falling back to text file")
                # Fallback to text file if WeasyPrint is not available
                with open(agreement_metadata['file_path'].replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
                    f.write(personalized_content)
                # Update metadata for text file
                agreement_metadata['filename'] = agreement_metadata['filename'].replace('.pdf', '.txt')
                agreement_metadata['file_path'] = agreement_metadata['file_path'].replace('.pdf', '.txt')
                
            # Store agreement metadata in MongoDB
            generated_agreements.store_agreement_metadata(agreement_metadata)
            print(f"✅ Agreement stored in MongoDB: {agreement_metadata['filename']}")
            
        except Exception as e:
            print(f"Warning: Failed to store agreement metadata: {e}")
        
        return jsonify({
            'success': True,
            'agreement': {
                'id': 'default',
                'name': 'Auto Generated',
                'type': 'agreement',
                'personalized_content': personalized_content,
                'template_content': template_content,  # Include template content if used
                'agreement_data': agreement_data,
                'quote_id': quote_id,
                'template_id': template_id,  # Include template ID if used
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

@app.route('/api/agreements/generate-pdf', methods=['POST'])
def generate_agreement_pdf():
    """Generate and store agreement PDF from quote data"""
    try:
        data = request.get_json()
        quote_id = data.get('quote_id')
        
        if not quote_id:
            return jsonify({'success': False, 'message': 'Quote ID is required'}), 400
        
        # Get quote data
        quote = quotes.get_quote_by_id(quote_id)
        if not quote:
            return jsonify({'success': False, 'message': 'Quote not found'}), 404
        
        # Build template data
        template_data = _build_template_data_from_quote(quote)
        
        # Read the agreement template
        template_path = os.path.join('cpq', 'purchase_agreement_pdf_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Replace placeholders with actual data
        for key, value in template_data.items():
            placeholder = f'{{{{{key}}}}}'
            template_content = template_content.replace(placeholder, str(value))
        
        # Generate PDF from HTML template
        try:
            from weasyprint import HTML
            from io import BytesIO
            
            # Create PDF
            html_doc = HTML(string=template_content)
            pdf_bytes = html_doc.write_pdf()
            
            # Save PDF to documents directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"agreement_{template_data.get('client_name', 'client')}_{timestamp}.pdf"
            file_path = os.path.join('documents', filename)
            
            # Ensure documents directory exists
            os.makedirs('documents', exist_ok=True)
            
            # Save PDF file
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Store agreement metadata in MongoDB
            agreement_metadata = {
                'quote_id': quote_id,
                'filename': filename,
                'file_path': file_path,
                'client_name': template_data.get('client_name', 'N/A'),
                'company_name': template_data.get('client_company', 'N/A'),
                'service_type': template_data.get('service_type', 'N/A'),
                'file_size': len(pdf_bytes)
            }
            
            try:
                generated_agreements.store_agreement_metadata(agreement_metadata)
            except Exception as e:
                print(f"Warning: Failed to store agreement metadata: {e}")
            
            # Return the PDF for download
            buffer = BytesIO(pdf_bytes)
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except ImportError:
            return jsonify({
                'success': False, 
                'message': 'PDF generation not available. WeasyPrint is not installed.'
            }), 500
        except Exception as e:
            return jsonify({'success': False, 'message': f'PDF generation error: {str(e)}'}), 500
        
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

@app.route('/api/templates/generate-agreement-for-signature', methods=['POST'])
def generate_agreement_for_signature():
    """Generate agreement for signature workflow (returns JSON with agreement_id)"""
    try:
        data = request.get_json()
        
        # Extract all the template data
        company_name = data.get('companyName', 'CloudFuze')
        company_address = data.get('companyAddress', '2500 Regency Parkway, Cary, NC 27518')
        client_company = data.get('clientCompany', 'Client Company')
        client_name = data.get('clientName', 'Client Name')
        service_type = data.get('serviceType', 'Migration Service')
        service_description = data.get('serviceDescription', 'Service description')
        total_price = data.get('totalPrice', 0)
        currency = data.get('currency', 'USD')
        start_date = data.get('startDate', datetime.now().strftime('%Y-%m-%d'))
        end_date = data.get('endDate', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        ceo_signature = data.get('ceoSignature', {})
        client_signature = data.get('clientSignature', {})
        
        # Generate the PDF (same as the main function)
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        # Create PDF using ReportLab
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            alignment=1  # Center
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            alignment=1
        )
        
        # PAGE 1: MAIN AGREEMENT
        story.append(Paragraph(f"{company_name} Purchase Agreement for {client_company}", title_style))
        story.append(Spacer(1, 20))
        
        # Service description
        story.append(Paragraph(f"This agreement provides <b>{client_company}</b> with pricing for use of the {company_name}'s X-Change Enterprise Data Migration Solution:", styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Service table
        service_data = [
            ['Job Requirement', 'Description', 'Migration Type', f'Price({currency})'],
            [f'{company_name} X-Change Data Migration', 
             f'{service_description}<br/><br/><b>Valid for One Month</b>', 
             'Managed Migration<br/>One-Time', 
             f'${total_price:.2f}']
        ]
        
        service_table = Table(service_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1*inch])
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b8dff0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(service_table)
        story.append(Spacer(1, 15))
        
        # Total price
        story.append(Paragraph(f"<b>Total Price: ${total_price:.2f}</b>", ParagraphStyle('TotalPrice', parent=styles['Normal'], fontSize=14, alignment=2)))
        story.append(Spacer(1, 20))
        
        # Payment notes
        story.append(Paragraph("Important Payment Notes:", styles['Heading3']))
        payment_notes = [
            "100% pre-payment before initiating the migration.",
            f"All prices are in US dollars ({currency}).",
            "Any required sales taxes are not included in the above agreement.",
            "Overage Charges: $35 per User | $500 per Additional Month",
            f"Initial Service Term: {start_date} till {end_date}"
        ]
        for note in payment_notes:
            story.append(Paragraph(f"• {note}", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # SaaS Agreement
        story.append(Paragraph("SAAS SERVICE AGREEMENT:", styles['Heading3']))
        saas_text = f"""
        This SaaS Services Agreement ("Agreement") is entered on this <b>{datetime.now().strftime('%m/%d/%Y')}</b> (the "Effective Date") between 
        <b>{company_name}, Inc.</b> with a place of business at <b>{company_address}</b> ("Company"), and the 
        Customer listed above ("Customer"). This Agreement includes and incorporates the above Order Form, In Scope 
        Features list Exhibit ("Exhibit 1"), Out of Scope Features list Exhibit ("Exhibit 2"), all attachments hereto, as well as 
        the attached Terms and Conditions and contains, among other things, warranty disclaimers, liability limitations and 
        use limitations. There shall be no force or effect to any different terms of any related purchase order or similar form 
        even if signed by the parties after the date hereof.
        """
        story.append(Paragraph(saas_text, styles['Normal']))
        
        # PAGE BREAK
        story.append(PageBreak())
        
        # PAGE 2: SIGNATURE PAGE
        story.append(Paragraph(f"{company_name} Purchase Agreement for {client_company}", header_style))
        story.append(Spacer(1, 30))
        
        # Signature section
        signature_data = [
            [f"For {company_name}, Inc.", f"For {client_company}"],
            ["", ""],  # Signature lines
            [f"Name: {ceo_signature.get('name', 'Adi Nandyala')}", f"Name: {client_signature.get('name', client_name)}"],
            [f"Title: {ceo_signature.get('title', 'Director of operations')}", f"Title: {client_signature.get('title', 'Client Title')}"],
            [f"Date: {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}", f"Date: {client_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}"]
        ]
        
        signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 30),  # Space for signatures
            ('LINEBELOW', (0, 1), (-1, 1), 1, colors.black),  # Signature lines
            ('ALIGN', (0, 2), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ]))
        story.append(signature_table)
        story.append(Spacer(1, 30))
        
        # Terms and Conditions
        story.append(Paragraph("TERMS AND CONDITIONS", styles['Heading3']))
        terms_text = """
        Subject to the terms of this Agreement, Company will use commercially reasonable efforts to provide Customer the 
        Migration Services. As part of the registration process, Customer will identify an administrative username and 
        password for Customer's Company account. Company reserves the right to refuse registration of or cancel 
        passwords it deems inappropriate.
        """
        story.append(Paragraph(terms_text, styles['Normal']))
        
        # PAGE BREAK
        story.append(PageBreak())
        
        # PAGE 3: SIGNATURE CERTIFICATE
        story.append(Paragraph("Signature Certificate", ParagraphStyle('CertificateTitle', parent=styles['Heading1'], fontSize=24, alignment=1, textColor=colors.HexColor('#1a73e8'))))
        story.append(Paragraph(f"Reference number: {datetime.now().strftime('%Y%m%d%H%M%S')}", ParagraphStyle('Reference', parent=styles['Normal'], fontSize=10, alignment=1)))
        story.append(Spacer(1, 20))
        
        # Document info
        doc_info = f"""
        <b>Document:</b> {company_name} Purchase Agreement for {client_company}<br/>
        <b>Company:</b> {company_name}<br/>
        <b>Client:</b> {client_company}<br/>
        <b>Service:</b> {service_type}<br/>
        <b>Amount:</b> ${total_price:.2f}
        """
        story.append(Paragraph(doc_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Certificate table
        cert_data = [
            ['Signer', 'Timestamp', 'Signature'],
            [f"<b>{ceo_signature.get('name', 'Adi Nandyala')}</b><br/>{ceo_signature.get('email', 'adi.nandyala@cloudfuze.com')}<br/><br/><b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
             f"<b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
             f"✓ Digital Signature<br/>{ceo_signature.get('data', '')}"],
            [f"<b>{client_signature.get('name', client_name)}</b><br/>{client_signature.get('email', 'client@company.com')}<br/><br/><b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
             f"<b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
             f"✓ Digital Signature<br/>{client_signature.get('data', '')}"]
        ]
        
        cert_table = Table(cert_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        cert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        story.append(cert_table)
        story.append(Spacer(1, 20))
        
        # Completion info
        completion_text = f"Document completed by all parties on: {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>Page 1 of 1"
        story.append(Paragraph(completion_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Save PDF to documents directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"agreement_{client_name.replace(' ', '_')}_{timestamp}.pdf"
        
        # Use file handler to get correct path
        file_handler.ensure_documents_directory()
        file_path = file_handler.get_document_path(filename)
        
        # Save PDF file
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Store agreement metadata in MongoDB
        agreement_metadata = {
            'quote_id': f'template_{timestamp}',
            'filename': filename,
            'file_path': file_path,
            'client_name': client_name,
            'company_name': client_company,
            'service_type': service_type,
            'file_size': len(pdf_bytes),
            'template_data': data,  # Store the original template data
            'signatures': {
                'ceo': ceo_signature,
                'client': client_signature
            }
        }
        
        try:
            generated_agreements.store_agreement_metadata(agreement_metadata)
            print(f"✅ Agreement metadata stored: {filename}")
        except Exception as e:
            print(f"Warning: Failed to store agreement metadata: {e}")
        
        # Return JSON response for signature workflow
        return jsonify({
            'success': True,
            'agreement_id': f'template_{timestamp}',
            'filename': filename,
            'message': 'Agreement generated successfully for signature workflow'
        })
        
    except Exception as e:
        print(f"Error in generate_agreement_for_signature: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating agreement: {str(e)}'
        }), 500

@app.route('/api/templates/generate-agreement-pdf', methods=['POST'])
def generate_agreement_pdf_from_template():
    """Generate agreement PDF from template builder data"""
    try:
        data = request.get_json()
        
        # Extract all the template data
        company_name = data.get('companyName', 'CloudFuze')
        company_address = data.get('companyAddress', '2500 Regency Parkway, Cary, NC 27518')
        client_company = data.get('clientCompany', 'Client Company')
        client_name = data.get('clientName', 'Client Name')
        service_type = data.get('serviceType', 'Migration Service')
        service_description = data.get('serviceDescription', 'Service description')
        total_price = data.get('totalPrice', 0)
        currency = data.get('currency', 'USD')
        start_date = data.get('startDate', datetime.now().strftime('%Y-%m-%d'))
        end_date = data.get('endDate', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        ceo_signature = data.get('ceoSignature', {})
        client_signature = data.get('clientSignature', {})
        
        # Create 3-page HTML content for the complete agreement
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{company_name} Purchase Agreement for {client_company}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.4; }}
                .page-break {{ page-break-before: always; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #ddd; }}
                .company-name {{ font-size: 24px; font-weight: bold; color: #1a73e8; }}
                .microsoft-partner {{ text-align: right; font-weight: bold; color: #666; }}
                .agreement-title {{ text-align: center; font-size: 20px; font-weight: bold; margin: 30px 0; }}
                .service-description {{ margin-bottom: 25px; line-height: 1.6; }}
                .service-table {{ width: 100%; border-collapse: collapse; margin: 25px 0; }}
                .service-table th {{ background: #b8dff0; padding: 12px; text-align: center; font-weight: bold; border: 1px solid #999; }}
                .service-table td {{ padding: 12px; border: 1px solid #999; vertical-align: top; }}
                .total-price {{ text-align: right; font-size: 18px; font-weight: bold; margin-top: 10px; }}
                .payment-notes {{ background: #b8dff0; padding: 15px; margin: 25px 0; border-radius: 5px; }}
                .payment-notes h4 {{ text-align: center; margin-bottom: 10px; font-weight: bold; }}
                .payment-notes ul {{ list-style-type: disc; margin-left: 20px; }}
                .payment-notes li {{ margin-bottom: 8px; }}
                .saas-agreement {{ background: #b8dff0; padding: 15px; margin: 25px 0; border-radius: 5px; }}
                .saas-agreement h4 {{ text-align: center; margin-bottom: 10px; font-weight: bold; }}
                .service-header {{ background: #b8dff0; padding: 10px; text-align: center; font-weight: bold; border: 1px solid #999; }}
                
                /* Page 2 - Signature Page Styles */
                .signature-page {{ text-align: center; padding: 50px 0; }}
                .signature-section {{ display: flex; justify-content: space-between; margin-top: 40px; padding-top: 30px; }}
                .signature-block {{ width: 45%; text-align: center; }}
                .signature-block h4 {{ font-weight: bold; margin-bottom: 20px; text-decoration: underline; }}
                .signature-line {{ border-bottom: 2px solid #333; height: 50px; margin: 10px 0; position: relative; }}
                .signature-info {{ margin-top: 10px; text-align: left; }}
                .signature-info div {{ margin: 5px 0; border-bottom: 1px solid #333; padding-bottom: 5px; }}
                .terms-section {{ background: #b8dff0; padding: 15px; margin: 25px 0; border-radius: 5px; }}
                .terms-section h4 {{ text-align: center; margin-bottom: 10px; font-weight: bold; }}
                
                /* Page 3 - Certificate Styles */
                .certificate-page {{ background: linear-gradient(45deg, #f0f8ff, #e6f3ff); padding: 40px; border: 3px solid #1a73e8; border-radius: 10px; }}
                .certificate-title {{ text-align: center; font-size: 28px; font-weight: bold; color: #1a73e8; margin-bottom: 20px; }}
                .certificate-reference {{ text-align: center; font-size: 14px; color: #666; margin-bottom: 30px; }}
                .certificate-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .certificate-table th {{ background: #1a73e8; color: white; padding: 12px; text-align: center; font-weight: bold; }}
                .certificate-table td {{ padding: 15px; border: 1px solid #ddd; vertical-align: top; background: white; }}
                .completion-info {{ text-align: center; margin-top: 30px; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <!-- PAGE 1: MAIN AGREEMENT -->
            <div class="page">
            <!-- Header with logos -->
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="microsoft-partner">
                    Microsoft Partner<br>
                    <span style="font-size: 12px;">Gold Cloud Productivity</span>
                </div>
            </div>

            <!-- Agreement Title -->
            <div class="agreement-title">
                {company_name} Purchase Agreement for {client_company}
            </div>

            <!-- Service Description -->
            <div class="service-description">
                This agreement provides <strong>{client_company}</strong> with pricing for use of the {company_name}'s X-Change Enterprise Data Migration Solution:
            </div>

            <!-- Service Table Header -->
            <div class="service-header">
                Cloud-Hosted SaaS Solution | Managed Migration | Dedicated Migration Manager
            </div>

            <!-- Service Details Table -->
            <table class="service-table">
                <thead>
                    <tr>
                        <th>Job Requirement</th>
                        <th>Description</th>
                        <th>Migration Type</th>
                        <th>Price({currency})</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="text-align: center; font-weight: bold;">{company_name} X-Change Data Migration</td>
                        <td>
                            {service_description.replace(chr(10), '<br>')}
                            <hr style="margin: 10px 0;">
                            <strong>Valid for One Month</strong>
                        </td>
                        <td style="text-align: center;">
                            Managed Migration<br>
                            One-Time
                        </td>
                        <td style="text-align: right; font-weight: bold;">${total_price:.2f}</td>
                    </tr>
                </tbody>
            </table>

            <!-- Total Price -->
            <div class="total-price">
                <strong>Total Price: ${total_price:.2f}</strong>
            </div>

            <!-- Payment Notes -->
            <div class="payment-notes">
                <h4>Important Payment Notes:</h4>
                <ul>
                    <li>100% pre-payment before initiating the migration.</li>
                    <li>All prices are in US dollars ({currency}).</li>
                    <li>Any required sales taxes are not included in the above agreement.</li>
                    <li>Overage Charges: $35 per User | $500 per Additional Month</li>
                    <li>Initial Service Term: {start_date} till {end_date}</li>
                </ul>
            </div>

            <!-- SaaS Agreement -->
            <div class="saas-agreement">
                <h4>SAAS SERVICE AGREEMENT:</h4>
                <p>
                    This SaaS Services Agreement ("Agreement") is entered on this <strong>{datetime.now().strftime('%m/%d/%Y')}</strong> (the "Effective Date") between 
                    <strong>{company_name}, Inc.</strong> with a place of business at <strong>{company_address}</strong> ("Company"), and the 
                    Customer listed above ("Customer"). This Agreement includes and incorporates the above Order Form, In Scope 
                    Features list Exhibit ("Exhibit 1"), Out of Scope Features list Exhibit ("Exhibit 2"), all attachments hereto, as well as 
                    the attached Terms and Conditions and contains, among other things, warranty disclaimers, liability limitations and 
                    use limitations. There shall be no force or effect to any different terms of any related purchase order or similar form 
                    even if signed by the parties after the date hereof.
                </p>
            </div>
            </div>

            <!-- PAGE 2: SIGNATURE PAGE -->
            <div class="page-break"></div>
            <div class="page signature-page">
                <!-- Header with logos -->
                <div class="header">
                    <div class="company-name">{company_name}</div>
                    <div class="microsoft-partner">
                        Microsoft Partner<br>
                        <span style="font-size: 12px;">Gold Cloud Productivity</span>
                    </div>
                </div>

            <!-- Signature Section -->
            <div class="signature-section">
                <!-- Company Signature -->
                <div class="signature-block">
                    <h4>For {company_name}, Inc.</h4>
                    <div class="signature-line">
                        {f'<div style="font-family: cursive; font-size: 18px; padding-top: 15px;">{ceo_signature.get("data", "")}</div>' if ceo_signature.get("type") == "text" else ""}
                    </div>
                    <div class="signature-info">
                        <div>Name: {ceo_signature.get('name', 'Adi Nandyala')}</div>
                        <div>Title: {ceo_signature.get('title', 'Director of operations')}</div>
                        <div>Date: {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}</div>
                    </div>
                </div>

                <!-- Client Signature -->
                <div class="signature-block">
                    <h4>For {client_company}</h4>
                    <div class="signature-line">
                        {f'<div style="font-family: cursive; font-size: 18px; padding-top: 15px;">{client_signature.get("data", "")}</div>' if client_signature.get("type") == "text" else ""}
                    </div>
                    <div class="signature-info">
                        <div>Name: {client_signature.get('name', client_name)}</div>
                        <div>Title: {client_signature.get('title', 'Client Title')}</div>
                        <div>Date: {client_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}</div>
                    </div>
                </div>
            </div>

            <!-- Terms and Conditions -->
            <div class="terms-section">
                <h4>TERMS AND CONDITIONS</h4>
                <p>
                    Subject to the terms of this Agreement, Company will use commercially reasonable efforts to provide Customer the 
                    Migration Services. As part of the registration process, Customer will identify an administrative username and 
                    password for Customer's Company account. Company reserves the right to refuse registration of or cancel 
                    passwords it deems inappropriate.
                </p>
                </div>
            </div>

            <!-- PAGE 3: SIGNATURE CERTIFICATE -->
            <div class="page-break"></div>
            <div class="page certificate-page">
                <div class="certificate-title">Signature Certificate</div>
                <div class="certificate-reference">Reference number: {datetime.now().strftime('%Y%m%d%H%M%S')}</div>
                
                <div style="margin-bottom: 20px;">
                    <strong>Document:</strong> {company_name} Purchase Agreement for {client_company}<br>
                    <strong>Company:</strong> {company_name}<br>
                    <strong>Client:</strong> {client_company}<br>
                    <strong>Service:</strong> {service_type}<br>
                    <strong>Amount:</strong> ${total_price:.2f}
                </div>

                <table class="certificate-table">
                    <thead>
                        <tr>
                            <th>Signer</th>
                            <th>Timestamp</th>
                            <th>Signature</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <strong>{ceo_signature.get('name', 'Adi Nandyala')}</strong><br/>
                                {ceo_signature.get('email', 'adi.nandyala@cloudfuze.com')}<br/><br/>
                                <strong>Sent:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Viewed:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Signed:</strong> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/>
                                <strong>Recipient Verification:</strong><br/>
                                ✓ Email verified<br/>
                                {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/>
                                <strong>IP address:</strong> 127.0.0.1<br/>
                                <strong>Location:</strong> N/A
                            </td>
                            <td>
                                <strong>Sent:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Viewed:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Signed:</strong> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/>
                                <strong>Recipient Verification:</strong><br/>
                                ✓ Email verified<br/>
                                {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/>
                                <strong>IP address:</strong> 127.0.0.1<br/>
                                <strong>Location:</strong> N/A
                            </td>
                            <td>
                                {f'<div style="font-family: cursive; font-size: 16px; padding: 10px; border: 1px solid #ddd; background: #f9f9f9;">{ceo_signature.get("data", "✓ Digital Signature")}</div>' if ceo_signature.get("data") else "✓ Digital Signature"}
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <strong>{client_signature.get('name', client_name)}</strong><br/>
                                {client_signature.get('email', 'client@company.com')}<br/><br/>
                                <strong>Sent:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Viewed:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Signed:</strong> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/>
                                <strong>Recipient Verification:</strong><br/>
                                ✓ Email verified<br/>
                                {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/>
                                <strong>IP address:</strong> 127.0.0.1<br/>
                                <strong>Location:</strong> N/A
                            </td>
                            <td>
                                <strong>Sent:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Viewed:</strong> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                                <strong>Signed:</strong> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/>
                                <strong>Recipient Verification:</strong><br/>
                                ✓ Email verified<br/>
                                {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/>
                                <strong>IP address:</strong> 127.0.0.1<br/>
                                <strong>Location:</strong> N/A
                            </td>
                            <td>
                                {f'<div style="font-family: cursive; font-size: 16px; padding: 10px; border: 1px solid #ddd; background: #f9f9f9;">{client_signature.get("data", "✓ Digital Signature")}</div>' if client_signature.get("data") else "✓ Digital Signature"}
                            </td>
                        </tr>
                    </tbody>
                </table>

                <div class="completion-info">
                    Document completed by all parties on: {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>
                    Page 1 of 1
                </div>
            </div>
        </body>
        </html>
        """

        # Generate PDF from HTML using WeasyPrint (with ReportLab fallback)
        try:
            # Try WeasyPrint first (better HTML rendering)
            try:
                from weasyprint import HTML
                from io import BytesIO
                
                # Create PDF
                html_doc = HTML(string=html_content)
                pdf_bytes = html_doc.write_pdf()
                
                print("✅ PDF generated successfully using WeasyPrint")
                
            except Exception as weasy_error:
                print(f"WeasyPrint failed: {weasy_error}")
                print("🔄 Falling back to ReportLab...")
                
                # Fallback to ReportLab with 3-page structure
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib import colors
                from reportlab.lib.units import inch
                from io import BytesIO
                
                # Create PDF using ReportLab
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
                story = []
                styles = getSampleStyleSheet()
                
                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=20,
                    spaceAfter=20,
                    alignment=1  # Center
                )
                
                company_style = ParagraphStyle(
                    'CompanyName',
                    parent=styles['Heading2'],
                    fontSize=16,
                    textColor=colors.HexColor('#1a73e8'),
                    spaceAfter=10
                )
                
                header_style = ParagraphStyle(
                    'Header',
                    parent=styles['Heading2'],
                    fontSize=14,
                    spaceAfter=15,
                    alignment=1
                )
                
                # PAGE 1: MAIN AGREEMENT
                story.append(Paragraph(f"{company_name} Purchase Agreement for {client_company}", title_style))
                story.append(Spacer(1, 20))
                
                # Service description
                story.append(Paragraph(f"This agreement provides <b>{client_company}</b> with pricing for use of the {company_name}'s X-Change Enterprise Data Migration Solution:", styles['Normal']))
                story.append(Spacer(1, 15))
                
                # Service table
                service_data = [
                    ['Job Requirement', 'Description', 'Migration Type', f'Price({currency})'],
                    [f'{company_name} X-Change Data Migration', 
                     f'{service_description}<br/><br/><b>Valid for One Month</b>', 
                     'Managed Migration<br/>One-Time', 
                     f'${total_price:.2f}']
                ]
                
                service_table = Table(service_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1*inch])
                service_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b8dff0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(service_table)
                story.append(Spacer(1, 15))
                
                # Total price
                story.append(Paragraph(f"<b>Total Price: ${total_price:.2f}</b>", ParagraphStyle('TotalPrice', parent=styles['Normal'], fontSize=14, alignment=2)))
                story.append(Spacer(1, 20))
                
                # Payment notes
                story.append(Paragraph("Important Payment Notes:", styles['Heading3']))
                payment_notes = [
                    "100% pre-payment before initiating the migration.",
                    f"All prices are in US dollars ({currency}).",
                    "Any required sales taxes are not included in the above agreement.",
                    "Overage Charges: $35 per User | $500 per Additional Month",
                    f"Initial Service Term: {start_date} till {end_date}"
                ]
                for note in payment_notes:
                    story.append(Paragraph(f"• {note}", styles['Normal']))
                
                story.append(Spacer(1, 20))
                
                # SaaS Agreement
                story.append(Paragraph("SAAS SERVICE AGREEMENT:", styles['Heading3']))
                saas_text = f"""
                This SaaS Services Agreement ("Agreement") is entered on this <b>{datetime.now().strftime('%m/%d/%Y')}</b> (the "Effective Date") between 
                <b>{company_name}, Inc.</b> with a place of business at <b>{company_address}</b> ("Company"), and the 
                Customer listed above ("Customer"). This Agreement includes and incorporates the above Order Form, In Scope 
                Features list Exhibit ("Exhibit 1"), Out of Scope Features list Exhibit ("Exhibit 2"), all attachments hereto, as well as 
                the attached Terms and Conditions and contains, among other things, warranty disclaimers, liability limitations and 
                use limitations. There shall be no force or effect to any different terms of any related purchase order or similar form 
                even if signed by the parties after the date hereof.
                """
                story.append(Paragraph(saas_text, styles['Normal']))
                
                # PAGE BREAK
                story.append(PageBreak())
                
                # PAGE 2: SIGNATURE PAGE
                story.append(Paragraph(f"{company_name} Purchase Agreement for {client_company}", header_style))
                story.append(Spacer(1, 30))
                
                # Signature section
                signature_data = [
                    [f"For {company_name}, Inc.", f"For {client_company}"],
                    ["", ""],  # Signature lines
                    [f"Name: {ceo_signature.get('name', 'Adi Nandyala')}", f"Name: {client_signature.get('name', client_name)}"],
                    [f"Title: {ceo_signature.get('title', 'Director of operations')}", f"Title: {client_signature.get('title', 'Client Title')}"],
                    [f"Date: {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}", f"Date: {client_signature.get('date', datetime.now().strftime('%Y-%m-%d'))}"]
                ]
                
                signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
                signature_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 1), (-1, 1), 30),  # Space for signatures
                    ('LINEBELOW', (0, 1), (-1, 1), 1, colors.black),  # Signature lines
                    ('ALIGN', (0, 2), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
                ]))
                story.append(signature_table)
                story.append(Spacer(1, 30))
                
                # Terms and Conditions
                story.append(Paragraph("TERMS AND CONDITIONS", styles['Heading3']))
                terms_text = """
                Subject to the terms of this Agreement, Company will use commercially reasonable efforts to provide Customer the 
                Migration Services. As part of the registration process, Customer will identify an administrative username and 
                password for Customer's Company account. Company reserves the right to refuse registration of or cancel 
                passwords it deems inappropriate.
                """
                story.append(Paragraph(terms_text, styles['Normal']))
                
                # PAGE BREAK
                story.append(PageBreak())
                
                # PAGE 3: SIGNATURE CERTIFICATE
                story.append(Paragraph("Signature Certificate", ParagraphStyle('CertificateTitle', parent=styles['Heading1'], fontSize=24, alignment=1, textColor=colors.HexColor('#1a73e8'))))
                story.append(Paragraph(f"Reference number: {datetime.now().strftime('%Y%m%d%H%M%S')}", ParagraphStyle('Reference', parent=styles['Normal'], fontSize=10, alignment=1)))
                story.append(Spacer(1, 20))
                
                # Document info
                doc_info = f"""
                <b>Document:</b> {company_name} Purchase Agreement for {client_company}<br/>
                <b>Company:</b> {company_name}<br/>
                <b>Client:</b> {client_company}<br/>
                <b>Service:</b> {service_type}<br/>
                <b>Amount:</b> ${total_price:.2f}
                """
                story.append(Paragraph(doc_info, styles['Normal']))
                story.append(Spacer(1, 20))
                
                # Certificate table
                cert_data = [
                    ['Signer', 'Timestamp', 'Signature'],
                    [f"<b>{ceo_signature.get('name', 'Adi Nandyala')}</b><br/>{ceo_signature.get('email', 'adi.nandyala@cloudfuze.com')}<br/><br/><b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
                     f"<b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {ceo_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
                     f"✓ Digital Signature<br/>{ceo_signature.get('data', '')}"],
                    [f"<b>{client_signature.get('name', client_name)}</b><br/>{client_signature.get('email', 'client@company.com')}<br/><br/><b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
                     f"<b>Sent:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Viewed:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><b>Signed:</b> {client_signature.get('date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S UTC'))}<br/><br/><b>Recipient Verification:</b><br/>✓ Email verified<br/>{datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/><br/><b>IP address:</b> 127.0.0.1<br/><b>Location:</b> N/A",
                     f"✓ Digital Signature<br/>{client_signature.get('data', '')}"]
                ]
                
                cert_table = Table(cert_data, colWidths=[2.5*inch, 2*inch, 2*inch])
                cert_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                story.append(cert_table)
                story.append(Spacer(1, 20))
                
                # Completion info
                completion_text = f"Document completed by all parties on: {datetime.now().strftime('%d %b %Y %H:%M:%S UTC')}<br/>Page 1 of 1"
                story.append(Paragraph(completion_text, styles['Normal']))
                
                # Build PDF
                doc.build(story)
                pdf_bytes = buffer.getvalue()
                buffer.close()
                
                print("✅ PDF generated successfully using ReportLab fallback")
            
            # Save PDF to documents directory using file handler
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"agreement_{client_name.replace(' ', '_')}_{timestamp}.pdf"
            
            # Use file handler to get correct path
            file_handler.ensure_documents_directory()
            file_path = file_handler.get_document_path(filename)
            
            # Save PDF file
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Store agreement metadata in MongoDB
            agreement_metadata = {
                'quote_id': f'template_{timestamp}',
                'filename': filename,
                'file_path': file_path,
                'client_name': client_name,
                'company_name': client_company,
                'service_type': service_type,
                'file_size': len(pdf_bytes),
                'template_data': data,  # Store the original template data
                'signatures': {
                    'ceo': ceo_signature,
                    'client': client_signature
                }
            }
            
            try:
                generated_agreements.store_agreement_metadata(agreement_metadata)
                print(f"✅ Agreement metadata stored: {filename}")
            except Exception as e:
                print(f"Warning: Failed to store agreement metadata: {e}")
            
            # Check if this is a signature workflow request (expects JSON response)
            # Look for signature workflow parameter in the request data
            print(f"🔍 DEBUG: signature_workflow = {data.get('signature_workflow')}")
            print(f"🔍 DEBUG: X-Signature-Workflow header = {request.headers.get('X-Signature-Workflow')}")
            if data.get('signature_workflow') == True or request.headers.get('X-Signature-Workflow') == 'true':
                # Return JSON response for signature workflow
                return jsonify({
                    'success': True,
                    'agreement_id': f'template_{timestamp}',
                    'filename': filename,
                    'message': 'Agreement generated successfully'
                })
            else:
                # Return the PDF file directly for download
                buffer = BytesIO(pdf_bytes)
                buffer.seek(0)
                
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )
            
        except ImportError as import_error:
            print(f"Import error: {import_error}")
            return jsonify({
                'success': False, 
                'message': 'PDF generation not available. Neither WeasyPrint nor ReportLab are installed.'
            }), 500
        except Exception as e:
            print(f"PDF generation error: {str(e)}")
            return jsonify({'success': False, 'message': f'PDF generation error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Template PDF generation error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sign-agreement/<agreement_id>')
def client_signature_page(agreement_id):
    """Serve the client signature page"""
    return render_template_string(open('approval_workflow/client-signature.html', 'r', encoding='utf-8').read())

@app.route('/sign-ceo/<agreement_id>')
def ceo_signature_page(agreement_id):
    """Serve the CEO signature page"""
    return render_template_string(open('approval_workflow/ceo-signature.html', 'r', encoding='utf-8').read())

@app.route('/api/agreements/download/<agreement_id>')
def download_agreement_pdf(agreement_id):
    """Download agreement PDF by ID"""
    try:
        # Find the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Get the file path
        file_path = agreement.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'PDF file not found'
            }), 404
        
        # Return the PDF file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=agreement.get('filename', f'agreement_{agreement_id}.pdf'),
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error downloading agreement PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error downloading PDF: {str(e)}'
        }), 500

@app.route('/api/agreements/sign/<agreement_id>', methods=['GET'])
def get_agreement_for_signing(agreement_id):
    """Get agreement data for client signing"""
    try:
        # Try to find agreement by ID
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Check if agreement is in a valid state for signing
        agreement_status = agreement.get('status', 'draft')
        if agreement_status in ['completed', 'cancelled']:
            return jsonify({
                'success': False,
                'message': f'Agreement is already {agreement_status} and cannot be signed'
            }), 400
        
        # Return agreement data (without sensitive info)
        agreement_data = {
            '_id': str(agreement['_id']),
            'company_name': agreement.get('company_name', 'CloudFuze'),
            'client_company': agreement.get('client_company', agreement.get('company_name', 'Client Company')),
            'client_name': agreement.get('client_name', 'Client'),
            'client_email': agreement.get('client_email', ''),
            'service_type': agreement.get('service_type', 'Migration Service'),
            'service_description': agreement.get('service_description', 'Service description'),
            'total_price': agreement.get('total_price', 0),
            'currency': agreement.get('currency', 'USD'),
            'start_date': agreement.get('start_date', ''),
            'end_date': agreement.get('end_date', ''),
            'status': agreement.get('status', 'draft'),
            'signatures': agreement.get('signatures', {}),
            'created_at': agreement.get('created_at', '').isoformat() if agreement.get('created_at') else '',
        }
        
        # Add template data if available
        if agreement.get('template_data'):
            template_data = agreement['template_data']
            agreement_data.update({
                'company_name': template_data.get('companyName', agreement_data['company_name']),
                'company_address': template_data.get('companyAddress', ''),
                'client_company': template_data.get('clientCompany', agreement_data['client_company']),
                'client_name': template_data.get('clientName', agreement_data['client_name']),
                'service_type': template_data.get('serviceType', agreement_data['service_type']),
                'service_description': template_data.get('serviceDescription', agreement_data['service_description']),
                'total_price': template_data.get('totalPrice', agreement_data['total_price']),
                'currency': template_data.get('currency', agreement_data['currency']),
                'start_date': template_data.get('startDate', agreement_data['start_date']),
                'end_date': template_data.get('endDate', agreement_data['end_date']),
            })
        
        return jsonify({
            'success': True,
            'agreement': agreement_data
        }), 200
        
    except Exception as e:
        print(f"Error getting agreement for signing: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading agreement: {str(e)}'
        }), 500

@app.route('/api/agreements/submit-signature/<agreement_id>', methods=['POST'])
def submit_client_signature(agreement_id):
    """Submit client signature for agreement"""
    try:
        data = request.get_json()
        
        # Get the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Check if already signed
        signatures = agreement.get('signatures', {})
        if signatures.get('client', {}).get('data'):
            return jsonify({
                'success': False,
                'message': 'Agreement has already been signed by client'
            }), 400
        
        # Validate signature data
        signature_info = data.get('signature', {})
        if not signature_info.get('data'):
            return jsonify({
                'success': False,
                'message': 'Signature data is required'
            }), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        date = data.get('date', '').strip()
        
        if not name or not email or not date:
            return jsonify({
                'success': False,
                'message': 'Name, email, and date are required'
            }), 400
        
        # Create client signature data
        client_signature = {
            'type': signature_info.get('type', 'text'),
            'data': signature_info.get('data'),
            'name': name,
            'title': data.get('title', '').strip(),
            'email': email,
            'date': date,
            'timestamp': datetime.now().isoformat(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Update signatures in agreement
        if 'signatures' not in agreement:
            agreement['signatures'] = {}
        agreement['signatures']['client'] = client_signature
        signatures = agreement['signatures']
        
        # Update agreement status
        agreement_status = 'client_signed'
        if signatures.get('ceo', {}).get('data'):
            agreement_status = 'completed'
        
        # Update the agreement in MongoDB
        try:
            from bson import ObjectId
            
            update_data = {
                'signatures': signatures,
                'status': agreement_status,
                'client_signed_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # If both signatures are complete, mark as completed and generate certificate
            if agreement_status == 'completed':
                update_data['completed_at'] = datetime.now()
            
                # Automatically generate signature certificate when both parties sign
                try:
                    print(f"🎉 Both parties have signed! Generating signature certificate for agreement: {agreement_id}")
                    generate_automatic_signature_certificate(agreement_id, agreement, signatures)
                except Exception as e:
                    print(f"Warning: Failed to generate automatic signature certificate: {e}")
            
            # Update using the same logic as get_agreement_by_id
            if ObjectId.is_valid(agreement_id):
                result = generated_agreements.collection.update_one(
                    {'_id': ObjectId(agreement_id)},
                    {'$set': update_data}
                )
            else:
                result = generated_agreements.collection.update_one(
                    {'quote_id': agreement_id},
                    {'$set': update_data}
                )
            
            if result.modified_count == 0:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update agreement'
                }), 500
            
            print(f"✅ Client signature added to agreement: {agreement_id}")
            
            # Send notification emails (optional - implement if needed)
            try:
                send_signature_notification(agreement, client_signature)
            except Exception as e:
                print(f"Warning: Failed to send notification email: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Signature submitted successfully',
                'status': agreement_status
            }), 200
            
        except Exception as e:
            print(f"Database update error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to save signature'
            }), 500
        
    except Exception as e:
        print(f"Error submitting client signature: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error submitting signature: {str(e)}'
        }), 500

@app.route('/api/agreements/submit-ceo-signature/<agreement_id>', methods=['POST'])
def submit_ceo_signature(agreement_id):
    """Submit CEO signature for agreement"""
    try:
        data = request.get_json()
        
        # Get the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Check if already signed by CEO
        signatures = agreement.get('signatures', {})
        if signatures.get('ceo', {}).get('data'):
            return jsonify({
                'success': False,
                'message': 'Agreement has already been signed by CEO'
            }), 400
        
        # Validate signature data
        signature_info = data.get('signature', {})
        if not signature_info.get('data'):
            return jsonify({
                'success': False,
                'message': 'Signature data is required'
            }), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        date = data.get('date', '').strip()
        
        if not name or not email or not date:
            return jsonify({
                'success': False,
                'message': 'Name, email, and date are required'
            }), 400
        
        # Create CEO signature data
        ceo_signature = {
            'type': signature_info.get('type', 'text'),
            'data': signature_info.get('data'),
            'name': name,
            'title': data.get('title', '').strip(),
            'email': email,
            'date': date,
            'timestamp': datetime.now().isoformat(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Update signatures in agreement
        if 'signatures' not in agreement:
            agreement['signatures'] = {}
        agreement['signatures']['ceo'] = ceo_signature
        signatures = agreement['signatures']
        
        # Update agreement status
        agreement_status = 'ceo_signed'
        if signatures.get('client', {}).get('data'):
            agreement_status = 'completed'
        
        # Update the agreement in MongoDB
        try:
            from bson import ObjectId
            
            update_data = {
                'signatures': signatures,
                'status': agreement_status,
                'ceo_signed_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # If both signatures are complete, mark as completed and generate certificate
            if agreement_status == 'completed':
                update_data['completed_at'] = datetime.now()
                
                # Automatically generate signature certificate when both parties sign
                try:
                    print(f"🎉 Both parties have signed! Generating signature certificate for agreement: {agreement_id}")
                    generate_automatic_signature_certificate(agreement_id, agreement, signatures)
                except Exception as e:
                    print(f"Warning: Failed to generate automatic signature certificate: {e}")
            
            # Update using the same logic as get_agreement_by_id
            if ObjectId.is_valid(agreement_id):
                result = generated_agreements.collection.update_one(
                    {'_id': ObjectId(agreement_id)},
                    {'$set': update_data}
                )
            else:
                result = generated_agreements.collection.update_one(
                    {'quote_id': agreement_id},
                    {'$set': update_data}
                )
            
            if result.modified_count == 0:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update agreement'
                }), 500
            
            print(f"✅ CEO signature added to agreement: {agreement_id}")
            
            return jsonify({
                'success': True,
                'message': 'CEO signature submitted successfully',
                'agreement_status': agreement_status
            })
            
        except Exception as e:
            print(f"Database update error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"Error submitting CEO signature: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error submitting signature: {str(e)}'
        }), 500

@app.route('/api/agreements/send-for-signature', methods=['POST'])
def send_agreement_for_signature():
    """Send agreement to client for signature"""
    try:
        data = request.get_json()
        agreement_id = data.get('agreement_id')
        client_email = data.get('client_email')
        client_name = data.get('client_name', 'Client')
        
        if not agreement_id or not client_email:
            return jsonify({
                'success': False,
                'message': 'Agreement ID and client email are required'
            }), 400
        
        # Get the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Update agreement status to 'pending_client_signature'
        try:
            from bson import ObjectId
            
            update_data = {
                'status': 'pending_client_signature',
                'client_email': client_email,
                'client_name': client_name,
                'signature_request_sent_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Update using the same logic as get_agreement_by_id
            if ObjectId.is_valid(agreement_id):
                result = generated_agreements.collection.update_one(
                    {'_id': ObjectId(agreement_id)},
                    {'$set': update_data}
                )
            else:
                result = generated_agreements.collection.update_one(
                    {'quote_id': agreement_id},
                    {'$set': update_data}
                )
            
            if result.modified_count == 0:
                print(f"Warning: Failed to update agreement status for {agreement_id}")
            
        except Exception as e:
            print(f"Warning: Failed to update agreement status: {e}")
        
        # Send signature request email
        try:
            send_signature_request_email(agreement_id, client_email, client_name, agreement)
            
            return jsonify({
                'success': True,
                'message': f'Signature request sent to {client_email}',
                'signature_url': f'/sign-agreement/{agreement_id}'
            }), 200
            
        except Exception as e:
            print(f"Error sending signature request email: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to send signature request: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"Error in send_agreement_for_signature: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending signature request: {str(e)}'
        }), 500

def send_signature_request_email(agreement_id, client_email, client_name, agreement):
    """Send signature request email to client"""
    try:
        email_service = EmailService()
        
        # Build signature URL
        base_url = request.host_url.rstrip('/')
        signature_url = f"{base_url}/sign-agreement/{agreement_id}"
        
        # Email subject and body
        company_name = agreement.get('company_name', 'CloudFuze')
        service_type = agreement.get('service_type', 'service')
        
        subject = f"Signature Required: Agreement from {company_name}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #1a73e8;">📋 Agreement Signature Request</h2>
                
                <p>Dear {client_name},</p>
                
                <p>You have received an agreement from <strong>{company_name}</strong> that requires your signature.</p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #333;">Agreement Details:</h3>
                    <ul style="margin: 10px 0;">
                        <li><strong>Service:</strong> {service_type}</li>
                        <li><strong>Company:</strong> {company_name}</li>
                        <li><strong>Total Amount:</strong> ${agreement.get('total_price', 0):.2f}</li>
                    </ul>
                </div>
                
                <p>To review and sign this agreement, please click the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{signature_url}" 
                       style="background: #1a73e8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        📝 Review & Sign Agreement
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">
                    <strong>Note:</strong> This signature request will remain valid for 30 days. 
                    If you have any questions about this agreement, please contact us directly.
                </p>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px; font-size: 12px; color: #666;">
                    <p>This email was sent by {company_name}. If you received this email by mistake, please ignore it.</p>
                    <p>Signature URL: <a href="{signature_url}">{signature_url}</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email
        email_service.send_email(
            recipient_email=client_email,
            subject=subject,
            body=body
        )
        
        print(f"✅ Signature request email sent to {client_email}")
        
    except Exception as e:
        print(f"❌ Failed to send signature request email: {str(e)}")
        raise

def send_signature_notification(agreement, client_signature):
    """Send notification when client signs agreement"""
    try:
        email_service = EmailService()
        
        # Get company/CEO email from agreement
        ceo_signature = agreement.get('signatures', {}).get('ceo', {})
        company_email = ceo_signature.get('email', 'admin@company.com')
        
        client_name = client_signature.get('name', 'Client')
        company_name = agreement.get('company_name', 'CloudFuze')
        
        subject = f"✅ Agreement Signed by {client_name}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">✅ Agreement Successfully Signed</h2>
                
                <p>Great news! The agreement has been signed by the client.</p>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">Signature Details:</h3>
                    <ul style="margin: 10px 0;">
                        <li><strong>Client Name:</strong> {client_name}</li>
                        <li><strong>Email:</strong> {client_signature.get('email', 'N/A')}</li>
                        <li><strong>Title:</strong> {client_signature.get('title', 'N/A')}</li>
                        <li><strong>Signed Date:</strong> {client_signature.get('date', 'N/A')}</li>
                        <li><strong>Timestamp:</strong> {client_signature.get('timestamp', 'N/A')}</li>
                    </ul>
                </div>
                
                <p>The agreement is now fully executed and both parties have provided their signatures.</p>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px; font-size: 12px; color: #666;">
                    <p>This notification was sent automatically by the {company_name} signature system.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send notification
        email_service.send_email(
            recipient_email=company_email,
            subject=subject,
            body=body
        )
        
        print(f"✅ Signature notification sent to {company_email}")
        
    except Exception as e:
        print(f"❌ Failed to send signature notification: {str(e)}")
        # Don't raise - this is not critical

@app.route('/api/agreements/generate-signature-certificate', methods=['POST'])
def generate_signature_certificate():
    """Generate a signature certificate PDF for a completed agreement"""
    try:
        data = request.get_json()
        agreement_id = data.get('agreement_id')
        
        if not agreement_id:
            return jsonify({
                'success': False,
                'message': 'Agreement ID is required'
            }), 400
        
        # Get the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        if not agreement:
            return jsonify({
                'success': False,
                'message': 'Agreement not found'
            }), 404
        
        # Check if agreement is completed (both signatures present)
        signatures = agreement.get('signatures', {})
        ceo_signature = signatures.get('ceo', {})
        client_signature = signatures.get('client', {})
        
        if not ceo_signature.get('data') or not client_signature.get('data'):
            return jsonify({
                'success': False,
                'message': 'Agreement must be fully signed by both parties to generate certificate'
            }), 400
        
        # Generate reference number
        import uuid
        reference_number = str(uuid.uuid4()).replace('-', '').upper()[:20]
        
        # Create certificate data
        certificate_data = {
            'agreement_id': agreement_id,
            'reference_number': reference_number,
            'document_title': f"{agreement.get('company_name', 'CloudFuze')} Purchase Agreement",
            'signers': [
                {
                    'name': ceo_signature.get('name', 'CEO'),
                    'email': ceo_signature.get('email', ''),
                    'role': 'Company Representative',
                    'signature_data': ceo_signature.get('data', ''),
                    'signature_type': 'drawn',
                    'signed_at': ceo_signature.get('timestamp', ''),
                    'ip_address': ceo_signature.get('ip_address', ''),
                    'location': ceo_signature.get('location', '')
                },
                {
                    'name': client_signature.get('name', 'Client'),
                    'email': client_signature.get('email', ''),
                    'role': 'Client',
                    'signature_data': client_signature.get('data', ''),
                    'signature_type': 'drawn',
                    'signed_at': client_signature.get('timestamp', ''),
                    'ip_address': client_signature.get('ip_address', ''),
                    'location': client_signature.get('location', '')
                }
            ],
            'completion_date': agreement.get('completed_at', datetime.now()),
            'certificate_data': {
                'company_name': agreement.get('company_name', 'CloudFuze'),
                'client_company': agreement.get('client_company', 'Client Company'),
                'service_type': agreement.get('service_type', 'Service'),
                'total_price': agreement.get('total_price', 0)
            }
        }
        
        # Generate the certificate PDF
        certificate_pdf_path = generate_signature_certificate_pdf(certificate_data)
        
        # Save certificate record
        certificate_data['file_path'] = certificate_pdf_path
        certificate_id = signature_certificate_collection.create_certificate(certificate_data)
        
        return jsonify({
            'success': True,
            'message': 'Signature certificate generated successfully',
            'certificate_id': certificate_id,
            'reference_number': reference_number
        }), 200
        
    except Exception as e:
        print(f"Error generating signature certificate: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating certificate: {str(e)}'
        }), 500

@app.route('/api/agreements/completed', methods=['GET'])
def get_completed_agreements():
    """Get all completed agreements (both signatures present)"""
    try:
        # Find agreements with both CEO and client signatures
        completed_agreements = list(generated_agreements.collection.find({
            "status": "completed",
            "signatures.ceo.data": {"$exists": True, "$ne": ""},
            "signatures.client.data": {"$exists": True, "$ne": ""}
        }).sort("completed_at", -1))
        
        # Convert ObjectId to string for JSON serialization
        for agreement in completed_agreements:
            agreement['_id'] = str(agreement['_id'])
        
        return jsonify({
            'success': True,
            'agreements': completed_agreements
        }), 200
        
    except Exception as e:
        print(f"Error getting completed agreements: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting completed agreements: {str(e)}'
        }), 500

@app.route('/api/agreements/certificate-status/<agreement_id>', methods=['GET'])
def get_certificate_status(agreement_id):
    """Check if a certificate was generated for an agreement"""
    try:
        certificate = signature_certificate_collection.get_certificate_by_agreement(agreement_id)
        
        if certificate:
            return jsonify({
                'success': True,
                'has_certificate': True,
                'certificate_id': certificate['_id'],
                'reference_number': certificate['reference_number'],
                'created_at': certificate['created_at']
            }), 200
        else:
            return jsonify({
                'success': True,
                'has_certificate': False
            }), 200
        
    except Exception as e:
        print(f"Error checking certificate status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error checking certificate status: {str(e)}'
        }), 500

@app.route('/api/agreements/certificates', methods=['GET'])
def get_all_certificates():
    """Get all generated signature certificates"""
    try:
        certificates = signature_certificate_collection.get_all_certificates()
        
        return jsonify({
            'success': True,
            'certificates': certificates
        }), 200
        
    except Exception as e:
        print(f"Error getting certificates: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting certificates: {str(e)}'
        }), 500

@app.route('/api/agreements/download-certificate/<certificate_id>')
def download_signature_certificate(certificate_id):
    """Download signature certificate PDF"""
    try:
        certificate = signature_certificate_collection.get_certificate_by_id(certificate_id)
        if not certificate:
            return jsonify({
                'success': False,
                'message': 'Certificate not found'
            }), 404
        
        file_path = certificate.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'Certificate file not found'
            }), 404
        
        return send_file(file_path, as_attachment=True, download_name=f"signature_certificate_{certificate.get('reference_number', certificate_id)}.pdf")
        
    except Exception as e:
        print(f"Error downloading certificate: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error downloading certificate: {str(e)}'
        }), 500

def generate_automatic_signature_certificate(agreement_id, agreement, signatures):
    """Automatically generate signature certificate when both parties sign"""
    try:
        # Generate reference number
        import uuid
        reference_number = str(uuid.uuid4()).replace('-', '').upper()[:20]
        
        # Get signature data
        ceo_signature = signatures.get('ceo', {})
        client_signature = signatures.get('client', {})
        
        # Create certificate data
        certificate_data = {
            'agreement_id': agreement_id,
            'reference_number': reference_number,
            'document_title': f"{agreement.get('company_name', 'CloudFuze')} Purchase Agreement",
            'signers': [
                {
                    'name': ceo_signature.get('name', 'CEO'),
                    'email': ceo_signature.get('email', ''),
                    'role': 'Company Representative',
                    'signature_data': ceo_signature.get('data', ''),
                    'signature_type': 'drawn',
                    'signed_at': ceo_signature.get('timestamp', ''),
                    'ip_address': ceo_signature.get('ip_address', ''),
                    'location': ceo_signature.get('location', '')
                },
                {
                    'name': client_signature.get('name', 'Client'),
                    'email': client_signature.get('email', ''),
                    'role': 'Client',
                    'signature_data': client_signature.get('data', ''),
                    'signature_type': 'drawn',
                    'signed_at': client_signature.get('timestamp', ''),
                    'ip_address': client_signature.get('ip_address', ''),
                    'location': client_signature.get('location', '')
                }
            ],
            'completion_date': datetime.now(),
            'certificate_data': {
                'company_name': agreement.get('company_name', 'CloudFuze'),
                'client_company': agreement.get('client_company', 'Client Company'),
                'service_type': agreement.get('service_type', 'Service'),
                'total_price': agreement.get('total_price', 0)
            }
        }
        
        # Generate the certificate PDF
        certificate_pdf_path = generate_signature_certificate_pdf(certificate_data)
        
        # Save certificate record
        certificate_data['file_path'] = certificate_pdf_path
        certificate_id = signature_certificate_collection.create_certificate(certificate_data)
        
        print(f"✅ Automatic signature certificate generated: {certificate_id}")
        print(f"📄 Certificate file: {certificate_pdf_path}")
        
        return certificate_id
        
    except Exception as e:
        print(f"❌ Error generating automatic signature certificate: {str(e)}")
        raise

def generate_signature_certificate_pdf(certificate_data):
    """Generate signature certificate PDF using ReportLab"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import base64
        import io
        
        # Create PDF file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signature_certificate_{certificate_data['reference_number']}_{timestamp}.pdf"
        file_path = os.path.join('documents', filename)
        
        # Ensure documents directory exists
        os.makedirs('documents', exist_ok=True)
        
        # Create PDF document with custom styling
        doc = SimpleDocTemplate(file_path, pagesize=letter, 
                              topMargin=72, bottomMargin=72, 
                              leftMargin=72, rightMargin=72)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Title style - matches your image
        title_style = ParagraphStyle(
            'SignatureCertificateTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        )
        
        # Reference number style
        ref_style = ParagraphStyle(
            'ReferenceNumber',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        # Document info style
        doc_info_style = ParagraphStyle(
            'DocumentInfo',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        # Add title - matches your image format
        story.append(Paragraph("Signature Certificate", title_style))
        story.append(Spacer(1, 15))
        
        # Add reference number - matches your image format
        story.append(Paragraph(f"Reference number: {certificate_data['reference_number']}", ref_style))
        story.append(Spacer(1, 25))
        
        # Create signers table - matches your image format exactly
        table_data = [['Signer', 'Timestamp', 'Signature']]
        
        for signer in certificate_data['signers']:
            # Format timestamps to match your image
            current_time = datetime.now().strftime('%d %b %Y %H:%M:%S UTC')
            sent_time = current_time
            viewed_time = current_time
            signed_time = signer['signed_at'] if signer['signed_at'] else current_time
            
            # Create signer info - matches your image format
            signer_info = f"""
            <b>{signer['name']}</b><br/>
            {signer['email']}<br/><br/>
            <b>Sent:</b> {sent_time}<br/>
            <b>Viewed:</b> {viewed_time}<br/>
            <b>Signed:</b> {signed_time}<br/><br/>
            <b>Recipient Verification:</b><br/>
            ✓ Email verified
            """
            
            # Create timestamp info - matches your image format
            timestamp_info = f"""
            <b>Sent:</b> {sent_time}<br/>
            <b>Viewed:</b> {viewed_time}<br/>
            <b>Signed:</b> {signed_time}<br/><br/>
            <b>Recipient Verification:</b><br/>
            ✓ Email verified<br/>
            {viewed_time}<br/><br/>
            <b>IP address:</b> {signer['ip_address'] or 'N/A'}<br/>
            <b>Location:</b> {signer['location'] or 'N/A'}
            """
            
            # Create signature display - matches your image format
            signature_display = f"""
            ✓ Digital Signature<br/>
            {signer['signature_data'] or signer['name']}
            """
            
            table_data.append([
                signer_info,
                timestamp_info,
                signature_display
            ])
        
        # Create table with 3 columns to match your image
        # Convert HTML content to Paragraph objects for proper rendering
        formatted_table_data = []
        for row_idx, row in enumerate(table_data):
            formatted_row = []
            for col_idx, cell_content in enumerate(row):
                if row_idx == 0:  # Header row
                    formatted_row.append(cell_content)
                else:  # Data rows
                    if isinstance(cell_content, str) and '<' in cell_content:
                        # Convert HTML to Paragraph
                        formatted_row.append(Paragraph(cell_content, styles['Normal']))
                    else:
                        formatted_row.append(cell_content)
            formatted_table_data.append(formatted_row)
        
        table = Table(formatted_table_data, colWidths=[2.5*inch, 2.0*inch, 2.0*inch])
        table.setStyle(TableStyle([
            # Header styling - matches your image
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data row styling - matches your image
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            
            # Alignment and spacing - matches your image
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Borders - matches your image
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Add completion info - matches your image format
        completion_date = certificate_data.get('completion_date', datetime.now())
        if isinstance(completion_date, str):
            try:
                completion_date = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
            except:
                completion_date = datetime.now()
        
        # Create completion section - matches your image format
        completion_style = ParagraphStyle(
            'Completion',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        completion_text = f"""
        <b>Document completed by all parties on:</b> {completion_date.strftime('%d %b %Y %H:%M:%S UTC')}<br/>
        Page 1 of 1
        """
        story.append(Paragraph(completion_text, completion_style))
        
        # Build PDF
        doc.build(story)
        
        print(f"✅ Signature certificate generated: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"Error generating signature certificate PDF: {str(e)}")
        raise

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
                # Try to attach latest signature images if available
                try:
                    client_email = template_data.get('client_email')
                    if client_email:
                        sig = signatures.get_latest_signature('client', client_email)
                        if sig and sig.get('signature_data'):
                            template_data['client_signature'] = sig['signature_data']
                except Exception:
                    pass
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
                'termination_notice': '30 days written notice',
                
            }

        return jsonify({'success': True, 'fields': sorted(list(template_data.keys())), 'template_data': template_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching fields: {str(e)}'}), 500


# Google Docs integration endpoints
@app.route('/api/gdocs/upsert', methods=['POST'])
def gdocs_upsert():
    """Create/update a Google Doc from HTML template content and placeholders.

    Request JSON: { title, template_content, placeholders }
    Returns: { success, document_id }
    """
    try:
        data = request.get_json() or {}
        title = data.get('title') or 'CPQ Template'
        html = data.get('template_content') or ''
        placeholders = data.get('placeholders') or {}
        doc_id = upsert_doc_from_template(title, html, placeholders)
        return jsonify({'success': True, 'document_id': doc_id})
    except Exception as e:
        import traceback
        # Improve HttpError visibility
        if isinstance(e, GHttpError):
            try:
                status = getattr(e, 'status_code', None) or getattr(e, 'resp', {}).status
            except Exception:
                status = ''
            reason = ''
            try:
                reason = e._get_reason()
            except Exception:
                reason = str(e)
            err = f"HttpError {status}: {reason}"
        else:
            err = f"{e.__class__.__name__}: {str(e)}"
        print('Google Docs upsert error:', err)
        traceback.print_exc()
        return jsonify({'success': False, 'message': err}), 500

@app.route('/api/gdocs/export-pdf', methods=['POST'])
def gdocs_export_pdf():
    """Export a Google Doc as PDF and return binary response."""
    try:
        data = request.get_json() or {}
        document_id = data.get('document_id')
        if not document_id:
            return jsonify({'success': False, 'message': 'document_id is required'}), 400
        pdf_bytes = export_doc_as_pdf(document_id)
        from flask import send_file
        from io import BytesIO
        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'{document_id}.pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Document Storage and Retrieval API Endpoints
@app.route('/api/documents/stored', methods=['GET'])
def get_stored_documents():
    """Get all stored documents (PDFs and Agreements)"""
    try:
        print("🔍 Debug: Starting get_stored_documents...")
        
        # Get all PDFs and agreements
        all_pdfs = generated_pdfs.get_all_pdfs(limit=100)
        print(f"🔍 Debug: Found {len(all_pdfs)} PDFs")
        
        all_agreements = generated_agreements.get_all_agreements(limit=100)
        print(f"🔍 Debug: Found {len(all_agreements)} agreements")
        
        # Combine and format documents
        documents = []
        
        # Add PDFs
        for pdf in all_pdfs:
            documents.append({
                'id': str(pdf['_id']),
                'document_type': 'PDF',
                'filename': pdf.get('filename', 'Unknown'),
                'client_name': pdf.get('client_name', 'Unknown'),
                'company_name': pdf.get('company_name', 'Unknown'),
                'generated_at': pdf.get('generated_at', datetime.now()),
                'quote_id': pdf.get('quote_id', 'Unknown'),
                'file_path': pdf.get('file_path', 'Unknown')
            })
        
        # Add Agreements
        for agreement in all_agreements:
            documents.append({
                'id': str(agreement['_id']),
                'document_type': 'Agreement',
                'filename': agreement.get('filename', 'Unknown'),
                'client_name': agreement.get('client_name', 'Unknown'),
                'company_name': agreement.get('company_name', 'Unknown'),
                'generated_at': agreement.get('generated_at', datetime.now()),
                'quote_id': agreement.get('quote_id', 'Unknown'),
                'file_path': agreement.get('file_path', 'Unknown')
            })
        
        print(f"🔍 Debug: Total documents: {len(documents)}")
        
        # Sort by generation date (newest first)
        documents.sort(key=lambda x: x['generated_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
        
    except Exception as e:
        print(f"❌ Debug: Error in get_stored_documents: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/documents/download/<document_id>', methods=['GET'])
def download_document(document_id):
    """Download a specific document by ID"""
    try:
        # Try to find in PDFs first
        pdf = generated_pdfs.get_pdf_by_id(document_id)
        if pdf:
            file_path = pdf.get('file_path')
            if file_path:
                filename = os.path.basename(file_path)
                correct_path = file_handler.get_document_path(filename)
                
                if file_handler.file_exists(filename):
                    return send_file(correct_path, as_attachment=True, download_name=pdf.get('filename', 'document.pdf'))
                else:
                    return jsonify({'success': False, 'message': f'PDF file not found: {filename}'}), 404
        
        # Try to find in agreements
        agreement = generated_agreements.get_agreement_by_id(document_id)
        if agreement:
            file_path = agreement.get('file_path')
            if file_path:
                filename = os.path.basename(file_path)
                correct_path = file_handler.get_document_path(filename)
                
                if file_handler.file_exists(filename):
                    return send_file(correct_path, as_attachment=True, download_name=agreement.get('filename', 'document.pdf'))
                else:
                    return jsonify({'success': False, 'message': f'Agreement file not found: {filename}'}), 404
        
        return jsonify({'success': False, 'message': 'Document not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/documents/preview/<document_id>', methods=['GET'])
def preview_document(document_id):
    """Preview a specific document by ID (for managers to view before approval)"""
    try:
        print(f"🔍 Preview request for document ID: {document_id}")
        
        # Try to find in PDFs first
        pdf = generated_pdfs.get_pdf_by_id(document_id)
        if pdf:
            print(f"✅ Found PDF: {pdf.get('filename', 'Unknown')}")
            file_path = pdf.get('file_path')
            
            # Use the new file path handler for consistent path resolution
            if file_path:
                # Get the filename from the stored path
                filename = os.path.basename(file_path)
                
                # Use the file handler to get the correct path
                correct_path = file_handler.get_document_path(filename)
                
                if file_handler.file_exists(filename):
                    print(f"✅ PDF file found using file handler: {correct_path}")
                    return send_file(correct_path, mimetype='application/pdf')
                else:
                    print(f"⚠️ PDF file not found: {filename}")
                    print(f"🔍 Documents directory: {file_handler.documents_dir}")
                    print(f"🔍 Available files: {file_handler.list_documents()}")
                    
                    # Return helpful error with file handler info
                    return jsonify({
                        'success': False, 
                        'message': f'PDF file not found: {filename}',
                        'debug_info': {
                            'filename': filename,
                            'original_path': file_path,
                            'documents_directory': file_handler.documents_dir,
                            'available_files': file_handler.list_documents(),
                            'current_working_dir': os.getcwd(),
                            'project_root': file_handler.project_root
                        }
                    }), 404
            else:
                print(f"❌ No file path stored for PDF")
                return jsonify({'success': False, 'message': 'No file path stored for this PDF'}), 404
        
        # Try to find in agreements
        agreement = generated_agreements.get_agreement_by_id(document_id)
        if agreement:
            print(f"✅ Found Agreement: {agreement.get('filename', 'Unknown')}")
            file_path = agreement.get('file_path')
            
            # Use the new file path handler for consistent path resolution
            if file_path:
                # Get the filename from the stored path
                filename = os.path.basename(file_path)
                
                # Use the file handler to get the correct path
                correct_path = file_handler.get_document_path(filename)
                
                if file_handler.file_exists(filename):
                    print(f"✅ Agreement file found using file handler: {correct_path}")
                    
                    # Check file extension to determine how to serve it
                    file_extension = os.path.splitext(filename)[1].lower()
                    
                    if file_extension == '.pdf':
                        # If it's actually a PDF, serve as PDF
                        return send_file(correct_path, mimetype='application/pdf')
                    elif file_extension == '.txt':
                        # If it's a text file, read and format it for browser display
                        try:
                            with open(correct_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Create a formatted HTML page for text content
                            html_content = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Agreement Preview - {agreement.get('filename', 'Document')}</title>
                                <style>
                                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                                    .header {{ border-bottom: 2px solid #667eea; padding-bottom: 20px; margin-bottom: 30px; }}
                                    .content {{ white-space: pre-wrap; font-size: 14px; }}
                                    .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
                                    .document-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                                    .document-info strong {{ color: #667eea; }}
                                </style>
                            </head>
                            <body>
                                <div class="header">
                                    <h1>📋 Agreement Preview</h1>
                                    <div class="document-info">
                                        <strong>Filename:</strong> {agreement.get('filename', 'N/A')}<br>
                                        <strong>Client:</strong> {agreement.get('client_name', 'N/A')}<br>
                                        <strong>Company:</strong> {agreement.get('company_name', 'N/A')}<br>
                                        <strong>Service Type:</strong> {agreement.get('service_type', 'N/A')}<br>
                                        <strong>Generated:</strong> {agreement.get('generated_at', 'N/A')}
                                    </div>
                                </div>
                                <div class="content">{content}</div>
                                <div class="footer">
                                    <p>This is a text-based agreement document. For PDF version, please contact the system administrator.</p>
                                </div>
                            </body>
                            </html>
                            """
                            
                            return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
                            
                        except Exception as read_error:
                            print(f"❌ Error reading agreement file: {read_error}")
                            return jsonify({'success': False, 'message': f'Error reading agreement file: {str(read_error)}'}), 500
                    else:
                        # For other file types, try to serve as-is
                        return send_file(correct_path)
                else:
                    # If no file found, return error with file handler info
                    print(f"⚠️ Agreement file not found: {filename}")
                    print(f"🔍 Documents directory: {file_handler.documents_dir}")
                    print(f"🔍 Available files: {file_handler.list_documents()}")
                    
                    return jsonify({
                        'success': False, 
                        'message': f'Agreement file not found: {filename}',
                        'debug_info': {
                            'filename': filename,
                            'original_path': file_path,
                            'documents_directory': file_handler.documents_dir,
                            'available_files': file_handler.list_documents(),
                            'current_working_dir': os.getcwd(),
                            'project_root': file_handler.project_root
                        }
                    }), 404
            else:
                print(f"❌ No file path stored for agreement")
                return jsonify({'success': False, 'message': 'No file path stored for this agreement'}), 404
        
        # If we get here, document wasn't found in either collection
        print(f"❌ Document not found in any collection: {document_id}")
        
        # Try to get more information about what's stored
        try:
            # Check if it's a valid ObjectId
            from bson import ObjectId
            obj_id = ObjectId(document_id)
            print(f"✅ Document ID is valid ObjectId: {obj_id}")
            
            # Check what collections actually contain this ID
            pdf_check = list(generated_pdfs.collection.find({"_id": obj_id}))
            agreement_check = list(generated_agreements.collection.find({"_id": obj_id}))
            
            print(f"📊 PDF collection results: {len(pdf_check)} documents")
            print(f"📊 Agreement collection results: {len(agreement_check)} documents")
            
            if pdf_check:
                print(f"📄 PDF found: {pdf_check[0]}")
            if agreement_check:
                print(f"📋 Agreement found: {agreement_check[0]}")
                
        except Exception as obj_error:
            print(f"⚠️ Error checking ObjectId: {obj_error}")
        
        return jsonify({'success': False, 'message': 'Document not found in database'}), 404
        
    except Exception as e:
        print(f"❌ Error in preview_document: {str(e)}")
        return jsonify({'success': False, 'message': f'Error previewing document: {str(e)}'}), 500

@app.route('/api/debug/file-storage', methods=['GET'])
def debug_file_storage():
    """Debug endpoint to check file storage status in production"""
    try:
        debug_info = {
            'current_working_directory': os.getcwd(),
            'app_directory': os.path.dirname(__file__),
            'documents_folder_exists': os.path.exists('documents'),
            'documents_folder_path': os.path.abspath('documents') if os.path.exists('documents') else 'N/A',
            'documents_folder_contents': [],
            'environment': os.environ.get('RENDER', 'local'),
            'file_system_info': {
                'temp_dir': os.environ.get('TEMP', 'N/A'),
                'home_dir': os.environ.get('HOME', 'N/A'),
                'user_dir': os.environ.get('USERPROFILE', 'N/A')
            }
        }
        
        # Check documents folder contents if it exists
        if os.path.exists('documents'):
            try:
                debug_info['documents_folder_contents'] = os.listdir('documents')
            except Exception as list_error:
                debug_info['documents_folder_contents'] = f'Error listing contents: {str(list_error)}'
        
        # Check if we're running on Render
        if os.environ.get('RENDER'):
            debug_info['render_info'] = {
                'service_id': os.environ.get('RENDER_SERVICE_ID', 'N/A'),
                'service_name': os.environ.get('RENDER_SERVICE_NAME', 'N/A'),
                'environment': os.environ.get('RENDER_ENVIRONMENT', 'N/A')
            }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting debug info: {str(e)}'
        }), 500

@app.route('/api/debug/agreements', methods=['GET'])
def debug_agreements():
    """Debug endpoint to check agreement storage and files"""
    try:
        debug_info = {
            'agreements_in_database': [],
            'file_system_check': {},
            'current_working_directory': os.getcwd(),
            'app_directory': os.path.dirname(__file__),
            'documents_folder_exists': os.path.exists('documents'),
            'documents_folder_path': os.path.abspath('documents') if os.path.exists('documents') else 'N/A'
        }
        
        # Get all agreements from database
        try:
            all_agreements = generated_agreements.get_all_agreements(limit=50)
            debug_info['agreements_in_database'] = all_agreements
        except Exception as db_error:
            debug_info['database_error'] = str(db_error)
        
        # Check file system for agreement files
        if os.path.exists('documents'):
            try:
                doc_files = os.listdir('documents')
                agreement_files = [f for f in doc_files if f.endswith(('.txt', '.pdf'))]
                debug_info['file_system_check'] = {
                    'total_files': len(doc_files),
                    'agreement_files': agreement_files,
                    'agreement_files_count': len(agreement_files)
                }
            except Exception as fs_error:
                debug_info['file_system_error'] = str(fs_error)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting agreement debug info: {str(e)}'
        }), 500

@app.route('/api/email/send-with-attachments', methods=['POST'])
def send_email_with_attachments():
    """Send email with document attachments"""
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        service_type = data.get('service_type')
        requirements = data.get('requirements')
        document_ids = data.get('document_ids', [])
        
        if not recipient_email or not recipient_name:
            return jsonify({'success': False, 'message': 'Recipient email and name are required'}), 400
        
        # Get document details for attachments
        attachments = []
        for doc_id in document_ids:
            # Try PDFs first
            pdf = generated_pdfs.get_pdf_by_id(doc_id)
            if pdf and pdf.get('file_path') and os.path.exists(pdf.get('file_path')):
                attachments.append({
                    'filename': pdf.get('filename', 'document.pdf'),
                    'file_path': pdf.get('file_path')
                })
                continue
            
            # Try agreements
            agreement = generated_agreements.get_agreement_by_id(doc_id)
            if agreement and agreement.get('file_path') and os.path.exists(agreement.get('file_path')):
                attachments.append({
                    'filename': agreement.get('filename', 'document.pdf'),
                    'file_path': agreement.get('file_path')
                })
        
        # Send email with attachments using EmailService
        email_service = EmailService()
        
        # Create email subject and body
        subject = f"Documents for {company_name} - {service_type}"
        body = f"""
        <html>
        <body>
            <h2>Hello {recipient_name},</h2>
            <p>Please find attached the requested documents for {company_name}.</p>
            <p><strong>Service Type:</strong> {service_type}</p>
            <p><strong>Requirements:</strong> {requirements or 'Not specified'}</p>
            <p><strong>Attachments:</strong> {len(attachments)} document(s)</p>
            <br>
            <p>Best regards,<br>Your Team</p>
        </body>
        </html>
        """
        
        # Send email with attachments
        email_result = email_service.send_email_with_attachments(recipient_email, subject, body, attachments)
        
        if email_result['success']:
            return jsonify({
                'success': True,
                'message': f'Email sent successfully with {len(attachments)} attachment(s)',
                'attachments_count': len(attachments)
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send email: {email_result.get("message", "Unknown error")}'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/email/generate-and-send', methods=['POST'])
def generate_pdf_and_send_email():
    """Generate a PDF quote and send it via email with attachment"""
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name')
        company_name = data.get('company_name')
        service_type = data.get('service_type')
        requirements = data.get('requirements')
        
        if not recipient_email or not recipient_name or not company_name:
            return jsonify({'success': False, 'message': 'Recipient email, name, and company are required'}), 400
        
        print(f"🔍 Debug: Generating PDF and sending email to {recipient_email}")
        
        # Create sample quote data for PDF generation
        quote_data = {
            'basic': {'perUserCost': 30.0, 'totalUserCost': 1500.0, 'dataCost': 100.0, 'migrationCost': 300.0, 'instanceCost': 1000.0, 'totalCost': 2900.0},
            'standard': {'perUserCost': 35.0, 'totalUserCost': 1750.0, 'dataCost': 150.0, 'migrationCost': 300.0, 'instanceCost': 1000.0, 'totalCost': 3200.0},
            'advanced': {'perUserCost': 40.0, 'totalUserCost': 2000.0, 'dataCost': 180.0, 'migrationCost': 300.0, 'instanceCost': 1000.0, 'totalCost': 3480.0}
        }
        
        configuration = {
            'users': 50, 'instanceType': 'standard', 'instances': 2, 'duration': 6,
            'migrationType': 'content', 'dataSize': 100
        }
        
        # Generate PDF
        from templates.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.create_quote_pdf(
            {'name': recipient_name, 'company': company_name, 'email': recipient_email, 'phone': '', 'serviceType': service_type},
            quote_data,
            configuration
        )
        
        # Save PDF to documents directory
        import os
        from datetime import datetime
        
        os.makedirs('documents', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quote_{recipient_name.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join('documents', filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        print(f"✅ Debug: PDF generated and saved to {pdf_path}")
        print(f"✅ Debug: File size: {os.path.getsize(pdf_path)} bytes")
        
        # Store PDF metadata in MongoDB
        pdf_metadata = {
            'quote_id': f'auto_{timestamp}',
            'filename': filename,
            'file_path': pdf_path,
            'client_name': recipient_name,
            'company_name': company_name,
            'service_type': service_type,
            'generated_at': datetime.now()
        }
        
        generated_pdfs.store_pdf_metadata(pdf_metadata)
        print(f"✅ Debug: PDF metadata stored in MongoDB")
        
        # Send email with the generated PDF
        email_service = EmailService()
        
        subject = f"Quote for {company_name} - {service_type}"
        body = f"""
        <html>
        <body>
            <h2>Hello {recipient_name},</h2>
            <p>Thank you for your interest in our {service_type}.</p>
            <p>Please find attached your detailed quote for {company_name}.</p>
            <p><strong>Service Type:</strong> {service_type}</p>
            <p><strong>Requirements:</strong> {requirements or 'Not specified'}</p>
            <br>
            <p>We've prepared three service tiers to meet your needs:</p>
            <ul>
                <li><strong>Basic Plan:</strong> ${quote_data['basic']['totalCost']:,.2f}</li>
                <li><strong>Standard Plan:</strong> ${quote_data['standard']['totalCost']:,.2f}</li>
                <li><strong>Advanced Plan:</strong> ${quote_data['advanced']['totalCost']:,.2f}</li>
            </ul>
            <br>
            <p>Please review the attached quote and let us know if you have any questions.</p>
            <p>Best regards,<br>Your Migration Services Team</p>
        </body>
        </html>
        """
        
        # Create attachment list
        attachments = [{
            'filename': filename,
            'file_path': pdf_path
        }]
        
        print(f"🔍 Debug: Sending email with PDF attachment")
        email_result = email_service.send_quote_email(recipient_email, recipient_name, company_name, quote_data, pdf_path)
        
        if email_result['success']:
            return jsonify({
                'success': True,
                'message': f'PDF generated and email sent successfully to {recipient_email}',
                'pdf_path': pdf_path,
                'filename': filename
            })
        else:
            return jsonify({
                'success': False,
                'message': f'PDF generated but email failed: {email_result.get("message", "Unknown error")}',
                'pdf_path': pdf_path,
                'filename': filename
            })
        
    except Exception as e:
        print(f"❌ Debug: Error in generate_pdf_and_send_email: {str(e)}")
        import traceback
        print(f"❌ Debug: Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Approval Workflow API Endpoints
@app.route('/api/approval/stats', methods=['GET'])
def get_approval_stats():
    """Get approval workflow statistics"""
    try:
        stats = approval_workflows.get_workflow_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching approval stats: {str(e)}'
        }), 500

@app.route('/api/approval/pending', methods=['GET'])
def get_pending_approvals():
    """Get all pending approval workflows"""
    try:
        # Temporarily use the more inclusive method to debug
        # Ensure we are not serving a cached cursor
        workflows = approval_workflows.get_all_active_workflows(limit=100)
        
        # Format workflows for frontend
        formatted_workflows = []
        for workflow in workflows:
            formatted_workflow = {
                '_id': str(workflow['_id']),
                'document_id': workflow.get('document_id'),
                'document_name': workflow.get('document_name', 'N/A'),
                'client_name': workflow.get('client_name', 'N/A'),
                'company_name': workflow.get('company_name', 'N/A'),
                'document_type': workflow.get('document_type', 'N/A'),
                'current_stage': workflow.get('current_stage', 'N/A'),
                'status': workflow.get('workflow_status', 'pending'),
                'manager_status': workflow.get('manager_status', 'pending'),
                'manager_comments': workflow.get('manager_comments', ''),
                'ceo_status': workflow.get('ceo_status', 'pending'),
                'ceo_comments': workflow.get('ceo_comments', ''),
                'client_status': workflow.get('client_status', 'pending'),
                'client_comments': workflow.get('client_comments', ''),
                'created_at': workflow.get('created_at'),
                'can_approve': True  # This would be determined by user role
            }
            formatted_workflows.append(formatted_workflow)
        
        return jsonify({
            'success': True,
            'workflows': formatted_workflows
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching pending approvals: {str(e)}'
        }), 500

@app.route('/api/approval/my-queue', methods=['GET'])
def get_my_approval_queue():
    """Get approval queue for current user"""
    try:
        # Get role and email from request parameters
        user_role = request.args.get('role', 'manager')
        user_email = request.args.get('email', 'manager@company.com')
        
        print(f"🔍 API: Getting approval queue for role: {user_role}, email: {user_email}")
        
        workflows = approval_workflows.get_my_approval_queue(user_role, user_email, limit=100)
        
        # Format workflows for frontend
        formatted_workflows = []
        for workflow in workflows:
            formatted_workflow = {
                '_id': str(workflow['_id']),
                'document_id': workflow.get('document_id'),
                'document_name': workflow.get('document_name', 'N/A'),
                'client_name': workflow.get('client_name', 'N/A'),
                'company_name': workflow.get('company_name', 'N/A'),
                'document_type': workflow.get('document_type', 'N/A'),
                'created_at': workflow.get('created_at'),
                'priority': 'normal'  # This could be calculated based on urgency
            }
            formatted_workflows.append(formatted_workflow)
        
        return jsonify({
            'success': True,
            'workflows': formatted_workflows
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching approval queue: {str(e)}'
        }), 500

@app.route('/api/approval/workflow-status', methods=['GET'])
def get_workflow_status():
    """Get all active workflow statuses"""
    try:
        # Temporarily use the more inclusive method to debug
        # Ensure we are not serving a cached cursor
        workflows = approval_workflows.get_all_active_workflows(limit=100)
        
        # Format workflows for frontend
        formatted_workflows = []
        for workflow in workflows:
            # Debug: Print manager comments from database
            manager_comments = workflow.get('manager_comments', '')
            print(f"🔍 Workflow {workflow.get('_id')} - Manager comments from DB: '{manager_comments}'")
            
            formatted_workflow = {
                '_id': str(workflow['_id']),
                'document_id': workflow.get('document_id'),
                'document_name': workflow.get('document_name', 'N/A'),
                'document_type': workflow.get('document_type', 'N/A'),
                'client_name': workflow.get('client_name', 'N/A'),
                'company_name': workflow.get('company_name', 'N/A'),
                'current_stage': workflow.get('current_stage', 'manager'),
                'workflow_status': workflow.get('workflow_status', 'active'),
                'manager_status': workflow.get('manager_status', 'pending'),
                'manager_comments': manager_comments,
                'ceo_status': workflow.get('ceo_status', 'pending'),
                'ceo_comments': workflow.get('ceo_comments', ''),
                'client_status': workflow.get('client_status', 'pending'),
                'client_comments': workflow.get('client_comments', ''),
                'created_at': workflow.get('created_at')
            }
            formatted_workflows.append(formatted_workflow)
        
        return jsonify({
            'success': True,
            'workflows': formatted_workflows
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching workflow status: {str(e)}'
        }), 500

@app.route('/api/approval/history', methods=['GET'])
def get_approval_history():
    """Get approval history"""
    try:
        history = approval_workflows.get_approval_history(limit=100)
        
        # Format history for frontend
        formatted_history = []
        for item in history:
            formatted_item = {
                '_id': str(item['_id']),
                'document_id': item.get('document_id'),
                'document_name': item.get('document_name', 'N/A'),
                'client_name': item.get('client_name', 'N/A'),
                'company_name': item.get('company_name', 'N/A'),
                'document_type': item.get('document_type', 'N/A'),
                'final_status': item.get('final_status', 'completed'),
                'manager_decision': item.get('manager_status', 'N/A'),
                'ceo_decision': item.get('ceo_status', 'N/A'),
                'manager_comments': item.get('manager_comments', ''),
                'ceo_comments': item.get('ceo_comments', ''),
                # Include client feedback for history view
                'client_decision': item.get('client_decision') or item.get('client_status', 'N/A'),
                'client_comments': item.get('client_comments', ''),
                'completed_at': item.get('completed_at') or item.get('updated_at')
            }
            formatted_history.append(formatted_item)
        
        return jsonify({
            'success': True,
            'history': formatted_history
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching approval history: {str(e)}'
        }), 500

@app.route('/api/approval/comments', methods=['GET'])
def get_approval_comments():
    """Get approval comments for completed workflows"""
    try:
        comments = approval_workflows.get_approval_comments(limit=100)
        
        return jsonify({
            'success': True,
            'comments': comments
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching approval comments: {str(e)}'
        }), 500

@app.route('/api/approval/workflow/<workflow_id>', methods=['GET'])
def get_workflow_details(workflow_id):
    """Get specific workflow details"""
    try:
        workflow = approval_workflows.get_workflow_by_id(workflow_id)
        
        if not workflow:
            return jsonify({
                'success': False,
                'message': 'Workflow not found'
            }), 404
        
        # Format workflow for frontend
        formatted_workflow = {
            '_id': str(workflow['_id']),
            'document_id': workflow.get('document_id'),
            'document_name': workflow.get('document_name', 'N/A'),
            'client_name': workflow.get('client_name', 'N/A'),
            'company_name': workflow.get('company_name', 'N/A'),
            'document_type': workflow.get('document_type', 'N/A'),
            'manager_status': workflow.get('manager_status', 'pending'),
            'ceo_status': workflow.get('ceo_status', 'pending'),
            'client_status': workflow.get('client_status', 'pending'),
            'workflow_status': workflow.get('workflow_status', 'active'),
            'created_at': workflow.get('created_at'),
            'updated_at': workflow.get('updated_at')
        }
        
        return jsonify({
            'success': True,
            'workflow': formatted_workflow
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching workflow details: {str(e)}'
        }), 500

@app.route('/api/approval/approve', methods=['GET', 'POST'])
def approve_workflow():
    """Approve a workflow"""
    if request.method == 'GET':
        return jsonify({
            'success': False,
            'message': 'This endpoint only accepts POST requests. Please use the approval form.',
            'method': request.method,
            'endpoint': '/api/approval/approve'
        }), 405
    
    try:
        data = request.get_json()
        workflow_id = data.get('workflow_id')
        role = data.get('role')
        action = data.get('action')
        comments = data.get('comments', '')
        
        print(f"🔍 Approval request received: workflow_id={workflow_id}, role={role}, action={action}")
        
        if not all([workflow_id, role, action]):
            return jsonify({
                'success': False,
                'message': 'Workflow ID, role, and action are required'
            }), 400
        
        if action not in ['approve', 'deny']:
            return jsonify({
                'success': False,
                'message': 'Action must be either approve or deny'
            }), 500
        
        # Update workflow status
        success = approval_workflows.update_workflow_status(workflow_id, role, action, comments)
        
        if success:
            # Get updated workflow details
            workflow = approval_workflows.get_workflow_by_id(workflow_id)
            
            if workflow:
                try:
                    # If manager approves, send email to CEO
                    if role == 'manager' and action == 'approve':
                        ceo_email = workflow.get('ceo_email')
                        if ceo_email:
                            # Get PDF file path for attachment
                            pdf_path = None
                            document_type = workflow.get('document_type')
                            if document_type == 'PDF':
                                document = generated_pdfs.get_pdf_by_id(workflow.get('document_id'))
                                pdf_path = document.get('file_path') if document else None
                            elif document_type == 'Agreement':
                                document = generated_agreements.get_agreement_by_id(workflow.get('document_id'))
                                pdf_path = document.get('file_path') if document else None
                            
                            # Send approval email to CEO
                            email_service = EmailService()
                            email_result = email_service.send_approval_workflow_email(
                                recipient_email=ceo_email,
                                recipient_role='ceo',
                                workflow_data=workflow,
                                pdf_path=pdf_path
                            )
                            
                            if email_result['success']:
                                print(f"✅ Approval email sent to CEO: {ceo_email}")
                            else:
                                print(f"⚠️ Failed to send approval email to CEO: {email_result['message']}")
                    
                    # If CEO approves, send final document to client
                    elif role == 'ceo' and action == 'approve':
                        client_email = workflow.get('client_email')
                        if client_email:
                            # Send final approved document to client
                            email_service = EmailService()
                            
                            # Get PDF file path for attachment
                            pdf_path = None
                            document_type = workflow.get('document_type')
                            if document_type == 'PDF':
                                document = generated_pdfs.get_pdf_by_id(workflow.get('document_id'))
                                pdf_path = document.get('file_path') if document else None
                            elif document_type == 'Agreement':
                                document = generated_agreements.get_agreement_by_id(workflow.get('document_id'))
                                pdf_path = document.get('file_path') if document else None
                            
                            # Send final approved document to client
                            client_name = workflow.get('client_name', 'Valued Client')
                            company_name = workflow.get('company_name', 'Your Company')
                            
                            email_result = email_service.send_client_delivery_email(
                                client_email=client_email,
                                client_name=client_name,
                                company_name=company_name,
                                workflow_data=workflow,
                                pdf_path=pdf_path
                            )
                            
                            if email_result['success']:
                                print(f"✅ Final approved document sent to client: {client_email}")
                            else:
                                print(f"⚠️ Failed to send final document to client: {email_result['message']}")
                        else:
                            print(f"⚠️ No client email found in workflow for final delivery")
                    
                    # If anyone denies, notify initiator
                    elif action == 'deny':
                        print(f"⚠️ Workflow denied by {role}. Notifying initiator...")
                        
                except Exception as email_error:
                    print(f"⚠️ Error sending workflow notification email: {str(email_error)}")
                    # Continue with workflow update even if email fails
            
            return jsonify({
                'success': True,
                'message': f'Workflow {action}d successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update workflow status'
            }), 500
        
    except Exception as e:
        print(f"❌ Error in approve_workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error approving workflow: {str(e)}'
        }), 500

@app.route('/api/approval/deny', methods=['POST'])
def deny_workflow():
    """Deny a workflow"""
    try:
        data = request.get_json()
        workflow_id = data.get('workflow_id')
        role = data.get('role')
        action = data.get('action')
        comments = data.get('comments', '')
        
        if not all([workflow_id, role, action]):
            return jsonify({
                'success': False,
                'message': 'Workflow ID, role, and action are required'
            }), 400
        
        if action != 'deny':
            return jsonify({
                'success': False,
                'message': 'Action must be deny'
            }), 500
        
        # Update workflow status
        success = approval_workflows.update_workflow_status(workflow_id, role, action, comments)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow denied successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update workflow status'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error denying workflow: {str(e)}'
        }), 500

@app.route('/api/approval/denied', methods=['GET'])
def get_denied_workflows():
    """Get all denied workflows with comments"""
    try:
        # Get denied workflows from the database
        denied_workflows = approval_workflows.get_denied_workflows()
        
        if denied_workflows:
            # Format the data for frontend display
            formatted_workflows = []
            for workflow in denied_workflows:
                # Determine who denied it and when
                denied_by_role = 'Unknown'
                denied_at = None
                
                if workflow.get('client_status') == 'rejected':
                    denied_by_role = 'Client'
                    denied_at = workflow.get('client_updated_at')
                elif workflow.get('ceo_status') == 'denied':
                    denied_by_role = 'CEO'
                    denied_at = workflow.get('ceo_updated_at')
                elif workflow.get('manager_status') == 'denied':
                    denied_by_role = 'Manager'
                    denied_at = workflow.get('manager_updated_at')
                
                formatted_workflow = {
                    '_id': str(workflow.get('_id')),
                    'document_name': workflow.get('document_name', 'N/A'),
                    'document_type': workflow.get('document_type', 'Document'),
                    'client_name': workflow.get('client_name', 'N/A'),
                    'denied_by_role': denied_by_role,
                    'denied_by_email': workflow.get('denied_by_email', 'Unknown'),
                    'denied_at': denied_at,
                    'comments': workflow.get('comments', 'No comments provided'),
                    'workflow_id': str(workflow.get('_id')),
                    # Include all comments for proper display
                    'manager_comments': workflow.get('manager_comments', ''),
                    'ceo_comments': workflow.get('ceo_comments', ''),
                    'client_comments': workflow.get('client_comments', ''),
                    'manager_status': workflow.get('manager_status', 'pending'),
                    'ceo_status': workflow.get('ceo_status', 'pending'),
                    'client_status': workflow.get('client_status', 'pending')
                }
                formatted_workflows.append(formatted_workflow)
            
            return jsonify({
                'success': True,
                'denied_requests': formatted_workflows,
                'count': len(formatted_workflows)
            }), 200
        else:
            return jsonify({
                'success': True,
                'denied_requests': [],
                'count': 0
            }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving denied workflows: {str(e)}'
        }), 500

@app.route('/api/approval/start-workflow', methods=['POST'])
def start_approval_workflow():
    """Start a new approval workflow for a document"""
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        document_type = data.get('document_type', 'PDF')
        manager_email = data.get('manager_email')
        ceo_email = data.get('ceo_email')
        client_email = data.get('client_email')
        
        if not all([document_id, manager_email, ceo_email, client_email]):
            return jsonify({
                'success': False,
                'message': 'Document ID, manager email, CEO email, and client email are required'
            }), 400
        
        # Get document details
        document = None
        if document_type == 'PDF':
            document = generated_pdfs.get_pdf_by_id(document_id)
        elif document_type == 'Agreement':
            document = generated_agreements.get_agreement_by_id(document_id)
        
        if not document:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        # Create workflow data
        workflow_data = {
            'document_id': document_id,
            'document_type': document_type,
            'document_name': document.get('filename', 'Document'),
            'client_name': document.get('client_name', 'N/A'),
            'company_name': document.get('company_name', 'N/A'),
            'client_email': client_email,  # Use client email from form
            'manager_email': manager_email,
            'ceo_email': ceo_email,
            'current_stage': 'manager',
            'priority': 'normal'
        }
        
        # Create the workflow
        result = approval_workflows.create_workflow(workflow_data)
        
        if result.inserted_id:
            workflow_id = str(result.inserted_id)
            
            # Send approval email to manager
            try:
                # Get PDF file path for attachment
                pdf_path = None
                if document_type == 'PDF':
                    pdf_path = document.get('file_path') or document.get('pdf_path')
                elif document_type == 'Agreement':
                    pdf_path = document.get('file_path') or document.get('agreement_path')
                
                # Add workflow ID to data for email
                workflow_data['_id'] = workflow_id
                workflow_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Send email to manager
                email_service = EmailService()
                email_result = email_service.send_approval_workflow_email(
                    recipient_email=manager_email,
                    recipient_role='manager',
                    workflow_data=workflow_data,
                    pdf_path=pdf_path
                )
                
                if email_result['success']:
                    print(f"✅ Approval email sent to manager: {manager_email}")
                else:
                    print(f"⚠️ Failed to send approval email to manager: {email_result['message']}")
                    
            except Exception as email_error:
                print(f"⚠️ Error sending approval email: {str(email_error)}")
                # Continue with workflow creation even if email fails
            
            return jsonify({
                'success': True,
                'message': 'Approval workflow started successfully and notification sent to manager',
                'workflow_id': workflow_id
                }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create approval workflow'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting approval workflow: {str(e)}'
        }), 500

@app.route('/api/documents/list', methods=['GET'])
def list_documents_for_approval():
    """Get all documents for approval workflow selection"""
    try:
        # Get all PDFs and agreements
        all_pdfs = generated_pdfs.get_all_pdfs(limit=100)
        all_agreements = generated_agreements.get_all_agreements(limit=100)
        
        # Combine and format documents
        documents = []
        
        # Add PDFs
        for pdf in all_pdfs:
            documents.append({
                'id': str(pdf['_id']),
                'document_type': 'PDF',
                'filename': pdf.get('filename', 'Unknown'),
                'client_name': pdf.get('client_name', 'Unknown'),
                'company_name': pdf.get('company_name', 'Unknown'),
                'client_email': pdf.get('client_email', ''),
                'generated_at': pdf.get('generated_at', datetime.now()),
                'quote_id': pdf.get('quote_id', 'Unknown')
            })
        
        # Add Agreements
        for agreement in all_agreements:
            documents.append({
                'id': str(agreement['_id']),
                'document_type': 'Agreement',
                'filename': agreement.get('filename', 'Unknown'),
                'client_name': agreement.get('client_name', 'Unknown'),
                'company_name': agreement.get('company_name', 'Unknown'),
                'client_email': agreement.get('client_email', ''),
                'generated_at': agreement.get('generated_at', datetime.now()),
                'quote_id': agreement.get('quote_id', 'Unknown')
            })
        
        # Sort by generation date (newest first)
        documents.sort(key=lambda x: x['generated_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/approval/debug/<workflow_id>', methods=['GET'])
def debug_approval_workflow(workflow_id):
    """Debug endpoint to troubleshoot approval workflow issues"""
    try:
        print(f"🔍 Debug request for workflow ID: {workflow_id}")
        
        # Get the workflow
        workflow = approval_workflows.get_workflow_by_id(workflow_id)
        if not workflow:
            return jsonify({'success': False, 'message': 'Workflow not found'}), 404
        
        print(f"✅ Found workflow: {workflow}")
        
        # Get document details
        document_id = workflow.get('document_id')
        document_type = workflow.get('document_type')
        
        print(f"📄 Document ID: {document_id}")
        print(f"📋 Document Type: {document_type}")
        
        # Try to find the actual document
        document = None
        if document_type == 'PDF':
            document = generated_pdfs.get_pdf_by_id(document_id)
        elif document_type == 'Agreement':
            document = generated_agreements.get_agreement_by_id(document_id)
        
        # Check if document exists
        document_exists = document is not None
        file_exists = False
        file_path = None
        
        if document:
            file_path = document.get('file_path')
            file_exists = file_path and os.path.exists(file_path)
            print(f"✅ Document found in database: {document.get('filename', 'Unknown')}")
            print(f"📁 File path: {file_path}")
            print(f"📁 File exists: {file_exists}")
        else:
            print(f"❌ Document not found in database")
        
        # Return debug information
        debug_info = {
            'success': True,
            'workflow': {
                'id': str(workflow['_id']),
                'document_id': document_id,
                'document_type': document_type,
                'document_name': workflow.get('document_name'),
                'client_name': workflow.get('client_name'),
                'company_name': workflow.get('company_name'),
                'manager_email': workflow.get('manager_email'),
                'ceo_email': workflow.get('ceo_email'),
                'current_stage': workflow.get('current_stage'),
                'manager_status': workflow.get('manager_status'),
                'ceo_status': workflow.get('ceo_status'),
                'created_at': workflow.get('created_at'),
                'updated_at': workflow.get('updated_at')
            },
            'document': {
                'exists_in_database': document_exists,
                'filename': document.get('filename') if document else None,
                'file_path': file_path,
                'file_exists_on_disk': file_exists,
                'client_name': document.get('client_name') if document else None,
                'company_name': document.get('company_name') if document else None
            },
            'collections_info': {
                'pdf_collection_name': generated_pdfs.collection.name,
                'agreement_collection_name': generated_agreements.collection.name,
                'workflow_collection_name': approval_workflows.collection.name
            }
        }
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        print(f"❌ Error in debug endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Error debugging workflow: {str(e)}'}), 500

@app.route('/api/agreements/convert-to-pdf/<agreement_id>', methods=['POST'])
def convert_agreement_to_pdf(agreement_id):
    """Convert an existing text agreement to PDF format"""
    try:
        print(f"🔍 Converting agreement to PDF: {agreement_id}")
        
        # Get the agreement
        agreement = generated_agreements.get_agreement_by_id(agreement_id)
        if not agreement:
            return jsonify({'success': False, 'message': 'Agreement not found'}), 404
        
        file_path = agreement.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Agreement file not found'}), 404
        
        # Check if it's already a PDF
        if file_path.lower().endswith('.pdf'):
            return jsonify({'success': False, 'message': 'Agreement is already a PDF'}), 400
        
        try:
            from weasyprint import HTML
            
            # Read the text content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create HTML template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Agreement - {agreement.get('client_name', 'Client')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    .header {{ text-align: center; border-bottom: 2px solid #667eea; padding-bottom: 20px; margin-bottom: 30px; }}
                    .content {{ white-space: pre-wrap; font-size: 14px; }}
                    .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }}
                    .company-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .company-info strong {{ color: #667eea; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📋 Service Agreement</h1>
                    <div class="company-info">
                        <strong>Client:</strong> {agreement.get('client_name', 'N/A')}<br>
                        <strong>Company:</strong> {agreement.get('company_name', 'N/A')}<br>
                        <strong>Service Type:</strong> {agreement.get('service_type', 'N/A')}<br>
                        <strong>Generated:</strong> {agreement.get('generated_at', 'N/A')}
                    </div>
                </div>
                <div class="content">{content}</div>
                <div class="footer">
                    <p>Converted to PDF on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
            </body>
            </html>
            """
            
            # Generate PDF
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf()
            
            # Create new PDF file path
            pdf_filename = agreement['filename'].replace('.txt', '.pdf')
            pdf_file_path = file_path.replace('.txt', '.pdf')
            
            # Save PDF file
            with open(pdf_file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Update agreement metadata
            updated_metadata = {
                'filename': pdf_filename,
                'file_path': pdf_file_path,
                'file_size': len(pdf_bytes),
                'converted_at': datetime.now(),
                'original_file': file_path
            }
            
            # Update in MongoDB
            generated_agreements.collection.update_one(
                {'_id': agreement['_id']},
                {'$set': updated_metadata}
            )
            
            print(f"✅ Agreement converted to PDF: {pdf_filename}")
            
            return jsonify({
                'success': True,
                'message': 'Agreement converted to PDF successfully',
                'pdf_filename': pdf_filename,
                'pdf_path': pdf_file_path
            }), 200
            
        except ImportError:
            return jsonify({
                'success': False, 
                'message': 'PDF conversion not available. WeasyPrint is not installed.'
            }), 500
            
    except Exception as e:
        print(f"❌ Error converting agreement to PDF: {str(e)}")
        return jsonify({'success': False, 'message': f'Error converting agreement: {str(e)}'}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to verify Flask routing is working"""
    return jsonify({
        'success': True,
        'message': 'Flask routing is working correctly',
        'timestamp': datetime.now().isoformat(),
        'endpoint': '/api/test'
    }), 200

@app.route('/api/approval/test', methods=['GET', 'POST'])
def test_approval_endpoint():
    """Test endpoint for approval routing"""
    return jsonify({
        'success': True,
        'message': 'Approval endpoint routing is working',
        'method': request.method,
        'timestamp': datetime.now().isoformat(),
        'endpoint': '/api/approval/test'
    }), 200

@app.route('/api/client/feedback', methods=['POST'])
def submit_client_feedback():
    """Submit client feedback on approved document"""
    try:
        data = request.get_json()
        workflow_id = data.get('workflow_id')
        client_email = data.get('client_email')
        client_comments = data.get('comments', '')
        client_decision = data.get('decision')  # "accepted", "rejected", "needs_changes"
        
        print(f"🔍 Client feedback received: workflow_id={workflow_id}, client_email={client_email}, decision={client_decision}")
        
        if not all([workflow_id, client_email, client_decision]):
            return jsonify({
                'success': False,
                'message': 'Workflow ID, client email, and decision are required'
            }), 400
        
        if client_decision not in ['accepted', 'rejected', 'needs_changes']:
            return jsonify({
                'success': False,
                'message': 'Decision must be one of: accepted, rejected, needs_changes'
            }), 400
        
        # Verify workflow exists and belongs to this client
        workflow = approval_workflows.get_workflow_by_client_email(client_email, workflow_id)
        if not workflow:
            return jsonify({
                'success': False,
                'message': 'Workflow not found or access denied'
            }), 404
        
        # Submit client feedback
        success = approval_workflows.submit_client_feedback(workflow_id, client_comments, client_decision)
        
        if success:
            # Send notification email to manager/CEO about client feedback
            try:
                email_service = EmailService()
                
                # Get document details for the email
                document_type = workflow.get('document_type')
                document_id = workflow.get('document_id')
                
                if document_type == 'PDF':
                    document = generated_pdfs.get_pdf_by_id(document_id)
                elif document_type == 'Agreement':
                    document = generated_agreements.get_agreement_by_id(document_id)
                else:
                    document = None
                
                # Send notification to manager and CEO
                manager_email = workflow.get('manager_email')
                ceo_email = workflow.get('ceo_email')
                
                if manager_email:
                    email_service.send_client_feedback_notification(
                        recipient_email=manager_email,
                        recipient_role='manager',
                        workflow_data=workflow,
                        client_feedback={
                            'decision': client_decision,
                            'comments': client_comments,
                            'client_email': client_email
                        },
                        document=document
                    )
                
                if ceo_email:
                    email_service.send_client_feedback_notification(
                        recipient_email=ceo_email,
                        recipient_role='ceo',
                        workflow_data=workflow,
                        client_feedback={
                            'decision': client_decision,
                            'comments': client_comments,
                            'client_email': client_email
                        },
                        document=document
                    )
                
            except Exception as e:
                print(f"⚠️ Warning: Could not send client feedback notification emails: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Client feedback submitted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to submit client feedback'
            }), 500
            
    except Exception as e:
        print(f"❌ Error submitting client feedback: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error submitting client feedback: {str(e)}'
        }), 500

@app.route('/api/client/workflow/<workflow_id>', methods=['GET'])
def get_client_workflow(workflow_id):
    """Get workflow details for client review (public endpoint)"""
    try:
        # Get client email from query parameter for verification
        client_email = request.args.get('email')
        
        if not client_email:
            return jsonify({
                'success': False,
                'message': 'Client email is required'
            }), 400
        
        # Get workflow and verify client access
        workflow = approval_workflows.get_workflow_by_client_email(client_email, workflow_id)
        
        if not workflow:
            return jsonify({
                'success': False,
                'message': 'Workflow not found or access denied'
            }), 404
        
        # Get document details
        document_type = workflow.get('document_type')
        document_id = workflow.get('document_id')
        
        document = None
        if document_type == 'PDF':
            document = generated_pdfs.get_pdf_by_id(document_id)
        elif document_type == 'Agreement':
            document = generated_agreements.get_agreement_by_id(document_id)
        
        if not document:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        # Format workflow data for client
        formatted_workflow = {
            'workflow_id': str(workflow['_id']),
            'document_id': workflow.get('document_id'),
            'document_type': workflow.get('document_type'),
            'client_name': workflow.get('client_name'),
            'company_name': workflow.get('company_name'),
            'service_type': workflow.get('service_type', 'N/A'),
            'created_at': workflow.get('created_at'),
            'manager_approval_date': workflow.get('manager_approval_date'),
            'ceo_approval_date': workflow.get('ceo_approval_date'),
            'document': {
                'filename': document.get('filename'),
                'file_path': document.get('file_path'),
                'file_size': document.get('file_size')
            }
        }
        
        return jsonify({
            'success': True,
            'workflow': formatted_workflow
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting client workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting workflow details: {str(e)}'
        }), 500

@app.route('/client-feedback')
def client_feedback_form():
    """Serve the client feedback form HTML page"""
    try:
        return send_from_directory('approval_workflow', 'client-feedback.html')
    except Exception as e:
        print(f"❌ Error serving client feedback form: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error serving client feedback form'
        }), 500

@app.route('/api/client/feedback-workflows', methods=['GET'])
def get_client_feedback_workflows():
    """Get workflows awaiting client feedback"""
    try:
        # Get client feedback workflows
        feedback_workflows = approval_workflows.get_client_feedback_workflows()
        
        # Format workflows for response
        formatted_workflows = []
        for workflow in feedback_workflows:
            # Get document details
            document_type = workflow.get('document_type')
            document_id = workflow.get('document_id')
            
            document = None
            if document_type == 'PDF':
                document = generated_pdfs.get_pdf_by_id(document_id)
            elif document_type == 'Agreement':
                document = generated_agreements.get_agreement_by_id(document_id)
            
            formatted_workflow = {
                'workflow_id': str(workflow['_id']),
                'document_id': workflow.get('document_id'),
                'document_type': workflow.get('document_type'),
                'client_name': workflow.get('client_name'),
                'client_email': workflow.get('client_email'),
                'company_name': workflow.get('company_name'),
                'service_type': workflow.get('service_type', 'N/A'),
                'created_at': workflow.get('created_at'),
                'manager_approval_date': workflow.get('manager_approval_date'),
                'ceo_approval_date': workflow.get('ceo_approval_date'),
                'document_name': document.get('filename') if document else 'N/A'
            }
            formatted_workflows.append(formatted_workflow)
        
        return jsonify({
            'success': True,
            'workflows': formatted_workflows
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting client feedback workflows: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting client feedback workflows: {str(e)}'
        }), 500

@app.route('/api/approval/resubmit/<workflow_id>', methods=['POST'])
def resubmit_workflow(workflow_id):
    """Resubmit a denied workflow for re-approval"""
    try:
        # Get the workflow
        workflow = approval_workflows.get_workflow_by_id(workflow_id)
        
        if not workflow:
            return jsonify({
                'success': False,
                'message': 'Workflow not found'
            }), 404
        
        # Check if workflow is actually denied/cancelled
        if workflow.get('workflow_status') not in ['cancelled', 'client_rejected']:
            return jsonify({
                'success': False,
                'message': 'Only denied or cancelled workflows can be resubmitted'
            }), 400
        
        # Reset the workflow to initial state
        reset_data = {
            'workflow_status': 'active',
            'current_stage': 'manager',
            'manager_status': 'pending',
            'ceo_status': 'pending', 
            'client_status': 'pending',
            'manager_comments': '',
            'ceo_comments': '',
            'client_comments': '',
            'client_decision': '',
            'resubmitted_at': datetime.now(),
            'resubmit_count': (workflow.get('resubmit_count', 0) + 1),
            'updated_at': datetime.now()
        }
        
        # Update the workflow
        success = approval_workflows.update_workflow_custom(workflow_id, reset_data)
        
        if success:
            # Send notification emails about resubmission
            try:
                email_service = EmailService()
                
                # Notify manager
                manager_email = workflow.get('manager_email')
                if manager_email:
                    email_service.send_workflow_notification(
                        recipient_email=manager_email,
                        recipient_role='manager',
                        workflow_data=workflow,
                        action='resubmitted',
                        document_type=workflow.get('document_type'),
                        document_id=workflow.get('document_id')
                    )
                
                # Notify CEO
                ceo_email = workflow.get('ceo_email')
                if ceo_email:
                    email_service.send_workflow_notification(
                        recipient_email=ceo_email,
                        recipient_role='ceo',
                        workflow_data=workflow,
                        action='resubmitted',
                        document_type=workflow.get('document_type'),
                        document_id=workflow.get('document_id')
                    )
                
            except Exception as e:
                print(f"⚠️ Warning: Could not send resubmission notification emails: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Workflow resubmitted successfully',
                'workflow_id': workflow_id,
                'resubmit_count': reset_data['resubmit_count']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to resubmit workflow'
            }), 500
            
    except Exception as e:
        print(f"❌ Error resubmitting workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resubmitting workflow: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Log environment detection on startup
    try:
        from utils.url_helper import log_environment_detection
        print("🚀 Starting CPQ Application...")
        log_environment_detection()
    except ImportError:
        print("⚠️ URL helper not available, using default configuration")
        print("💻 Default base URL: http://localhost:5000")
    
    # Get port from environment variable for deployment (Render, Heroku, etc.)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        debug=debug,
        host='0.0.0.0',  # Allow external connections for deployment
        port=port,
        use_reloader=False,  # Prevents duplicate processes
        threaded=True
    )

# Template Builder API endpoints moved to blueprint in template_builder/__init__.py