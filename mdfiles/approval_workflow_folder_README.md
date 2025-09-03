# Approval Workflow Files

This folder contains all the HTML templates and related files for the approval workflow system.

## Files:

### 1. `approval-dashboard.html`
- **Purpose**: Main dashboard for managers to view and approve quotes
- **Route**: `/approval-dashboard`
- **Features**: 
  - View pending quotes
  - Approve/reject quotes
  - Manager approval workflow

### 2. `ceo-signature.html`
- **Purpose**: CEO signature page for agreements
- **Route**: `/sign-ceo/<agreement_id>`
- **Features**:
  - CEO signature capture
  - Agreement review
  - Digital signature workflow

### 3. `client-signature.html`
- **Purpose**: Client signature page for agreements
- **Route**: `/sign-agreement/<agreement_id>`
- **Features**:
  - Client signature capture
  - Agreement review
  - Digital signature workflow

### 4. `client-feedback.html`
- **Purpose**: Client feedback form for document review
- **Route**: `/client-feedback`
- **Features**:
  - Document feedback collection
  - Client review workflow
  - Feedback submission

## Workflow Process:

1. **Manager Approval**: `approval-dashboard.html` → Manager reviews and approves quotes
2. **CEO Signature**: `ceo-signature.html` → CEO signs the agreement
3. **Client Signature**: `client-signature.html` → Client signs the agreement
4. **Client Feedback**: `client-feedback.html` → Client provides feedback on documents

## Integration:

All files are integrated with the main Flask application (`app.py`) and use the same:
- Database connections (MongoDB)
- Email services
- PDF generation
- Signature capture system

## Dependencies:

- Flask (for routing)
- MongoDB (for data storage)
- SignaturePad.js (for signature capture)
- Email service (for notifications)
- PDF generation (ReportLab/WeasyPrint)
