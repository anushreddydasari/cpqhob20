from datetime import datetime
from bson import ObjectId
from cpq.db import db

class HubSpotDealCollection:
    """Handles HubSpot deal-related MongoDB operations"""
    
    def __init__(self):
        self.collection = db["hubspot_deals"]
    
    def store_deal(self, deal_data):
        """Store a new HubSpot deal with validation"""
        # Normalize incoming keys from frontend
        normalized = {
            'hubspot_id': deal_data.get('hubspot_id') or deal_data.get('id'),
            'dealname': deal_data.get('dealname', ''),
            'amount': deal_data.get('amount', ''),
            'closedate': deal_data.get('closedate', ''),
            'dealstage': deal_data.get('dealstage', ''),
            'dealtype': deal_data.get('dealtype', ''),
            'pipeline': deal_data.get('pipeline', ''),
            'hubspot_owner_id': deal_data.get('hubspot_owner_id', ''),
            'company': deal_data.get('company', ''),
            'source': deal_data.get('source', 'HubSpot'),
            'fetched_at': deal_data.get('fetched_at', datetime.now()),
            'status': deal_data.get('status', 'new')
        }

        if not self._validate_deal_data(normalized):
            raise ValueError("Invalid deal data")

        # Check if deal already exists
        existing = self.get_deal_by_hubspot_id(normalized['hubspot_id'])
        if existing:
            # Update existing deal
            normalized["updated_at"] = datetime.now()
            return self.collection.update_one(
                {"hubspot_id": normalized['hubspot_id']},
                {"$set": normalized}
            )
        else:
            # Create new deal
            normalized["created_at"] = datetime.now()
            normalized["updated_at"] = datetime.now()
            return self.collection.insert_one(normalized)
    
    def get_deal_by_id(self, deal_id):
        """Get deal by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(deal_id)})
        except:
            return None
    
    def get_deal_by_hubspot_id(self, hubspot_id):
        """Get deal by HubSpot ID"""
        return self.collection.find_one({"hubspot_id": hubspot_id})
    
    def get_all_deals(self, limit=100):
        """Get all deals with pagination"""
        return list(self.collection.find({}).sort("fetched_at", -1).limit(limit))
    
    def update_deal(self, deal_id, deal_data):
        """Update existing deal"""
        normalized = {
            'dealname': deal_data.get('dealname', ''),
            'amount': deal_data.get('amount', ''),
            'closedate': deal_data.get('closedate', ''),
            'dealstage': deal_data.get('dealstage', ''),
            'dealtype': deal_data.get('dealtype', ''),
            'pipeline': deal_data.get('pipeline', ''),
            'hubspot_owner_id': deal_data.get('hubspot_owner_id', ''),
            'company': deal_data.get('company', ''),
            'status': deal_data.get('status', '')
        }

        normalized["updated_at"] = datetime.now()

        return self.collection.update_one(
            {"_id": ObjectId(deal_id)},
            {"$set": normalized}
        )
    
    def delete_deal(self, deal_id):
        """Delete deal by ID"""
        try:
            return self.collection.delete_one({"_id": ObjectId(deal_id)})
        except:
            return None
    
    def search_deals(self, search_term, limit=50):
        """Search deals by name, company, or stage"""
        search_query = {
            "$or": [
                {"dealname": {"$regex": search_term, "$options": "i"}},
                {"company": {"$regex": search_term, "$options": "i"}},
                {"dealstage": {"$regex": search_term, "$options": "i"}}
            ]
        }

        return list(self.collection.find(search_query).sort("fetched_at", -1).limit(limit))
    
    def get_deal_stats(self):
        """Get deal statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$dealstage",
                    "count": {"$sum": 1},
                    "total_amount": {"$sum": {"$toDouble": "$amount"}}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def get_deals_by_stage(self, stage, limit=50):
        """Get deals by specific stage"""
        return list(self.collection.find({"dealstage": stage}).sort("fetched_at", -1).limit(limit))
    
    def get_deals_by_company(self, company_name, limit=50):
        """Get deals by company name"""
        return list(self.collection.find({"company": {"$regex": company_name, "$options": "i"}}).sort("fetched_at", -1).limit(limit))
    
    def _validate_deal_data(self, data):
        """Validate deal data before saving"""
        required_fields = ["hubspot_id", "dealname"]
        return all(data.get(field) for field in required_fields)
    
    def clear_all_deals(self):
        """Clear all deals from collection"""
        return self.collection.delete_many({})
