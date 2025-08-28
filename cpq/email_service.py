import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.mime.application import MIMEApplication
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('GMAIL_EMAIL')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("GMAIL_EMAIL and GMAIL_APP_PASSWORD must be set in .env file")
    
    def send_quote_email(self, recipient_email, recipient_name, company_name, quote_data, pdf_path=None):
        """
        Send quote email to client
        
        Args:
            recipient_email (str): Client's email address
            recipient_name (str): Client's name
            company_name (str): Client's company name
            quote_data (dict): Quote information
            pdf_path (str): Path to PDF quote file (optional)
        
        Returns:
            dict: Success status and message
        """
        try:
            print(f"🔍 Debug: Starting email send to {recipient_email}")
            print(f"🔍 Debug: PDF path provided: {pdf_path}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Professional Quote - {company_name} Migration Services"
            
            # Email body
            body = self._create_email_body(recipient_name, company_name, quote_data)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach PDF if provided
            if pdf_path and os.path.exists(pdf_path):
                print(f"✅ Debug: PDF file exists at {pdf_path}")
                print(f"✅ Debug: PDF file size: {os.path.getsize(pdf_path)} bytes")
                
                with open(pdf_path, "rb") as f:
                    pdf_content = f.read()
                    pdf_attachment = MIMEApplication(pdf_content, _subtype="pdf")
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                           filename=f"quote_{company_name}_{datetime.now().strftime('%Y%m%d')}.pdf")
                    msg.attach(pdf_attachment)
                    print(f"✅ Debug: PDF attachment added to email")
            else:
                print(f"⚠️ Debug: No PDF attachment - path: {pdf_path}, exists: {os.path.exists(pdf_path) if pdf_path else False}")
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            print(f"✅ Debug: Email sent successfully to {recipient_email}")
            
            return {
                "success": True,
                "message": f"Quote email sent successfully to {recipient_email}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Debug: Email sending failed: {str(e)}")
            import traceback
            print(f"❌ Debug: Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def send_email_with_attachments(self, recipient_email, subject, body, attachments=None):
        """
        Send email with multiple file attachments
        
        Args:
            recipient_email (str): Recipient's email address
            subject (str): Email subject
            body (str): Email body (can be HTML)
            attachments (list): List of attachment dictionaries with 'filename' and 'file_path'
        
        Returns:
            dict: Success status and message
        """
        try:
            print(f"🔍 Debug: Starting email with attachments to {recipient_email}")
            print(f"🔍 Debug: Number of attachments: {len(attachments) if attachments else 0}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Check if body is HTML
            if '<html>' in body or '<body>' in body:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Attach files if provided
            if attachments:
                for i, attachment in enumerate(attachments):
                    file_path = attachment.get('file_path')
                    filename = attachment.get('filename', 'attachment')
                    
                    print(f"🔍 Debug: Processing attachment {i+1}: {filename} at {file_path}")
                    
                    if file_path and os.path.exists(file_path):
                        print(f"✅ Debug: File exists, size: {os.path.getsize(file_path)} bytes")
                        
                        # Determine MIME type based on file extension
                        file_ext = os.path.splitext(file_path)[1].lower()
                        print(f"🔍 Debug: File extension: {file_ext}")
                        
                        if file_ext == '.pdf':
                            with open(file_path, "rb") as f:
                                file_attachment = MIMEApplication(f.read(), _subtype="pdf")
                        elif file_ext in ['.docx', '.doc']:
                            with open(file_path, "rb") as f:
                                file_attachment = MIMEApplication(f.read(), _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document")
                        elif file_ext in ['.txt']:
                            with open(file_path, "rb") as f:
                                file_attachment = MIMEText(f.read())
                        else:
                            # Generic binary file
                            with open(file_path, "rb") as f:
                                file_attachment = MIMEBase('application', 'octet-stream')
                                file_attachment.set_payload(f.read())
                                encoders.encode_base64(file_attachment)
                        
                        # Add attachment header
                        if file_ext != '.txt':
                            file_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                        
                        msg.attach(file_attachment)
                        print(f"✅ Debug: Attachment {filename} added successfully")
                    else:
                        print(f"⚠️ Debug: File not found or path invalid: {file_path}")
            else:
                print(f"⚠️ Debug: No attachments provided")
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            print(f"✅ Debug: Email with attachments sent successfully to {recipient_email}")
            
            return {
                "success": True,
                "message": f"Email sent successfully to {recipient_email} with {len(attachments) if attachments else 0} attachment(s)",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Debug: Email with attachments failed: {str(e)}")
            import traceback
            print(f"❌ Debug: Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_email_body(self, recipient_name, company_name, quote_data):
        """Create professional email body HTML"""
        
        # Get quote details
        basic_cost = quote_data.get('basic', {}).get('totalCost', 0)
        standard_cost = quote_data.get('standard', {}).get('totalCost', 0)
        advanced_cost = quote_data.get('advanced', {}).get('totalCost', 0)
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .quote-summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .pricing-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .pricing-table th, .pricing-table td {{ padding: 12px; text-align: center; border: 1px solid #dee2e6; }}
                .pricing-table th {{ background: #667eea; color: white; }}
                .cta {{ background: #28a745; color: white; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>�� Professional Quote</h1>
                <p>Migration Services & Solutions</p>
            </div>
            
            <div class="content">
                <p>Dear {recipient_name},</p>
                
                <p>Thank you for your interest in our migration services. We're excited to present you with a comprehensive quote for {company_name}.</p>
                
                <div class="quote-summary">
                    <h2>📋 Quote Summary</h2>
                    <p>We've prepared three service tiers to meet your specific needs:</p>
                    
                    <table class="pricing-table">
                        <tr>
                            <th>Service Tier</th>
                            <th>Total Cost</th>
                            <th>Features</th>
                        </tr>
                        <tr>
                            <td><strong>Basic Plan</strong></td>
                            <td><strong>${basic_cost:,.2f}</strong></td>
                            <td>Essential migration services</td>
                        </tr>
                        <tr>
                            <td><strong>Standard Plan</strong></td>
                            <td><strong>${standard_cost:,.2f}</strong></td>
                            <td>Enhanced features & support</td>
                        </tr>
                        <tr>
                            <td><strong>Advanced Plan</strong></td>
                            <td><strong>${advanced_cost:,.2f}</strong></td>
                            <td>Premium services & priority support</td>
                        </tr>
                    </table>
                </div>
                
                <div class="cta">
                    <h3>🎯 Next Steps</h3>
                    <p>Please review the attached detailed quote and let us know if you have any questions or would like to discuss any specific requirements.</p>
                </div>
                
                <p>We're here to help you choose the best option for your business needs.</p>
                
                <p>Best regards,<br>
                <strong>Your Migration Services Team</strong></p>
            </div>
            
            <div class="footer">
                <p>📧 sales@yourcompany.com | 📱 +1 (555) 123-4567 | 🌐 www.yourcompany.com</p>
                <p><small>This quote is valid for 30 days from the date of issue.</small></p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def test_connection(self):
        """Test Gmail SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.quit()
            
            return {
                "success": True,
                "message": "Gmail SMTP connection successful!"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Gmail SMTP connection failed: {str(e)}"
            }

    def send_email(self, recipient_email, subject, body):
        """
        Send a simple email
        
        Args:
            recipient_email (str): Recipient's email address
            subject (str): Email subject
            body (str): Email body (can be HTML)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Check if body is HTML
            if '<html>' in body or '<body>' in body:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"❌ Email sending failed: {str(e)}")
            return False

    def send_approval_workflow_email(self, recipient_email, recipient_role, workflow_data, pdf_path=None):
        """
        Send approval workflow email to managers/CEOs with PDF and approval buttons
        
        Args:
            recipient_email (str): Recipient's email address
            recipient_role (str): Role (manager/ceo)
            workflow_data (dict): Workflow information
            pdf_path (str): Path to PDF document file
        
        Returns:
            dict: Success status and message
        """
        try:
            print(f"🔍 Debug: Starting approval email send to {recipient_email} (Role: {recipient_role})")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # Set subject based on role
            if recipient_role == 'manager':
                msg['Subject'] = f"�� APPROVAL REQUIRED: {workflow_data.get('document_type', 'Document')} - {workflow_data.get('document_id', 'N/A')}"
            else:
                msg['Subject'] = f"👑 CEO APPROVAL REQUIRED: {workflow_data.get('document_type', 'Document')} - {workflow_data.get('document_id', 'N/A')}"
            
            # Create HTML email body with approval buttons - PASS recipient_email here!
            html_body = self._create_approval_email_body(recipient_role, workflow_data, recipient_email)
            
            # Attach HTML content
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach PDF if provided
            if pdf_path and os.path.exists(pdf_path):
                print(f"✅ Debug: PDF file exists at {pdf_path}")
                
                with open(pdf_path, "rb") as f:
                    pdf_content = f.read()
                    pdf_attachment = MIMEApplication(pdf_content, _subtype="pdf")
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                           filename=f"{workflow_data.get('document_type', 'Document')}_{workflow_data.get('document_id', 'N/A')}.pdf")
                    msg.attach(pdf_attachment)
                    print(f"✅ Debug: PDF attachment added to approval email")
            else:
                print(f"⚠️ Debug: No PDF attachment for approval email")
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            print(f"✅ Debug: Approval email sent successfully to {recipient_email}")
            
            return {
                "success": True,
                "message": f"Approval email sent successfully to {recipient_email}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Debug: Approval email sending failed: {str(e)}")
            import traceback
            print(f"❌ Debug: Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to send approval email: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_approval_email_body(self, recipient_role, workflow_data, recipient_email):
        """Create HTML email body for approval workflow emails"""
        
        # Get base URL for approval links
        base_url = os.getenv('APP_BASE_URL', 'http://localhost:5000')
        
        # Create approval/rejection links
        workflow_id = workflow_data.get('_id', '')
        approve_link = f"{base_url}/api/approval/approve"
        deny_link = f"{base_url}/api/approval/deny"
        
        # Style the email
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document Approval Required</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .document-info {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                .approval-buttons {{ text-align: center; margin: 30px 0; }}
                .btn {{ display: inline-block; padding: 15px 30px; margin: 0 10px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; }}
                .btn-approve {{ background: #28a745; color: white; }}
                .btn-deny {{ background: #dc3545; color: white; }}
                .btn:hover {{ opacity: 0.9; transform: translateY(-2px); transition: all 0.3s ease; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .workflow-status {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Document Approval Required</h1>
                    <p>Your attention is needed for an important document</p>
                </div>
                
                <div class="content">
                    <div class="workflow-status">
                        <h3>�� Workflow Status</h3>
                        <p><strong>Current Stage:</strong> {recipient_role.title()} Review</p>
                        <p><strong>Document Type:</strong> {workflow_data.get('document_type', 'N/A')}</p>
                        <p><strong>Document ID:</strong> {workflow_data.get('document_id', 'N/A')}</p>
                    </div>
                    
                    <div class="document-info">
                        <h3>�� Document Details</h3>
                        <p><strong>Client:</strong> {workflow_data.get('client_name', 'N/A')}</p>
                        <p><strong>Company:</strong> {workflow_data.get('company_name', 'N/A')}</p>
                        <p><strong>Submitted:</strong> {workflow_data.get('created_at', 'N/A')}</p>
                        <p><strong>Priority:</strong> {workflow_data.get('priority', 'Normal')}</p>
                    </div>
                    
                    <div class="approval-buttons">
                        <h3>✅ Take Action</h3>
                        <p>Please review the attached PDF and take action:</p>
                        
                        <a href="{approve_link}" class="btn btn-approve">
                            ✅ APPROVE
                        </a>
                        
                        <a href="{deny_link}" class="btn btn-deny">
                            ❌ REJECT
                        </a>
                    </div>
                    
                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
                        <h4>💡 How to Approve/Reject:</h4>
                        <ol>
                            <li><strong>Review the PDF</strong> attached to this email</li>
                            <li><strong>Click APPROVE</strong> if the document meets requirements</li>
                            <li><strong>Click REJECT</strong> if changes are needed</li>
                            <li><strong>Add comments</strong> explaining your decision</li>
                        </ol>
                    </div>
                    
                    <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                        <h4>�� Alternative Access:</h4>
                        <p>You can also review and approve this document through our web dashboard:</p>
                        <p><a href="{base_url}/approval-dashboard?role={recipient_role}&email={recipient_email}" style="color: #17a2b8; text-decoration: underline;">📊 Open Approval Dashboard</a></p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from your CPQ Approval System</p>
                    <p>If you have questions, please contact your system administrator</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html