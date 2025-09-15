from datetime import datetime
from bson import ObjectId
from cpq.db import db

class GeneratedAgreementCollection:
    """Handles generated agreement metadata storage in MongoDB"""
    
    def __init__(self):
        self.collection = db["storinggenratedaggremntfromquotemangnt"]
    
    def store_agreement_metadata(self, agreement_data, agreement_content=None):
        """Store agreement metadata after generation with optional content for regeneration"""
        if not self._validate_agreement_data(agreement_data):
            raise ValueError("Invalid agreement data")
        
        agreement_data["generated_at"] = datetime.now()
        agreement_data["created_at"] = datetime.now()
        agreement_data["updated_at"] = datetime.now()
        
        # Store agreement content as base64 for regeneration if provided
        if agreement_content:
            import base64
            agreement_data["agreement_data"] = base64.b64encode(agreement_content).decode('utf-8')
        
        return self.collection.insert_one(agreement_data)
    
    def get_agreement_by_id(self, agreement_id):
        """Get agreement metadata by MongoDB ObjectId or quote_id"""
        try:
            # First try to find by MongoDB ObjectId
            if ObjectId.is_valid(agreement_id):
                agreement = self.collection.find_one({"_id": ObjectId(agreement_id)})
                if agreement:
                    return agreement
            
            # If not found by ObjectId, try to find by quote_id
            agreement = self.collection.find_one({"quote_id": agreement_id})
            if agreement:
                return agreement
            
            return None
        except Exception as e:
            print(f"Error looking up agreement {agreement_id}: {e}")
            return None
    
    def get_agreements_by_quote_id(self, quote_id, limit=50):
        """Get all agreements for a specific quote"""
        return list(self.collection.find(
            {"quote_id": quote_id}
        ).sort("generated_at", -1).limit(limit))
    
    def get_agreement_by_quote_id(self, quote_id):
        """Get the most recent agreement for a specific quote"""
        return self.collection.find_one(
            {"quote_id": quote_id},
            sort=[("generated_at", -1)]
        )
    
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
