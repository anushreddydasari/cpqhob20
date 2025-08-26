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
                with open(pdf_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                           filename=f"quote_{company_name}_{datetime.now().strftime('%Y%m%d')}.pdf")
                    msg.attach(pdf_attachment)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            return {
                "success": True,
                "message": f"Quote email sent successfully to {recipient_email}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
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
                <h1>🚀 Professional Quote</h1>
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


