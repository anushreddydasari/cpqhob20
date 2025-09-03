from datetime import datetime
from bson import ObjectId
import json
from cpq.db import db

class SignatureCertificateCollection:
    """Handles signature certificate MongoDB operations"""
    
    def __init__(self):
        self.collection = db["signature_certificates"]
    
    def create_certificate(self, certificate_data):
        """Create a new signature certificate record"""
        certificate_doc = {
            "agreement_id": certificate_data.get("agreement_id"),
            "reference_number": certificate_data.get("reference_number"),
            "document_title": certificate_data.get("document_title", "Purchase Agreement"),
            "signers": certificate_data.get("signers", []),
            "completion_date": certificate_data.get("completion_date"),
            "certificate_data": certificate_data.get("certificate_data", {}),
            "file_path": certificate_data.get("file_path"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_active": True
        }
        
        result = self.collection.insert_one(certificate_doc)
        return str(result.inserted_id)
    
    def get_certificate_by_id(self, certificate_id):
        """Get certificate by ID"""
        doc = self.collection.find_one({"_id": ObjectId(certificate_id)})
        if doc and '_id' in doc:
            doc['_id'] = str(doc['_id'])
        return doc
    
    def get_certificate_by_agreement(self, agreement_id):
        """Get certificate by agreement ID"""
        doc = self.collection.find_one({"agreement_id": agreement_id, "is_active": True})
        if doc and '_id' in doc:
            doc['_id'] = str(doc['_id'])
        return doc
    
    def get_all_certificates(self):
        """Get all certificates"""
        cursor = self.collection.find({"is_active": True}).sort("created_at", -1)
        results = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        return results
    
    def update_certificate(self, certificate_id, updates):
        """Update certificate metadata"""
        updates['updated_at'] = datetime.now()
        result = self.collection.update_one(
            {"_id": ObjectId(certificate_id)},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def delete_certificate(self, certificate_id):
        """Soft delete certificate"""
        result = self.collection.update_one(
            {"_id": ObjectId(certificate_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
