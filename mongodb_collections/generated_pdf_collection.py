from datetime import datetime
from bson import ObjectId
from cpq.db import db

class GeneratedPDFCollection:
    """Handles generated PDF metadata storage in MongoDB"""
    
    def __init__(self):
        self.collection = db["storinggenratedpdfinqotemangamnet"]
    
    def store_pdf_metadata(self, pdf_data):
        """Store PDF metadata after generation"""
        if not self._validate_pdf_data(pdf_data):
            raise ValueError("Invalid PDF data")
        
        pdf_data["generated_at"] = datetime.now()
        pdf_data["created_at"] = datetime.now()
        pdf_data["updated_at"] = datetime.now()
        
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
    
    def _validate_pdf_data(self, pdf_data):
        """Validate PDF metadata structure"""
        required_fields = ["quote_id", "filename", "file_path", "client_name", "company_name"]
        return all(field in pdf_data for field in required_fields)
