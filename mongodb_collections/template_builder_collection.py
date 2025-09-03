from datetime import datetime
from bson import ObjectId
import json
from cpq.db import db

class TemplateBuilderCollection:
    def __init__(self):
        # Use a separate collection for template builder documents
        self.collection = db["template_builder_documents"]
    
    def save_document(self, document_data):
        """Save a template builder document"""
        try:
            # Check if document already exists (by id)
            existing_doc = None
            if 'id' in document_data:
                existing_doc = self.collection.find_one({'id': document_data['id']})
            
            if existing_doc:
                # Update existing document
                update_data = {
                    'title': document_data['title'],
                    'updated': datetime.now(),
                    'blocks': document_data['blocks'],
                    'metadata': document_data['metadata']
                }
                
                result = self.collection.update_one(
                    {'id': document_data['id']},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    return {
                        'success': True,
                        'id': document_data['id'],
                        'action': 'updated',
                        'message': 'Document updated successfully'
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Failed to update document'
                    }
            else:
                # Create new document
                document = {
                    'id': document_data['id'],
                    'title': document_data['title'],
                    'created': datetime.now(),
                    'updated': datetime.now(),
                    'blocks': document_data['blocks'],
                    'metadata': document_data['metadata'],
                    'is_active': True
                }
                
                result = self.collection.insert_one(document)
                
                return {
                    'success': True,
                    'id': document_data['id'],
                    'action': 'created',
                    'message': 'Document saved successfully'
                }
                
        except Exception as e:
            print(f"Error saving document: {str(e)}")
            return {
                'success': False,
                'message': f'Error saving document: {str(e)}'
            }
    
    def get_document_by_id(self, document_id):
        """Get document by ID"""
        try:
            document = self.collection.find_one({'id': document_id, 'is_active': True})
            if document:
                # Convert datetime objects to ISO strings
                document['created'] = document['created'].isoformat()
                document['updated'] = document['updated'].isoformat()
                # Remove MongoDB _id field
                document.pop('_id', None)
            return document
        except Exception as e:
            print(f"Error getting document: {str(e)}")
            return None
    
    def get_all_documents(self):
        """Get all active documents"""
        try:
            documents = list(self.collection.find({'is_active': True}).sort('updated', -1))
            
            # Convert datetime objects and remove _id
            for doc in documents:
                doc['created'] = doc['created'].isoformat()
                doc['updated'] = doc['updated'].isoformat()
                doc.pop('_id', None)
            
            return documents
        except Exception as e:
            print(f"Error getting documents: {str(e)}")
            return []
    
    def delete_document(self, document_id):
        """Soft delete a document"""
        try:
            result = self.collection.update_one(
                {'id': document_id},
                {'$set': {'is_active': False, 'updated': datetime.now()}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            return False
    
    def search_documents(self, search_term):
        """Search documents by title or content"""
        try:
            from bson.regex import Regex
            
            search_regex = Regex(search_term, 'i')
            documents = list(self.collection.find({
                '$or': [
                    {'title': search_regex},
                    {'metadata.totalBlocks': {'$regex': search_term}}
                ],
                'is_active': True
            }).sort('updated', -1))
            
            # Convert datetime objects and remove _id
            for doc in documents:
                doc['created'] = doc['created'].isoformat()
                doc['updated'] = doc['updated'].isoformat()
                doc.pop('_id', None)
            
            return documents
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            return []
    
    def get_document_stats(self):
        """Get statistics about documents"""
        try:
            total_docs = self.collection.count_documents({'is_active': True})
            
            # Get documents with different block types
            docs_with_images = self.collection.count_documents({
                'is_active': True,
                'metadata.hasImages': True
            })
            
            docs_with_signatures = self.collection.count_documents({
                'is_active': True,
                'metadata.hasSignatures': True
            })
            
            docs_with_pricing = self.collection.count_documents({
                'is_active': True,
                'metadata.hasPricing': True
            })
            
            return {
                'total_documents': total_docs,
                'documents_with_images': docs_with_images,
                'documents_with_signatures': docs_with_signatures,
                'documents_with_pricing': docs_with_pricing
            }
        except Exception as e:
            print(f"Error getting document stats: {str(e)}")
            return {
                'total_documents': 0,
                'documents_with_images': 0,
                'documents_with_signatures': 0,
                'documents_with_pricing': 0
            }
