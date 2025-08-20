from datetime import datetime
from bson import ObjectId
from cpq.db import db

class EmailCollection:
    """Handles email-related MongoDB operations"""
    
    def __init__(self):
        self.collection = db["email_logs"]
    
    def log_email_sent(self, email_data):
        """Log successful email sending"""
        email_data["sent_at"] = datetime.now()
        email_data["status"] = "sent"
        return self.collection.insert_one(email_data)
    
    def log_email_failed(self, email_data, error_message):
        """Log failed email sending"""
        email_data["sent_at"] = datetime.now()
        email_data["status"] = "failed"
        email_data["error"] = error_message
        return self.collection.insert_one(email_data)
    
    def get_email_history(self, recipient_email=None, limit=50):
        """Get email sending history"""
        filter_query = {}
        if recipient_email:
            filter_query["recipient_email"] = recipient_email
        
        return list(self.collection.find(filter_query).sort("sent_at", -1).limit(limit))
    
    def get_email_by_id(self, email_id):
        """Get email log by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(email_id)})
        except:
            return None
    
    def update_email_status(self, email_id, new_status, notes=""):
        """Update email status"""
        update_data = {
            "status": new_status,
            "updated_at": datetime.now()
        }
        if notes:
            update_data["notes"] = notes
        
        return self.collection.update_one(
            {"_id": ObjectId(email_id)},
            {"$set": update_data}
        )
    
    def get_email_stats(self):
        """Get email sending statistics"""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def send_email(self, to_email, subject, body):
        """Send email using the email service"""
        try:
            from cpq.email_service import EmailService
            
            email_service = EmailService()
            result = email_service.send_email(to_email, subject, body)
            
            # Log the email attempt
            if result.get('success'):
                self.log_email_sent({
                    "to_email": to_email,
                    "subject": subject,
                    "body": body,
                    "sent_at": datetime.now()
                })
            else:
                self.log_email_failed({
                    "to_email": to_email,
                    "subject": subject,
                    "body": body,
                    "sent_at": datetime.now()
                }, result.get('message', 'Unknown error'))
            
            return result
            
        except Exception as e:
            # Log the error
            self.log_email_failed({
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "sent_at": datetime.now()
            }, str(e))
            
            return {
                "success": False,
                "message": f"Email sending failed: {str(e)}"
            }
