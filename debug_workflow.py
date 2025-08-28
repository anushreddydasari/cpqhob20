#!/usr/bin/env python3
"""
Debug script to check workflow status and approval process
"""

from mongodb_collections import ApprovalWorkflowCollection
from datetime import datetime

def debug_workflow():
    print("🔍 Debugging Approval Workflow Status...")
    print("=" * 50)
    
    try:
        workflows = ApprovalWorkflowCollection()
        
        # Show CEO queue before any changes
        ceo_queue_before = workflows.get_my_approval_queue('ceo', 'ceo@company.com')
        print(f"👑 CEO Queue (before): {len(ceo_queue_before)} item(s)")
        
        # Get pending workflows
        pending_workflows = workflows.get_pending_workflows()
        print(f"📋 Pending Workflows Found: {len(pending_workflows)}")
        
        if pending_workflows:
            for i, workflow in enumerate(pending_workflows, 1):
                print(f"\n🔍 Workflow {i}:")
                print(f"  ID: {workflow.get('_id')}")
                print(f"  Document: {workflow.get('document_type')} - {workflow.get('document_id')}")
                print(f"  Client: {workflow.get('client_name')}")
                print(f"  Manager Status: {workflow.get('manager_status', 'N/A')}")
                print(f"  CEO Status: {workflow.get('ceo_status', 'N/A')}")
                print(f"  Client Status: {workflow.get('client_status', 'N/A')}")
                print(f"  Workflow Status: {workflow.get('workflow_status', 'N/A')}")
                print(f"  Created: {workflow.get('created_at', 'N/A')}")
                print(f"  Updated: {workflow.get('updated_at', 'N/A')}")
                
                # Check if there are any approval actions
                if 'approval_history' in workflow:
                    print(f"  Approval History: {len(workflow['approval_history'])} actions")
                    for action in workflow['approval_history']:
                        print(f"    - {action.get('action')} by {action.get('role')} at {action.get('timestamp')}")
                else:
                    print("  Approval History: None")
        
        else:
            print("❌ No pending workflows found")
        
        # Try to advance one manager-pending workflow to CEO stage
        print("\n🔄 Advancing one manager-pending workflow (if any) to CEO stage...")
        try:
            pending_manager = workflows.collection.find_one({
                "workflow_status": "active",
                "manager_status": "pending"
            })
            if pending_manager:
                wid = str(pending_manager.get("_id"))
                ok = workflows.update_workflow_status(wid, role="manager", action="approve", comments="Auto-approve for debug")
                print(f"   ➜ Manager approval on {wid}: {'OK' if ok else 'FAILED'}")
            else:
                print("   ➜ No manager-pending workflow to advance.")
        except Exception as e:
            print(f"   ⚠️ Could not auto-advance a workflow: {e}")
            
        # Show CEO queue after advancing
        ceo_queue_after = workflows.get_my_approval_queue('ceo', 'ceo@company.com')
        print(f"\n👑 CEO Queue (after): {len(ceo_queue_after)} item(s)")
        if ceo_queue_after:
            for i, wf in enumerate(ceo_queue_after, 1):
                print(f"   {i}. {wf.get('document_name','Document')} | client={wf.get('client_name','N/A')} | manager_status={wf.get('manager_status')} | ceo_status={wf.get('ceo_status')}")

        # Get workflow status
        print(f"\n📊 Workflow Status:")
        workflow_status = workflows.get_workflow_status()
        print(f"  Total Active Workflows: {len(workflow_status)}")
        
        # Get stats
        print(f"\n📈 Workflow Statistics:")
        stats = workflows.get_workflow_stats()
        print(f"  Pending: {stats['pending']}")
        print(f"  Completed Today: {stats['completed_today']}")
        print(f"  Average Approval Time: {stats['avg_approval_time']}")
            
    except Exception as e:
        print(f"❌ Error debugging workflow: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n💡 Possible Issues:")
    print("1. Approval API endpoint not working")
    print("2. Workflow update logic has error")
    print("3. Database connection issue")
    print("4. JavaScript approval function not calling API")
    print("5. Manager approval not updating database")

if __name__ == "__main__":
    debug_workflow()
