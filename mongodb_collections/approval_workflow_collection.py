from datetime import datetime
from bson import ObjectId
from cpq.db import db

class ApprovalWorkflowCollection:
    """Handles approval workflow MongoDB operations"""
    
    def __init__(self):
        self.collection = db["approval_workflows"]
    
    def create_workflow(self, workflow_data):
        """Create a new approval workflow"""
        workflow_data["created_at"] = datetime.now()
        workflow_data["updated_at"] = datetime.now()
        workflow_data["workflow_status"] = "active"
        
        # Set initial statuses
        workflow_data["manager_status"] = "pending"
        workflow_data["ceo_status"] = "pending"
        workflow_data["client_status"] = "pending"
        
        return self.collection.insert_one(workflow_data)
    
    def get_workflow_by_id(self, workflow_id):
        """Get workflow by MongoDB ObjectId"""
        try:
            return self.collection.find_one({"_id": ObjectId(workflow_id)})
        except:
            return None
    
    def get_workflows_by_document_id(self, document_id):
        """Get workflows by document ID"""
        return list(self.collection.find({"document_id": document_id}))
    
    def get_pending_workflows(self, limit=100):
        """Get all pending workflows"""
        return list(self.collection.find({
            "workflow_status": "active",
            "$or": [
                {"manager_status": "pending"},
                {"ceo_status": "pending"}
            ]
        }).sort("created_at", -1).limit(limit))
    
    def get_my_approval_queue(self, user_role, user_email, limit=100):
        """Get approval queue for specific user role"""
        if user_role == "manager":
            return list(self.collection.find({
                "workflow_status": "active",
                "manager_status": "pending"
            }).sort("created_at", -1).limit(limit))
        elif user_role == "ceo":
            return list(self.collection.find({
                "workflow_status": "active",
                "manager_status": "approved",
                "ceo_status": "pending"
            }).sort("created_at", -1).limit(limit))
        else:
            return []
    
    def get_workflow_status(self, limit=100):
        """Get all active workflows with status"""
        return list(self.collection.find({
            "workflow_status": "active"
        }).sort("created_at", -1).limit(limit))
    
    def get_approval_history(self, limit=100):
        """Get completed approval history"""
        return list(self.collection.find({
            "workflow_status": {"$in": ["completed", "cancelled"]}
        }).sort("updated_at", -1).limit(limit))
    
    def update_workflow_status(self, workflow_id, role, action, comments):
        """Update workflow status based on role and action"""
        try:
            # Normalize action values to consistent statuses
            normalized_action = {
                "approve": "approved",
                "deny": "denied",
                "approved": "approved",
                "denied": "denied"
            }.get(action, action)

            update_data = {
                "updated_at": datetime.now()
            }
            
            if role == "manager":
                update_data["manager_status"] = normalized_action
                update_data["manager_comments"] = comments
                update_data["manager_approval_date"] = datetime.now()
                
                if normalized_action == "denied":
                    update_data["workflow_status"] = "cancelled"
                    update_data["final_status"] = "denied_by_manager"
                elif normalized_action == "approved":
                    # Advance to CEO stage when manager approves
                    update_data["current_stage"] = "ceo"
                    
            elif role == "ceo":
                update_data["ceo_status"] = normalized_action
                update_data["ceo_comments"] = comments
                update_data["ceo_approval_date"] = datetime.now()
                
                if normalized_action == "approved":
                    update_data["workflow_status"] = "completed"
                    update_data["client_status"] = "delivered"
                    update_data["final_status"] = "approved"
                    update_data["completed_at"] = datetime.now()
                elif normalized_action == "denied":
                    update_data["workflow_status"] = "cancelled"
                    update_data["final_status"] = "denied_by_ceo"
            
            result = self.collection.update_one(
                {"_id": ObjectId(workflow_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error updating workflow status: {e}")
            return False
    
    def get_workflow_stats(self):
        """Get workflow statistics"""
        try:
            # Count pending approvals
            pending_count = self.collection.count_documents({
                "workflow_status": "active",
                "$or": [
                    {"manager_status": "pending"},
                    {"ceo_status": "pending"}
                ]
            })
            
            # Count completed today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            completed_today = self.collection.count_documents({
                "workflow_status": "completed",
                "completed_at": {"$gte": today}
            })
            
            # Calculate average approval time
            pipeline = [
                {
                    "$match": {
                        "workflow_status": "completed",
                        "completed_at": {"$exists": True},
                        "created_at": {"$exists": True}
                    }
                },
                {
                    "$addFields": {
                        "approval_time": {
                            "$divide": [
                                {"$subtract": ["$completed_at", "$created_at"]},
                                1000 * 60 * 60  # Convert to hours
                            ]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_time": {"$avg": "$approval_time"}
                    }
                }
            ]
            
            avg_time_result = list(self.collection.aggregate(pipeline))
            avg_time = avg_time_result[0]["avg_time"] if avg_time_result else 0
            
            return {
                "pending": pending_count,
                "completed_today": completed_today,
                "avg_approval_time": f"{avg_time:.1f}h"
            }
            
        except Exception as e:
            print(f"Error getting workflow stats: {e}")
            return {
                "pending": 0,
                "completed_today": 0,
                "avg_approval_time": "0h"
            }
    
    def cancel_workflow(self, workflow_id, reason):
        """Cancel a workflow"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(workflow_id)},
                {
                    "$set": {
                        "workflow_status": "cancelled",
                        "cancelled_at": datetime.now(),
                        "cancellation_reason": reason,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error cancelling workflow: {e}")
            return False
    
    def get_workflows_by_client(self, client_email, limit=50):
        """Get workflows for a specific client"""
        return list(self.collection.find({
            "client_email": client_email
        }).sort("created_at", -1).limit(limit))
    
    def search_workflows(self, search_term, limit=50):
        """Search workflows by document name, client name, or company"""
        search_query = {
            "$or": [
                {"document_name": {"$regex": search_term, "$options": "i"}},
                {"client_name": {"$regex": search_term, "$options": "i"}},
                {"company_name": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        return list(self.collection.find(search_query).sort("created_at", -1).limit(limit))
