from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class TemplateCollection:
    def __init__(self):
        # Get MongoDB connection string from environment
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.client = MongoClient(mongo_uri)
        self.db = self.client['hubspot_cpq']
        self.collection = self.db['templates']
        
        # Create indexes for better performance
        self.collection.create_index([('name', 1)])
        self.collection.create_index([('type', 1)])
        self.collection.create_index([('created_at', -1)])
    
    def save_template(self, template_data):
        """Save a new template to MongoDB"""
        try:
            # Ensure required fields
            if not template_data.get('name') or not template_data.get('type') or not template_data.get('content'):
                raise ValueError("Missing required template fields")
            
            # Add timestamps if not present
            if 'created_at' not in template_data:
                template_data['created_at'] = datetime.utcnow()
            if 'updated_at' not in template_data:
                template_data['updated_at'] = datetime.utcnow()
            
            # Insert template
            result = self.collection.insert_one(template_data)
            return result.inserted_id
            
        except Exception as e:
            print(f"Error saving template: {e}")
            raise e
    
    def get_all_templates(self, limit=100):
        """Get all templates from MongoDB"""
        try:
            templates = list(self.collection.find().sort('created_at', -1).limit(limit))
            return templates
            
        except Exception as e:
            print(f"Error fetching templates: {e}")
            return []
    
    def get_template_by_id(self, template_id):
        """Get a specific template by ID"""
        try:
            if not ObjectId.is_valid(template_id):
                return None
            
            template = self.collection.find_one({'_id': ObjectId(template_id)})
            return template
            
        except Exception as e:
            print(f"Error fetching template by ID: {e}")
            return None
    
    def get_templates_by_type(self, template_type, limit=50):
        """Get templates by type (email, pdf, quote)"""
        try:
            templates = list(self.collection.find({'type': template_type}).sort('created_at', -1).limit(limit))
            return templates
            
        except Exception as e:
            print(f"Error fetching templates by type: {e}")
            return []
    
    def search_templates(self, search_term, limit=50):
        """Search templates by name or content"""
        try:
            # Create text search query
            query = {
                '$or': [
                    {'name': {'$regex': search_term, '$options': 'i'}},
                    {'content': {'$regex': search_term, '$options': 'i'}},
                    {'description': {'$regex': search_term, '$options': 'i'}}
                ]
            }
            
            templates = list(self.collection.find(query).sort('created_at', -1).limit(limit))
            return templates
            
        except Exception as e:
            print(f"Error searching templates: {e}")
            return []
    
    def update_template(self, template_id, update_data):
        """Update an existing template"""
        try:
            if not ObjectId.is_valid(template_id):
                return False
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            # Update template
            result = self.collection.update_one(
                {'_id': ObjectId(template_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error updating template: {e}")
            return False
    
    def delete_template(self, template_id):
        """Delete a template by ID"""
        try:
            if not ObjectId.is_valid(template_id):
                return False
            
            result = self.collection.delete_one({'_id': ObjectId(template_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Error deleting template: {e}")
            return False
    
    def get_template_stats(self):
        """Get template statistics"""
        try:
            total = self.collection.count_documents({})
            email_count = self.collection.count_documents({'type': 'email'})
            pdf_count = self.collection.count_documents({'type': 'pdf'})
            quote_count = self.collection.count_documents({'type': 'quote'})
            
            return {
                'total': total,
                'email': email_count,
                'pdf': pdf_count,
                'quote': quote_count
            }
            
        except Exception as e:
            print(f"Error getting template stats: {e}")
            return {'total': 0, 'email': 0, 'pdf': 0, 'quote': 0}
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
