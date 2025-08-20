from datetime import datetime, timedelta
from bson import ObjectId
from cpq.db import db

class HubSpotIntegrationCollection:
    """Handles HubSpot integration MongoDB operations"""
    
    def __init__(self):
        self.collection = db["hubspot_integrations"]
    
    def log_api_call(self, api_data):
        """Log HubSpot API call"""
        api_data["timestamp"] = datetime.now()
        api_data["status"] = "success"
        return self.collection.insert_one(api_data)
    
    def log_api_error(self, api_data, error_message):
        """Log HubSpot API error"""
        api_data["timestamp"] = datetime.now()
        api_data["status"] = "error"
        api_data["error"] = error_message
        return self.collection.insert_one(api_data)
    
    def log_contact_sync(self, sync_data):
        """Log contact synchronization activity"""
        sync_data["synced_at"] = datetime.now()
        sync_data["sync_type"] = "contact_sync"
        return self.collection.insert_one(sync_data)
    
    def log_integration_test(self, test_data):
        """Log integration test results"""
        test_data["tested_at"] = datetime.now()
        return self.collection.insert_one(test_data)
    
    def get_integration_history(self, limit=100):
        """Get integration activity history"""
        return list(self.collection.find({}).sort("timestamp", -1).limit(limit))
    
    def get_api_call_stats(self):
        """Get API call statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def get_sync_history(self, sync_type=None, limit=50):
        """Get synchronization history"""
        filter_query = {}
        if sync_type:
            filter_query["sync_type"] = sync_type
        
        return list(self.collection.find(filter_query).sort("synced_at", -1).limit(limit))
    
    def get_last_successful_sync(self):
        """Get the last successful synchronization"""
        return self.collection.find_one(
            {"status": "success", "sync_type": "contact_sync"},
            sort=[("synced_at", -1)]
        )
    
    def get_integration_health(self):
        """Get integration health status"""
        # Get last 24 hours of activity
        yesterday = datetime.now() - timedelta(days=1)
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": yesterday}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        return list(self.collection.aggregate(pipeline))
