import os
from pathlib import Path

class FilePathHandler:
    """Handle file paths consistently across local and production environments"""
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.documents_dir = self._get_documents_directory()
    
    def _get_project_root(self):
        """Get the project root directory, handling both local and production paths"""
        current_dir = os.getcwd()
        
        # Check if we're in a production environment (Render, Heroku, etc.)
        if 'render' in current_dir.lower() or 'heroku' in current_dir.lower():
            # Production: look for the app.py file to determine project root
            app_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to the project root (where app.py is located)
            while app_dir != '/' and not os.path.exists(os.path.join(app_dir, 'app.py')):
                app_dir = os.path.dirname(app_dir)
            return app_dir if os.path.exists(os.path.join(app_dir, 'app.py')) else current_dir
        else:
            # Local development: use current working directory
            return current_dir
    
    def _get_documents_directory(self):
        """Get the documents directory path"""
        # Try multiple possible locations
        possible_paths = [
            os.path.join(self.project_root, 'documents'),
            os.path.join(os.getcwd(), 'documents'),
            'documents',
            '/tmp/documents',  # Fallback for production
            os.path.join(os.path.expanduser('~'), 'documents')  # User home directory
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no documents directory exists, create one in project root
        default_path = os.path.join(self.project_root, 'documents')
        try:
            os.makedirs(default_path, exist_ok=True)
            return default_path
        except Exception:
            # Last resort: use current directory
            return os.path.join(os.getcwd(), 'documents')
    
    def get_document_path(self, filename):
        """Get the full path to a document file"""
        return os.path.join(self.documents_dir, filename)
    
    def get_relative_path(self, filepath):
        """Convert absolute path to relative path for storage"""
        if os.path.isabs(filepath):
            # If it's an absolute path, make it relative to documents directory
            return os.path.basename(filepath)
        return filepath
    
    def ensure_documents_directory(self):
        """Ensure the documents directory exists"""
        os.makedirs(self.documents_dir, exist_ok=True)
        return self.documents_dir
    
    def list_documents(self):
        """List all files in the documents directory"""
        try:
            if os.path.exists(self.documents_dir):
                return [f for f in os.listdir(self.documents_dir) if os.path.isfile(os.path.join(self.documents_dir, f))]
            return []
        except Exception:
            return []
    
    def file_exists(self, filename):
        """Check if a file exists in the documents directory"""
        file_path = self.get_document_path(filename)
        return os.path.exists(file_path)
    
    def get_file_info(self, filename):
        """Get detailed information about a file"""
        file_path = self.get_document_path(filename)
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            return {
                'filename': filename,
                'file_path': file_path,
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'exists': True
            }
        return {
            'filename': filename,
            'file_path': file_path,
            'exists': False
        }

# Global instance for easy access
file_handler = FilePathHandler()
