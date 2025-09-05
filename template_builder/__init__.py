from flask import Blueprint, jsonify, request
from mongodb_collections.template_builder_collection import TemplateBuilderCollection


template_builder_bp = Blueprint('template_builder', __name__, url_prefix='/api/template-builder')


@template_builder_bp.route('/save', methods=['POST'])
def save_template_builder_document():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        template_builder = TemplateBuilderCollection()
        result = template_builder.save_document(data)
        status = 200 if result.get('success') else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@template_builder_bp.route('/load/<document_id>', methods=['GET'])
def load_template_builder_document(document_id):
    try:
        template_builder = TemplateBuilderCollection()
        document = template_builder.get_document_by_id(document_id)
        if document:
            return jsonify({'success': True, 'document': document}), 200
        return jsonify({'success': False, 'message': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@template_builder_bp.route('/documents', methods=['GET'])
def get_all_template_builder_documents():
    try:
        template_builder = TemplateBuilderCollection()
        documents = template_builder.get_all_documents()
        return jsonify({'success': True, 'documents': documents, 'count': len(documents)}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@template_builder_bp.route('/delete/<document_id>', methods=['DELETE'])
def delete_template_builder_document(document_id):
    try:
        template_builder = TemplateBuilderCollection()
        success = template_builder.delete_document(document_id)
        if success:
            return jsonify({'success': True, 'message': 'Document deleted successfully'}), 200
        return jsonify({'success': False, 'message': 'Document not found or already deleted'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@template_builder_bp.route('/search', methods=['GET'])
def search_template_builder_documents():
    try:
        search_term = request.args.get('q', '')
        if not search_term:
            return jsonify({'success': False, 'message': 'Search term required'}), 400
        template_builder = TemplateBuilderCollection()
        documents = template_builder.search_documents(search_term)
        return jsonify({'success': True, 'documents': documents, 'count': len(documents), 'search_term': search_term}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@template_builder_bp.route('/stats', methods=['GET'])
def get_template_builder_stats():
    try:
        template_builder = TemplateBuilderCollection()
        stats = template_builder.get_document_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


