from datetime import datetime
from bson import ObjectId
from cpq.db import db

class ClientCollection:
    """Handles client-related MongoDB operations"""
    
    def __init__(self):
        self.collection = db["clients"]
    
    def create_client(self, client_data):
        """Create a new client with validation"""
        # Normalize incoming keys from frontend
        normalized = {
            'clientName': client_data.get('clientName') or client_data.get('name'),
            'companyName': client_data.get('companyName') or client_data.get('company'),
            'email': client_data.get('email'),
            'phoneNumber': client_data.get('phoneNumber') or client_data.get('phone'),
            'serviceType': client_data.get('serviceType'),
            'requirements': client_data.get('requirements')
        }

        if not self._validate_client_data(normalized):
            raise ValueError("Invalid client data")

        normalized["created_at"] = datetime.now()
        normalized["updated_at"] = datetime.now()

        return self.collection.insert_one(normalized)
    
    def get_client_by_id(self, client_id):
        """Get client by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(client_id)})
        except:
            return None
    
    def get_client_by_email(self, email):
        """Get client by email address"""
        return self.collection.find_one({"email": email})
    
    def get_all_clients(self, limit=100):
        """Get all clients with pagination"""
        return list(self.collection.find({}).sort("created_at", -1).limit(limit))
    
    def update_client(self, client_id, client_data):
        """Update existing client"""
        normalized = {
            'clientName': client_data.get('clientName') or client_data.get('name'),
            'companyName': client_data.get('companyName') or client_data.get('company'),
            'email': client_data.get('email'),
            'phoneNumber': client_data.get('phoneNumber') or client_data.get('phone'),
            'serviceType': client_data.get('serviceType'),
            'requirements': client_data.get('requirements')
        }

        if not self._validate_client_data(normalized):
            raise ValueError("Invalid client data")

        normalized["updated_at"] = datetime.now()

        return self.collection.update_one(
            {"_id": ObjectId(client_id)},
            {"$set": normalized}
        )
    
    def delete_client(self, client_id):
        """Delete client by ID"""
        try:
            return self.collection.delete_one({"_id": ObjectId(client_id)})
        except:
            return None
    
    def search_clients(self, search_term, limit=50):
        """Search clients by name, email, or company"""
        search_query = {
            "$or": [
                {"clientName": {"$regex": search_term, "$options": "i"}},
                {"email": {"$regex": search_term, "$options": "i"}},
                {"companyName": {"$regex": search_term, "$options": "i"}}
            ]
        }

        return list(self.collection.find(search_query).sort("created_at", -1).limit(limit))
    
    def get_client_stats(self):
        """Get client statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$serviceType",
                    "count": {"$sum": 1}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def _validate_client_data(self, data):
        """Validate client data before saving"""
        required_fields = ["clientName", "email", "companyName", "phoneNumber"]
        return all(data.get(field) for field in required_fields)
