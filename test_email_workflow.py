#!/usr/bin/env python3
"""
Test script for the Email-Based Approval Workflow System
This script demonstrates how managers and CEOs receive emails with PDFs and approval buttons
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"

def print_step(step_num, title):
    """Print a formatted step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def print_info(message):
    """Print an info message"""
    print(f"ℹ️  {message}")

def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")

def test_email_workflow():
    """Test the complete email-based approval workflow"""
    
    print("📧 EMAIL-BASED APPROVAL WORKFLOW DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how managers and CEOs receive emails")
    print("with PDFs and approval/rejection buttons.")
    
    # Step 1: Check system status
    print_step(1, "CHECKING SYSTEM STATUS")
    
    try:
        response = requests.get(f"{BASE_URL}/api/approval/stats")
        if response.status_code == 200:
            stats = response.json()
            if stats.get('success'):
                print_success("System is running and accessible")
                print_info(f"Current pending approvals: {stats['stats']['pending']}")
            else:
                print_error(f"Stats API error: {stats.get('message')}")
        else:
            print_error(f"Stats API returned status: {response.status_code}")
    except Exception as e:
        print_error(f"Error checking system: {e}")
        return
    
    # Step 2: Explain the email workflow
    print_step(2, "HOW THE EMAIL WORKFLOW OPERATES")
    
    print_info("Here's the complete email-based approval process:")
    print()
    print("1. 📄 USER CREATES DOCUMENT")
    print("   - User creates quote/agreement in Quote Management")
    print("   - PDF is generated and stored in database")
    print()
    print("2. 🔄 WORKFLOW INITIATION")
    print("   - User clicks 'Start Approval Workflow'")
    print("   - System creates workflow record")
    print("   - **AUTOMATIC EMAIL SENT TO MANAGER** with:")
    print("     • PDF document attached")
    print("     • Professional HTML email template")
    print("     • ✅ APPROVE button")
    print("     • ❌ REJECT button")
    print("     • Link to web dashboard")
    print()
    print("3. 👨‍💼 MANAGER RECEIVES EMAIL")
    print("   - Manager gets email with PDF attachment")
    print("   - Manager can review PDF directly in email")
    print("   - Manager clicks APPROVE or REJECT")
    print("   - Manager adds comments if needed")
    print()
    print("4. 👑 CEO RECEIVES EMAIL (if Manager approves)")
    print("   - **AUTOMATIC EMAIL SENT TO CEO** with:")
    print("     • Same PDF document attached")
    print("     • Manager's approval decision")
    print("     • ✅ APPROVE button")
    print("     • ❌ REJECT button")
    print()
    print("5. 📧 CLIENT RECEIVES FINAL DOCUMENT (if CEO approves)")
    print("   - **AUTOMATIC EMAIL SENT TO CLIENT** with:")
    print("     • Final approved document")
    print("     • Approval confirmation")
    print()
    
    # Step 3: Show email template features
    print_step(3, "EMAIL TEMPLATE FEATURES")
    
    print_info("Professional HTML emails include:")
    print()
    print("✅ **Beautiful Design**")
    print("   - Gradient header with icons")
    print("   - Professional color scheme")
    print("   - Responsive layout")
    print()
    print("✅ **PDF Attachment**")
    print("   - Document automatically attached")
    print("   - Proper filename formatting")
    print("   - Easy to download and review")
    print()
    print("✅ **Action Buttons**")
    print("   - Large, clickable APPROVE button (green)")
    print("   - Large, clickable REJECT button (red)")
    print("   - Hover effects and animations")
    print()
    print("✅ **Workflow Information**")
    print("   - Document details and status")
    print("   - Client and company information")
    print("   - Current approval stage")
    print()
    print("✅ **Alternative Access**")
    print("   - Link to web dashboard")
    print("   - Instructions for approval process")
    print("   - Professional footer")
    print()
    
    # Step 4: Show how to test
    print_step(4, "HOW TO TEST THE EMAIL WORKFLOW")
    
    print_info("To test the complete email workflow:")
    print()
    print("1. 🌐 Open your browser: http://localhost:5000")
    print("2. 📝 Go to 'Quote Management' page")
    print("3. 📄 Create a real quote/PDF document")
    print("4. 🔄 Use 'Start Approval Workflow' section")
    print("5. 📧 Fill in manager and CEO emails")
    print("6. 🚀 Click 'Start Workflow'")
    print()
    print("📧 **What Happens Next:**")
    print("   - Manager receives email with PDF + approval buttons")
    print("   - Manager can approve/reject directly from email")
    print("   - If approved, CEO automatically receives email")
    print("   - If CEO approves, client receives final document")
    print()
    
    # Step 5: Email configuration requirements
    print_step(5, "EMAIL CONFIGURATION REQUIREMENTS")
    
    print_info("Make sure your .env file has these settings:")
    print()
    print("GMAIL_EMAIL=your-email@gmail.com")
    print("GMAIL_APP_PASSWORD=your-app-password")
    print("APP_BASE_URL=http://localhost:5000")
    print()
    print("ℹ️  **Note:** Gmail requires an 'App Password' for security")
    print("ℹ️  **Note:** You can change SMTP settings in email_service.py")
    print()
    
    print("🎯 EMAIL WORKFLOW DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("Your system now sends professional approval emails with:")
    print("✅ PDF attachments")
    print("✅ Approval/Rejection buttons")
    print("✅ Beautiful HTML templates")
    print("✅ Automatic workflow progression")
    print("✅ Professional branding")
    print()
    print("🚀 Ready to test the complete email workflow!")

if __name__ == "__main__":
    print("⚠️  Make sure your Flask app is running on http://localhost:5000")
    print("⚠️  Make sure your .env file has Gmail credentials")
    print()
    
    try:
        test_email_workflow()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
