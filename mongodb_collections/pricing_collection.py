from datetime import datetime
from bson import ObjectId
from cpq.db import db

class PricingCollection:
    """Handles CPQ pricing-related MongoDB operations"""
    
    def __init__(self):
        self.collection = db["pricing_configs"]
    
    def create_pricing_config(self, config_data):
        """Create a new pricing configuration"""
        if not self._validate_pricing_data(config_data):
            raise ValueError("Invalid pricing configuration data")
        
        config_data["created_at"] = datetime.now()
        config_data["updated_at"] = datetime.now()
        config_data["is_active"] = True
        
        return self.collection.insert_one(config_data)
    
    def get_pricing_config_by_id(self, config_id):
        """Get pricing configuration by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(config_id)})
        except:
            return None
    
    def get_active_pricing_config(self):
        """Get the currently active pricing configuration"""
        return self.collection.find_one({"is_active": True})
    
    def update_pricing_config(self, config_id, config_data):
        """Update existing pricing configuration"""
        if not self._validate_pricing_data(config_data):
            raise ValueError("Invalid pricing configuration data")
        
        config_data["updated_at"] = datetime.now()
        
        # Remove _id if present
        if '_id' in config_data:
            del config_data['_id']
        
        return self.collection.update_one(
            {"_id": ObjectId(config_id)},
            {"$set": config_data}
        )
    
    def deactivate_pricing_config(self, config_id):
        """Deactivate a pricing configuration"""
        return self.collection.update_one(
            {"_id": ObjectId(config_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
    
    def activate_pricing_config(self, config_id):
        """Activate a pricing configuration (deactivates others)"""
        # First deactivate all other configs
        self.collection.update_many(
            {"_id": {"$ne": ObjectId(config_id)}},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        
        # Then activate this one
        return self.collection.update_one(
            {"_id": ObjectId(config_id)},
            {"$set": {"is_active": True, "updated_at": datetime.now()}}
        )
    
    def get_all_pricing_configs(self, limit=100):
        """Get all pricing configurations"""
        return list(self.collection.find({}).sort("created_at", -1).limit(limit))
    
    def delete_pricing_config(self, config_id):
        """Delete pricing configuration by ID"""
        try:
            return self.collection.delete_one({"_id": ObjectId(config_id)})
        except:
            return None
    
    def get_pricing_history(self, limit=50):
        """Get pricing configuration change history"""
        return list(self.collection.find({}).sort("updated_at", -1).limit(limit))
    
    def _validate_pricing_data(self, data):
        """Validate pricing configuration data"""
        required_fields = ["name", "version", "pricing_rules"]
        return all(field in data for field in required_fields)
