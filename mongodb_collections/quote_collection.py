from datetime import datetime
from bson import ObjectId
from cpq.db import db

class QuoteCollection:
    """Handles quote-related MongoDB operations"""
    
    def __init__(self):
        self.collection = db["quotes"]
    
    def create_quote(self, quote_data):
        """Create a new quote with validation"""
        if not self._validate_quote_data(quote_data):
            raise ValueError("Invalid quote data")
        
        quote_data["timestamp"] = datetime.now()
        quote_data["status"] = "draft"
        quote_data["created_at"] = datetime.now()
        quote_data["updated_at"] = datetime.now()
        
        return self.collection.insert_one(quote_data)
    
    def get_quote_by_id(self, quote_id):
        """Get quote by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(quote_id)})
        except:
            return None
    
    def get_quotes_by_client(self, client_email, limit=50):
        """Get all quotes for a specific client"""
        return list(self.collection.find(
            {"client.email": client_email}
        ).sort("timestamp", -1).limit(limit))
    
    def update_quote_status(self, quote_id, new_status, notes=""):
        """Update quote status (draft → sent → accepted → rejected)"""
        update_data = {
            "status": new_status,
            "updated_at": datetime.now()
        }
        if notes:
            update_data["notes"] = notes
        
        return self.collection.update_one(
            {"_id": ObjectId(quote_id)},
            {"$set": update_data}
        )
    
    def get_quotes_by_status(self, status, limit=50):
        """Get quotes by status"""
        return list(self.collection.find(
            {"status": status}
        ).sort("timestamp", -1).limit(limit))
    
    def get_all_quotes(self, limit=100):
        """Get all quotes with pagination"""
        return list(self.collection.find({}).sort("timestamp", -1).limit(limit))
    
    def delete_quote(self, quote_id):
        """Delete quote by ID"""
        try:
            return self.collection.delete_one({"_id": ObjectId(quote_id)})
        except:
            return None
    
    def get_quote_stats(self):
        """Get quote statistics by status"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": "$quote.basic.totalCost"}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def _validate_quote_data(self, data):
        """Validate quote data before saving"""
        required_fields = ["client", "configuration", "quote"]
        return all(field in data for field in required_fields)
