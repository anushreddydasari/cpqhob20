from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from .styles import PDFStyles

class PDFGenerator:
    """PDF generation for quotes and documents"""
    
    def __init__(self):
        self.styles = PDFStyles()
    
    def create_quote_pdf(self, client_data, quote_data, configuration):
        """Create a professional PDF quote"""
        
        # Create buffer for PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("PROFESSIONAL QUOTE", self.styles.get_title_style()))
        story.append(Paragraph("Migration Services & Solutions", self.styles.get_normal_style()))
        story.append(Spacer(1, 20))
        
        # Client Information
        story.append(Paragraph("Client Information", self.styles.get_heading_style()))
        client_info = [
            ['Name:', client_data.get('name', 'N/A')],
            ['Company:', client_data.get('company', 'N/A')],
            ['Email:', client_data.get('email', 'N/A')],
            ['Phone:', client_data.get('phone', 'N/A')],
            ['Service Type:', client_data.get('serviceType', 'N/A')]
        ]
        
        client_table = Table(client_info, colWidths=[2*inch, 4*inch])
        client_table.setStyle(TableStyle(self.styles.get_client_table_style()))
        story.append(client_table)
        story.append(Spacer(1, 20))
        
        # Quote Details
        story.append(Paragraph("Quote Details", self.styles.get_heading_style()))
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
        quote_table.setStyle(TableStyle(self.styles.get_quote_table_style()))
        story.append(quote_table)
        story.append(Spacer(1, 20))
        
        # Pricing Table
        story.append(Paragraph("Pricing Breakdown", self.styles.get_heading_style()))
        
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
            pricing_table.setStyle(TableStyle(self.styles.get_pricing_table_style()))
            story.append(pricing_table)
        
        story.append(Spacer(1, 20))
        
        # Terms and Conditions
        story.append(Paragraph("Terms & Conditions", self.styles.get_heading_style()))
        terms = [
            "• This quote is valid for 30 days from the date of issue",
            "• Payment terms: 50% upfront, 50% upon completion",
            "• Project timeline will be finalized upon acceptance",
            "• Any changes to scope may affect pricing",
            "• Support and maintenance included for 3 months post-migration"
        ]
        
        for term in terms:
            story.append(Paragraph(term, self.styles.get_normal_style()))
            story.append(Spacer(1, 6))
        
        story.append(Spacer(1, 20))
        
        # Contact Information
        story.append(Paragraph("Contact Information", self.styles.get_heading_style()))
        contact_info = [
            ['Email:', 'sales@yourcompany.com'],
            ['Phone:', '+1 (555) 123-4567'],
            ['Website:', 'www.yourcompany.com']
        ]
        
        contact_table = Table(contact_info, colWidths=[1*inch, 5*inch])
        contact_table.setStyle(TableStyle(self.styles.get_contact_table_style()))
        story.append(contact_table)
        
        # Build PDF
        doc.build(story)
        return buffer
