from datetime import datetime
from bson import ObjectId
from cpq.db import db

class FormTrackingCollection:
    """Handles form tracking MongoDB operations"""
    
    def __init__(self):
        self.collection = db["form_tracking"]
    
    def create_form_session(self, quote_id, client_data, form_type="signature"):
        """Create a new form tracking session"""
        session_data = {
            "quote_id": quote_id,
            "client_data": client_data,
            "form_type": form_type,
            "session_id": self._generate_session_id(),
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "interactions": {
                "page_views": 0,
                "field_interactions": 0,
                "time_spent": 0,
                "errors": 0,
                "clicks": 0,
                "submissions": 0
            },
            "signature_data": None,
            "approval_data": None,
            "last_activity": None
        }
        
        self.collection.insert_one(session_data)
        return session_data["session_id"]
    
    def log_page_view(self, session_id, user_agent=None, ip_address=None):
        """Log when form page is viewed"""
        interaction = {
            "timestamp": datetime.now(),
            "type": "page_view",
            "user_agent": user_agent,
            "ip_address": ip_address
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interactions.page_views": 1},
                "$push": {"interactions.page_views": interaction},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_field_interaction(self, session_id, action, field_name=None, details=None):
        """Log field interactions (focus, blur, change, etc.)"""
        interaction = {
            "timestamp": datetime.now(),
            "type": "field_interaction",
            "action": action,
            "field_name": field_name,
            "details": details
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interactions.field_interactions": 1},
                "$push": {"interactions.field_interactions": interaction},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_click(self, session_id, element_id, element_type, details=None):
        """Log button clicks and other click events"""
        interaction = {
            "timestamp": datetime.now(),
            "type": "click",
            "element_id": element_id,
            "element_type": element_type,
            "details": details
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interactions.clicks": 1},
                "$push": {"interactions.clicks": interaction},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_error(self, session_id, error_type, error_details, stack_trace=None):
        """Log form errors and validation failures"""
        interaction = {
            "timestamp": datetime.now(),
            "type": "error",
            "error_type": error_type,
            "error_details": error_details,
            "stack_trace": stack_trace
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interactions.errors": 1},
                "$push": {"interactions.errors": interaction},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_time_spent(self, session_id, time_spent_seconds):
        """Log time spent on form"""
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interactions.time_spent": time_spent_seconds},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_signature(self, session_id, signature_data, signature_type="drawn"):
        """Log signature capture"""
        signature_info = {
            "timestamp": datetime.now(),
            "type": signature_type,
            "data": signature_data,
            "captured": True
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "signature_data": signature_info,
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def log_form_submission(self, session_id, approval_data, success=True):
        """Log form submission and approval"""
        submission_info = {
            "timestamp": datetime.now(),
            "success": success,
            "approval_data": approval_data,
            "submitted": True
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "approval_data": submission_info,
                    "status": "completed" if success else "failed",
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                },
                "$inc": {"interactions.submissions": 1}
            }
        )
        return result
    
    def log_page_exit(self, session_id, time_spent, final_stats):
        """Log when user leaves the form page"""
        exit_info = {
            "timestamp": datetime.now(),
            "type": "page_exit",
            "time_spent": time_spent,
            "final_stats": final_stats
        }
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"interactions.page_exits": exit_info},
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def get_session_by_id(self, session_id):
        """Get form session by session ID"""
        doc = self.collection.find_one({"session_id": session_id})
        if doc and '_id' in doc:
            doc['_id'] = str(doc['_id'])
        return doc
    
    def get_sessions_by_quote_id(self, quote_id):
        """Get all form sessions for a specific quote"""
        cursor = self.collection.find({"quote_id": quote_id})
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
    
    def get_all_sessions(self, limit=100):
        """Get all form tracking sessions"""
        cursor = self.collection.find({}).sort("created_at", -1).limit(limit)
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
    
    def get_tracking_stats(self):
        """Get form tracking statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "avg_time_spent": {"$avg": "$interactions.time_spent"},
                    "avg_field_interactions": {"$avg": "$interactions.field_interactions"},
                    "avg_page_views": {"$avg": "$interactions.page_views"},
                    "total_errors": {"$sum": "$interactions.errors"},
                    "total_submissions": {"$sum": "$interactions.submissions"}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def get_client_engagement_stats(self, client_email):
        """Get engagement statistics for a specific client"""
        pipeline = [
            {
                "$match": {
                    "client_data.email": client_email
                }
            },
            {
                "$group": {
                    "_id": "$client_data.email",
                    "total_sessions": {"$sum": 1},
                    "total_time_spent": {"$sum": "$interactions.time_spent"},
                    "total_interactions": {"$sum": "$interactions.field_interactions"},
                    "total_submissions": {"$sum": "$interactions.submissions"},
                    "last_activity": {"$max": "$last_activity"}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def update_session_status(self, session_id, new_status):
        """Update form session status"""
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now()
                }
            }
        )
        return result
    
    def _generate_session_id(self):
        """Generate unique session ID"""
        import uuid
        return str(uuid.uuid4())[:12].upper()
    
    def _validate_session_data(self, data):
        """Validate session data before saving"""
        required_fields = ["quote_id", "client_data", "form_type"]
        return all(field in data for field in required_fields)
