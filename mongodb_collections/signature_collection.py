from datetime import datetime
from cpq.db import db


class SignatureCollection:
    """Store and retrieve e-signatures captured in-app."""

    def __init__(self):
        self.collection = db["signatures"]

    def save_signature(self, payload: dict) -> str:
        """Save a signature image (data URL) and metadata.

        Expected keys: role (client|manager), name, email, company, quote_id (optional),
        signature_data (data URL base64), signed_ip, signed_user_agent
        """
        document = {
            "role": payload.get("role"),
            "name": payload.get("name"),
            "email": payload.get("email"),
            "company": payload.get("company"),
            "quote_id": payload.get("quote_id"),
            "signature_data": payload.get("signature_data"),
            "signed_ip": payload.get("signed_ip"),
            "signed_user_agent": payload.get("signed_user_agent"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def get_latest_signature(self, role: str, email: str):
        """Get the most recent signature by role and signer email."""
        doc = self.collection.find_one({"role": role, "email": email}, sort=[("created_at", -1)])
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])  # for JSON serialization
        return doc

from datetime import datetime
from cpq.db import db

class SignatureCollection:
    """Handles signature MongoDB operations"""
    
    def __init__(self):
        self.collection = db["signatures"]
    
    def create_signature(self, signature_data, signature_type="drawn", template_id=None, user_id=None, metadata=None):
        """Create a new signature record"""
        signature_doc = {
            "signature_data": signature_data,  # Base64 encoded image
            "signature_type": signature_type,  # "drawn" or "typed"
            "template_id": template_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_active": True
        }
        
        result = self.collection.insert_one(signature_doc)
        return str(result.inserted_id)
    
    def get_signature_by_id(self, signature_id):
        """Get signature by ID"""
        from bson import ObjectId
        doc = self.collection.find_one({"_id": ObjectId(signature_id)})
        if doc and '_id' in doc:
            doc['_id'] = str(doc['_id'])
        return doc
    
    def get_signatures_by_template(self, template_id):
        """Get all signatures for a specific template"""
        cursor = self.collection.find({"template_id": template_id, "is_active": True})
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
    
    def get_signatures_by_user(self, user_id):
        """Get all signatures for a specific user"""
        cursor = self.collection.find({"user_id": user_id, "is_active": True})
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
    
    def update_signature(self, signature_id, updates):
        """Update signature metadata"""
        from bson import ObjectId
        updates["updated_at"] = datetime.now()
        
        result = self.collection.update_one(
            {"_id": ObjectId(signature_id)},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def delete_signature(self, signature_id):
        """Soft delete signature (mark as inactive)"""
        from bson import ObjectId
        result = self.collection.update_one(
            {"_id": ObjectId(signature_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
    
    def get_all_active_signatures(self):
        """Get all active signatures"""
        cursor = self.collection.find({"is_active": True}).sort("created_at", -1)
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
