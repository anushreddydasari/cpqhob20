from datetime import datetime
from bson import ObjectId
from cpq.db import db

class SMTPCollection:
    """Handles SMTP connection and testing logs"""
    
    def __init__(self):
        self.collection = db["smtp_logs"]
    
    def log_connection_test(self, test_data):
        """Log SMTP connection test results"""
        test_data["tested_at"] = datetime.now()
        return self.collection.insert_one(test_data)
    
    def log_connection_success(self, connection_data):
        """Log successful SMTP connection"""
        connection_data["connected_at"] = datetime.now()
        connection_data["status"] = "success"
        return self.collection.insert_one(connection_data)
    
    def log_connection_failed(self, connection_data, error_message):
        """Log failed SMTP connection"""
        connection_data["attempted_at"] = datetime.now()
        connection_data["status"] = "failed"
        connection_data["error"] = error_message
        return self.collection.insert_one(connection_data)
    
    def get_connection_history(self, limit=50):
        """Get SMTP connection history"""
        return list(self.collection.find({}).sort("tested_at", -1).limit(limit))
    
    def get_connection_stats(self):
        """Get SMTP connection statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def get_last_successful_connection(self):
        """Get the last successful SMTP connection"""
        return self.collection.find_one(
            {"status": "success"},
            sort=[("connected_at", -1)]
        )
