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
    
    def create_quote_pdf(self, client_data, quote_data, configuration, selected_plan='standard'):
        """Create a professional PDF quote with selected plan"""
        
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
        
        # Pricing Table - Show only selected plan
        story.append(Paragraph("Pricing Breakdown", self.styles.get_heading_style()))
        
        if quote_data:
            # Get selected plan data
            selected_plan_data = quote_data.get(selected_plan, quote_data.get('standard', {}))
            plan_name = selected_plan.replace('_', ' ').title() + ' Plan'
            
            # Create single-column table for selected plan only
            pricing_data = [
                ['Service Details', plan_name]
            ]
            
            # Add pricing rows for selected plan only
            if selected_plan_data:
                pricing_data.extend([
                    ['Per User Cost', f"${selected_plan_data.get('perUserCost', 0):.2f}"],
                    ['Per GB Cost', f"${selected_plan_data.get('perGBCost', 0):.2f}"],
                    ['Total User Cost', f"${selected_plan_data.get('totalUserCost', 0):.2f}"],
                    ['Data Cost', f"${selected_plan_data.get('dataCost', 0):.2f}"],
                    ['Migration Cost', f"${selected_plan_data.get('migrationCost', 0):.2f}"],
                    ['Instance Cost', f"${selected_plan_data.get('instanceCost', 0):.2f}"],
                    ['TOTAL COST', f"${selected_plan_data.get('totalCost', 0):.2f}"]
                ])
            
            pricing_table = Table(pricing_data, colWidths=[3*inch, 2*inch])
            
            # Create table style for single plan
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), '#667eea'),  # Header background
                ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),      # Header text color
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),          # Left align all
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),          # Right align prices
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),   # Service details font
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),  # Price font
                ('FONTSIZE', (0, 0), (-1, -1), 10),           # Font size
                ('GRID', (0, 0), (-1, -1), 1, 'black'),       # Grid lines
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), ['white', '#f8f9fa']),  # Alternating rows
                ('BACKGROUND', (0, -1), (-1, -1), '#28a745'),  # Total row background
                ('TEXTCOLOR', (0, -1), (-1, -1), 'white'),     # Total row text color
                ('FONTSIZE', (0, -1), (-1, -1), 12),          # Total row font size
            ]
            
            pricing_table.setStyle(TableStyle(table_style))
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
