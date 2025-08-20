from datetime import datetime
from bson import ObjectId
from cpq.db import db

class HubSpotContactCollection:
    """Handles HubSpot contact MongoDB operations"""
    
    def __init__(self):
        self.collection = db["hubspot_contacts"]
    
    def store_contact(self, contact_data):
        """Store HubSpot contact with duplicate checking"""
        if not self._validate_contact_data(contact_data):
            raise ValueError("Invalid contact data")
        
        # Check if contact already exists
        existing_contact = self.collection.find_one({"hubspot_id": contact_data["hubspot_id"]})
        
        if existing_contact:
            # Update existing contact
            contact_data["fetched_at"] = datetime.now()
            contact_data["updated_at"] = datetime.now()
            result = self.collection.update_one(
                {"hubspot_id": contact_data["hubspot_id"]},
                {"$set": contact_data}
            )
            contact_data["action"] = "updated"
            return result
        else:
            # Insert new contact
            contact_data["fetched_at"] = datetime.now()
            contact_data["created_at"] = datetime.now()
            contact_data["status"] = "new"
            result = self.collection.insert_one(contact_data)
            contact_data["action"] = "inserted"
            return result
    
    def get_contact_by_hubspot_id(self, hubspot_id):
        """Get contact by HubSpot ID"""
        return self.collection.find_one({"hubspot_id": hubspot_id})
    
    def get_contacts_by_status(self, status, limit=50):
        """Get contacts by status"""
        return list(self.collection.find(
            {"status": status}
        ).sort("fetched_at", -1).limit(limit))
    
    def get_all_contacts(self, limit=100):
        """Get all HubSpot contacts"""
        return list(self.collection.find({}).sort("fetched_at", -1).limit(limit))
    
    def update_contact_status(self, hubspot_id, new_status, notes=""):
        """Update contact status"""
        update_data = {
            "status": new_status,
            "updated_at": datetime.now()
        }
        if notes:
            update_data["notes"] = notes
        
        return self.collection.update_one(
            {"hubspot_id": hubspot_id},
            {"$set": update_data}
        )
    
    def search_contacts(self, search_term, limit=50):
        """Search contacts by name, email, company, or job title"""
        search_query = {
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"email": {"$regex": search_term, "$options": "i"}},
                {"company": {"$regex": search_term, "$options": "i"}},
                {"job_title": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        return list(self.collection.find(search_query).sort("fetched_at", -1).limit(limit))
    
    def get_contact_stats(self):
        """Get contact statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def _validate_contact_data(self, data):
        """Validate contact data before saving"""
        required_fields = ["hubspot_id", "name", "email"]
        return all(field in data for field in required_fields)
