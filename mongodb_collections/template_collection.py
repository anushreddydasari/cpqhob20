from datetime import datetime
from bson import ObjectId
import json
from cpq.db import db

class TemplateCollection:
    def __init__(self):
        # Reuse the shared MongoDB connection configured in cpq.db
        self.collection = db["agreement_templates"]
    
    def create_template(self, template_data):
        """Create a new agreement template"""
        try:
            template = {
                'name': template_data['name'],
                'description': template_data.get('description', ''),
                'content': template_data['content'],
                'placeholders': template_data.get('placeholders', []),
                'clauses': template_data.get('clauses', []),
                'category': template_data.get('category', 'general'),
                # html or pdf
                'type': template_data.get('type', 'html'),
                # file metadata for pdf templates
                'file_name': template_data.get('file_name'),
                'file_path': template_data.get('file_path'),
                'file_size': template_data.get('file_size'),
                'mime_type': template_data.get('mime_type'),
                'is_active': template_data.get('is_active', True),
                'version': 1,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'created_by': template_data.get('created_by', 'admin'),
                'tags': template_data.get('tags', [])
            }
            
            result = self.collection.insert_one(template)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating template: {str(e)}")
            return None
    
    def get_template_by_id(self, template_id):
        """Get template by ID"""
        try:
            if isinstance(template_id, str):
                template_id = ObjectId(template_id)
            return self.collection.find_one({'_id': template_id})
        except Exception as e:
            print(f"Error getting template: {str(e)}")
            return None
    
    def get_all_templates(self, active_only=True):
        """Get all templates, optionally only active ones"""
        try:
            filter_query = {}
            if active_only:
                filter_query['is_active'] = True
            
            templates = list(self.collection.find(filter_query).sort('updated_at', -1))
            
            # Convert ObjectIds to strings for JSON serialization
            for template in templates:
                template['_id'] = str(template['_id'])
                template['created_at'] = template['created_at'].isoformat()
                template['updated_at'] = template['updated_at'].isoformat()
            
            return templates
        except Exception as e:
            print(f"Error getting templates: {str(e)}")
            return []
    
    def update_template(self, template_id, update_data):
        """Update an existing template"""
        try:
            if isinstance(template_id, str):
                template_id = ObjectId(template_id)
            
            # Increment version
            current_template = self.collection.find_one({'_id': template_id})
            if current_template:
                new_version = current_template.get('version', 1) + 1
            else:
                new_version = 1
            
            update_data['version'] = new_version
            update_data['updated_at'] = datetime.now()
            
            result = self.collection.update_one(
                {'_id': template_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating template: {str(e)}")
            return False
    
    def delete_template(self, template_id):
        """Soft delete a template (mark as inactive)"""
        try:
            if isinstance(template_id, str):
                template_id = ObjectId(template_id)
            
            result = self.collection.update_one(
                {'_id': template_id},
                {'$set': {'is_active': False, 'updated_at': datetime.now()}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deleting template: {str(e)}")
            return False
    
    def get_templates_by_category(self, category):
        """Get templates by category"""
        try:
            templates = list(self.collection.find({
                'category': category,
                'is_active': True
            }).sort('updated_at', -1))
            
            # Convert ObjectIds to strings
            for template in templates:
                template['_id'] = str(template['_id'])
                template['created_at'] = template['created_at'].isoformat()
                template['updated_at'] = template['updated_at'].isoformat()
            
            return templates
        except Exception as e:
            print(f"Error getting templates by category: {str(e)}")
            return []
    
    def search_templates(self, search_term):
        """Search templates by name, description, or content"""
        try:
            from bson.regex import Regex
            
            search_regex = Regex(search_term, 'i')
            templates = list(self.collection.find({
                '$or': [
                    {'name': search_regex},
                    {'description': search_regex},
                    {'content': search_regex}
                ],
                'is_active': True
            }).sort('updated_at', -1))
            
            # Convert ObjectIds to strings
            for template in templates:
                template['_id'] = str(template['_id'])
                template['created_at'] = template['created_at'].isoformat()
                template['updated_at'] = template['updated_at'].isoformat()
            
            return templates
        except Exception as e:
            print(f"Error searching templates: {str(e)}")
            return []
    
    def create_template_version(self, template_id, new_content, user_id='admin'):
        """Create a new version of an existing template"""
        try:
            if isinstance(template_id, str):
                template_id = ObjectId(template_id)
            
            # Get current template
            current_template = self.collection.find_one({'_id': template_id})
            if not current_template:
                return None
            
            # Create new version
            new_version = {
                'name': current_template['name'],
                'description': current_template.get('description', ''),
                'content': new_content,
                'placeholders': current_template.get('placeholders', []),
                'clauses': current_template.get('clauses', []),
                'category': current_template.get('category', 'general'),
                'is_active': True,
                'version': current_template.get('version', 1) + 1,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'created_by': user_id,
                'tags': current_template.get('tags', []),
                'parent_template_id': template_id
            }
            
            result = self.collection.insert_one(new_version)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating template version: {str(e)}")
            return None
