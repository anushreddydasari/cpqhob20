"""Google Docs integration utilities.

Prereqs:
- Enable Google Docs API and Drive API for your Google Cloud project
- Create OAuth2 credentials and save credentials JSON to env var or path
- Service account recommended for server-to-server; share docs with the SA email

This module provides minimal helpers to:
1) Create a Google Doc from HTML content
2) Replace placeholders like {{client_name}} with values
3) Export a Doc as PDF and return bytes

Note: For production, add token storage/refresh and robust error handling.
"""

from __future__ import annotations

import os
import base64
from typing import Dict, Optional

import json
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaInMemoryUpload
from io import BytesIO


SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
]


def _get_service(service_name: str, version: str):
    # Prefer path vars; fall back to inline JSON
    creds_path = (
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        or os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')
    )
    inline_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json')

    credentials = None
    # 1) Try OAuth user token first (best for personal Gmail)
    if os.path.exists(token_path):
        try:
            credentials = UserCredentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            credentials = None

    if inline_json:
        try:
            info = json.loads(inline_json)
            if not credentials:
                credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as exc:
            raise RuntimeError('Invalid GOOGLE_SERVICE_ACCOUNT_JSON content') from exc
    elif creds_path and os.path.exists(creds_path):
        if not credentials:
            credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        if not credentials:
            raise RuntimeError('Google credentials not configured. Provide OAuth token (token.json) via /oauth/login or set GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_SERVICE_ACCOUNT_KEY_PATH / GOOGLE_SERVICE_ACCOUNT_JSON.')
    return build(service_name, version, credentials=credentials, cache_discovery=False)


def _create_doc_via_drive(title: str, parent_folder_id: Optional[str] = None) -> str:
    """Create a Google Doc using Drive API (works better with shared folders).

    Returns: fileId / documentId
    """
    drive = _get_service('drive', 'v3')
    meta = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.document'
    }
    if parent_folder_id:
        meta['parents'] = [parent_folder_id]
    file = drive.files().create(body=meta, fields='id').execute()
    return file.get('id')


def create_doc_from_html(title: str, html_content: str) -> str:
    """Create a new Google Doc with basic HTML content (as body text).

    Google Docs API does not accept raw HTML; we insert as text for simplicity.
    For richer fidelity, convert HTML to Docs requests (out of scope here).
    Returns: documentId
    """
    docs = _get_service('docs', 'v1')
    # Create via Drive first (works best for SA + shared folders), fallback to Docs API
    try:
        parent = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        document_id = _create_doc_via_drive(title, parent)
    except Exception:
        body = {'title': title}
        doc = docs.documents().create(body=body).execute()
        document_id = doc.get('documentId')

    # Clear default content and insert our text
    requests = [
        {'deleteContentRange': {'range': {'segmentId': '', 'startIndex': 1, 'endIndex': 1_000_000}}},
        {'insertText': {'location': {'index': 1}, 'text': html_content}},
    ]
    docs.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
    return document_id


def replace_placeholders(document_id: str, values: Dict[str, str]) -> None:
    """Replace {{placeholder}} tokens with values throughout the doc."""
    docs = _get_service('docs', 'v1')
    requests = []
    for key, val in values.items():
        requests.append({
            'replaceAllText': {
                'containsText': {'text': f'{{{{{key}}}}}', 'matchCase': True},
                'replaceText': str(val),
            }
        })
    if requests:
        docs.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()


def export_doc_as_pdf(document_id: str) -> bytes:
    """Export a Google Doc as PDF via Drive API and return bytes."""
    drive = _get_service('drive', 'v3')
    request = drive.files().export(fileId=document_id, mimeType='application/pdf')
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fd=fh, request=request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()


def upsert_doc_from_template(title: str, html_content: str, placeholders: Dict[str, str]) -> str:
    """Create a Doc from HTML and replace placeholders; return documentId."""
    doc_id = create_doc_from_html(title, html_content)
    replace_placeholders(doc_id, placeholders)
    return doc_id
