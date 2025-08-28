from datetime import datetime
from bson import ObjectId
from cpq.db import db

class GeneratedAgreementCollection:
    """Handles generated agreement metadata storage in MongoDB"""
    
    def __init__(self):
        self.collection = db["storinggenratedaggremntfromquotemangnt"]
    
    def store_agreement_metadata(self, agreement_data):
        """Store agreement metadata after generation"""
        if not self._validate_agreement_data(agreement_data):
            raise ValueError("Invalid agreement data")
        
        agreement_data["generated_at"] = datetime.now()
        agreement_data["created_at"] = datetime.now()
        agreement_data["updated_at"] = datetime.now()
        
        return self.collection.insert_one(agreement_data)
    
    def get_agreement_by_id(self, agreement_id):
        """Get agreement metadata by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(agreement_id)})
        except:
            return None
    
    def get_agreements_by_quote_id(self, quote_id, limit=50):
        """Get all agreements for a specific quote"""
        return list(self.collection.find(
            {"quote_id": quote_id}
        ).sort("generated_at", -1).limit(limit))
    
    def get_agreements_by_client(self, client_name, limit=50):
        """Get all agreements for a specific client"""
        return list(self.collection.find(
            {"client_name": {"$regex": client_name, "$options": "i"}}
        ).sort("generated_at", -1).limit(limit))
    
    def get_agreements_by_company(self, company_name, limit=50):
        """Get all agreements for a specific company"""
        return list(self.collection.find(
            {"company_name": {"$regex": company_name, "$options": "i"}}
        ).sort("generated_at", -1).limit(limit))
    
    def get_all_agreements(self, limit=100):
        """Get all agreements with pagination"""
        return list(self.collection.find().sort("generated_at", -1).limit(limit))
    
    def delete_agreement(self, agreement_id):
        """Delete agreement metadata"""
        try:
            return self.collection.delete_one({"_id": ObjectId(agreement_id)})
        except:
            return None
    
    def _validate_agreement_data(self, agreement_data):
        """Validate agreement metadata structure"""
        required_fields = ["quote_id", "filename", "file_path", "client_name", "company_name"]
        return all(field in agreement_data for field in required_fields)
