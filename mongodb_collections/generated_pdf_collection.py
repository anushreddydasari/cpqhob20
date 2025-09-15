from datetime import datetime
from bson import ObjectId
from cpq.db import db
import base64

class GeneratedPDFCollection:
    """Handles generated PDF metadata storage in MongoDB"""
    
    def __init__(self):
        self.collection = db["storinggenratedpdfinqotemangamnet"]
    
    def store_pdf_metadata(self, pdf_data, pdf_content=None):
        """Store PDF metadata after generation with optional PDF content for regeneration"""
        if not self._validate_pdf_data(pdf_data):
            raise ValueError("Invalid PDF data")
        
        pdf_data["generated_at"] = datetime.now()
        pdf_data["created_at"] = datetime.now()
        pdf_data["updated_at"] = datetime.now()
        
        # Store PDF content as base64 for regeneration if provided
        if pdf_content:
            import base64
            pdf_data["pdf_data"] = base64.b64encode(pdf_content).decode('utf-8')
        
        return self.collection.insert_one(pdf_data)
    
    def get_pdf_by_id(self, pdf_id):
        """Get PDF metadata by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(pdf_id)})
        except:
            return None
    
    def get_pdfs_by_quote_id(self, quote_id, limit=50):
        """Get all PDFs for a specific quote"""
        return list(self.collection.find(
            {"quote_id": quote_id}
        ).sort("generated_at", -1).limit(limit))
    
    def get_pdfs_by_client(self, client_name, limit=50):
        """Get all PDFs for a specific client"""
        return list(self.collection.find(
            {"client_name": {"$regex": client_name, "$options": "i"}}
        ).sort("generated_at", -1).limit(limit))
    
    def get_pdfs_by_company(self, company_name, limit=50):
        """Get all PDFs for a specific company"""
        return list(self.collection.find(
            {"company_name": {"$regex": company_name, "$options": "i"}}
        ).sort("generated_at", -1).limit(limit))
    
    def get_all_pdfs(self, limit=100):
        """Get all PDFs with pagination"""
        return list(self.collection.find().sort("generated_at", -1).limit(limit))
    
    def delete_pdf(self, pdf_id):
        """Delete PDF metadata"""
        try:
            return self.collection.delete_one({"_id": ObjectId(pdf_id)})
        except:
            return None
    
    def regenerate_pdf_from_quote(self, pdf_id, quote_data):
        """Regenerate PDF from stored quote data when file is missing"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from io import BytesIO
            import os
            
            # Create PDF buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title = Paragraph("Quote Details", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Add client information
            client = quote_data.get('client', {})
            client_info = f"""
            <b>Client Information:</b><br/>
            Name: {client.get('name', 'N/A')}<br/>
            Company: {client.get('company', 'N/A')}<br/>
            Email: {client.get('email', 'N/A')}<br/>
            Phone: {client.get('phone', 'N/A')}<br/>
            Service Type: {client.get('serviceType', 'N/A')}
            """
            story.append(Paragraph(client_info, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Add configuration
            config = quote_data.get('configuration', {})
            config_info = f"""
            <b>Configuration:</b><br/>
            Users: {config.get('users', 'N/A')}<br/>
            Instance Type: {config.get('instanceType', 'N/A')}<br/>
            Instances: {config.get('instances', 'N/A')}<br/>
            Duration: {config.get('duration', 'N/A')} months<br/>
            Migration Type: {config.get('migrationType', 'N/A')}<br/>
            Data Size: {config.get('dataSize', 'N/A')} GB
            """
            story.append(Paragraph(config_info, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Add pricing if available
            quote_pricing = quote_data.get('quote', {})
            if quote_pricing:
                pricing_info = f"""
                <b>Pricing:</b><br/>
                Basic Plan: ${quote_pricing.get('basic', {}).get('totalCost', 'N/A')}<br/>
                Premium Plan: ${quote_pricing.get('premium', {}).get('totalCost', 'N/A')}<br/>
                Enterprise Plan: ${quote_pricing.get('enterprise', {}).get('totalCost', 'N/A')}
                """
                story.append(Paragraph(pricing_info, styles['Normal']))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            # Get the PDF metadata
            pdf_metadata = self.get_pdf_by_id(pdf_id)
            if not pdf_metadata:
                return None, "PDF metadata not found"
            
            # Save regenerated PDF
            file_path = pdf_metadata.get('file_path')
            if file_path:
                # Ensure documents directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save the regenerated PDF
                with open(file_path, 'wb') as f:
                    f.write(buffer.getvalue())
                
                # Update the PDF data in database
                pdf_content = buffer.getvalue()
                self.collection.update_one(
                    {"_id": ObjectId(pdf_id)},
                    {"$set": {
                        "pdf_data": base64.b64encode(pdf_content).decode('utf-8'),
                        "updated_at": datetime.now()
                    }}
                )
                
                return file_path, "PDF regenerated successfully"
            else:
                return None, "No file path stored for this PDF"
                
        except Exception as e:
            return None, f"Error regenerating PDF: {str(e)}"
    
    def _validate_pdf_data(self, pdf_data):
        """Validate PDF metadata structure"""
        required_fields = ["quote_id", "filename", "file_path", "client_name", "company_name"]
        return all(field in pdf_data for field in required_fields)
