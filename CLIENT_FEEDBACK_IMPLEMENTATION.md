# Client Feedback Implementation

## Overview

This document describes the implementation of the client feedback feature that allows clients to provide feedback on approved documents after they receive them via email.

## Feature Description

The client feedback system enables clients to:
- **Accept** - Document is approved and ready to proceed
- **Reject** - Document needs significant changes  
- **Request Changes** - Minor modifications needed

## Workflow Changes

### 1. Approval Workflow Updates

The approval workflow now includes a **Client Review** stage:

```
Manager Approves → CEO Approves → Client Review → Final Status
```

- **Before**: CEO approval → Workflow completed
- **After**: CEO approval → Workflow enters "client_review" status → Client provides feedback → Final status determined

### 2. Database Schema Updates

New fields added to the approval workflow collection:

```python
# New workflow statuses
"workflow_status": "client_review"  # Instead of "completed"
"current_stage": "client"
"client_status": "pending_feedback"

# New client feedback fields
"client_comments": "Client's feedback text"
"client_decision": "accepted|rejected|needs_changes"
"client_feedback_date": "Timestamp of feedback"
"final_status": "pending_client_feedback|accepted_by_client|rejected_by_client|client_requested_changes"
```

## API Endpoints

### 1. Submit Client Feedback
```
POST /api/client/feedback
```

**Request Body:**
```json
{
    "workflow_id": "workflow_id_here",
    "client_email": "client@example.com",
    "decision": "accepted|rejected|needs_changes",
    "comments": "Optional feedback text"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Client feedback submitted successfully"
}
```

### 2. Get Client Workflow Details
```
GET /api/client/workflow/<workflow_id>?email=<client_email>
```

**Response:**
```json
{
    "success": true,
    "workflow": {
        "workflow_id": "id",
        "document_type": "PDF|Agreement",
        "client_name": "Client Name",
        "company_name": "Company Name",
        "document": {
            "filename": "document.pdf",
            "file_path": "/path/to/file"
        }
    }
}
```

### 3. Get Client Feedback Workflows (Admin)
```
GET /api/client/feedback-workflows
```

**Response:**
```json
{
    "success": true,
    "workflows": [
        {
            "workflow_id": "id",
            "document_type": "PDF",
            "client_name": "Client Name",
            "client_email": "client@example.com",
            "status": "Awaiting Client Feedback"
        }
    ]
}
```

### 4. Client Feedback Form
```
GET /client-feedback?workflow=<workflow_id>&email=<client_email>
```

Serves the HTML form for clients to submit feedback.

## Email Integration

### 1. Client Delivery Email Updates

The client delivery email now includes:
- **Feedback Section**: Instructions and link to feedback form
- **Decision Options**: Clear explanation of accept/reject/change options
- **Feedback Form Link**: Direct link to submit feedback

### 2. Client Feedback Notification Emails

When clients submit feedback, notification emails are sent to:
- **Manager**: About client's decision and comments
- **CEO**: About client's decision and comments

**Email Subjects:**
- ✅ CLIENT ACCEPTED: [Document] - [Company]
- ❌ CLIENT REJECTED: [Document] - [Company]  
- 🔄 CLIENT REQUESTS CHANGES: [Document] - [Company]

## Frontend Implementation

### 1. Client Feedback Form (`/client-feedback`)

**Features:**
- Document information display
- Decision selection (Accept/Reject/Request Changes)
- Comments textarea
- Email verification
- Responsive design

**URL Parameters:**
- `workflow`: Workflow ID
- `email`: Client email for verification

### 2. Approval Dashboard Updates

**New Section**: "👥 Client Feedback"
- Shows workflows awaiting client feedback
- Displays client information and document details
- Provides view actions for documents

**Navigation**: Added "Client Feedback" button with badge showing count

## Database Methods

### New Methods in `ApprovalWorkflowCollection`

```python
def submit_client_feedback(self, workflow_id, client_comments, client_decision):
    """Submit client feedback and update workflow status"""
    
def get_client_feedback_workflows(self, limit=100):
    """Get workflows waiting for client feedback"""
    
def get_workflow_by_client_email(self, client_email, workflow_id):
    """Verify client access to workflow"""
```

## Security Features

### 1. Client Verification
- Clients must provide their email address
- Email must match the workflow's client_email field
- Prevents unauthorized access to other clients' documents

### 2. Workflow State Validation
- Only workflows in "client_review" status accept feedback
- Prevents feedback on incomplete or already processed workflows

## Testing

### Test Script
Run `test_client_feedback.py` to test all endpoints:

```bash
python test_client_feedback.py
```

### Manual Testing Steps
1. Start approval workflow with client email
2. Have manager approve
3. Have CEO approve  
4. Check client receives email with feedback form link
5. Submit feedback through form
6. Verify manager/CEO receive notification emails
7. Check workflow status updates

## Configuration

### Environment Variables
```bash
APP_BASE_URL=http://localhost:5000  # For email links
```

### Company Configuration
The system uses `company_config.py` for:
- Company branding in emails
- Support contact information
- Document review instructions

## Error Handling

### Common Error Scenarios
1. **Invalid Workflow ID**: 404 Not Found
2. **Unauthorized Access**: 404 Not Found (security through obscurity)
3. **Missing Parameters**: 400 Bad Request
4. **Invalid Decision**: 400 Bad Request
5. **Workflow Not in Client Review**: 400 Bad Request

### Error Messages
- Clear, user-friendly error messages
- Detailed logging for debugging
- Graceful fallbacks for email failures

## Future Enhancements

### Potential Improvements
1. **Client Dashboard**: Dedicated client portal
2. **Feedback History**: Track client feedback over time
3. **Automated Follow-ups**: Reminder emails for pending feedback
4. **Feedback Analytics**: Track acceptance/rejection rates
5. **Document Versioning**: Handle multiple revision cycles

## Troubleshooting

### Common Issues
1. **Client can't access feedback form**
   - Check workflow status is "client_review"
   - Verify client email matches workflow
   - Check URL parameters are correct

2. **Feedback not being submitted**
   - Verify all required fields are filled
   - Check workflow exists and is accessible
   - Review server logs for errors

3. **Notification emails not sent**
   - Check SMTP configuration
   - Verify manager/CEO emails in workflow
   - Review email service logs

## Conclusion

The client feedback system provides a complete workflow for client document review and feedback, enhancing the approval process with client input while maintaining security and providing clear communication channels for all stakeholders.
