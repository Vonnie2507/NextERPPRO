# Copyright (c) 2024, Probuild and contributors
# For license information, please see license.txt

"""
Add SMS Inbox shortcut to CRM workspace.
This patch ONLY ADDS new items - does NOT modify or delete existing items.
"""

import frappe


def execute():
    """Add SMS Inbox shortcut to CRM workspace safely."""
    
    # Get the CRM workspace
    if not frappe.db.exists("Workspace", "CRM"):
        return
    
    ws = frappe.get_doc("Workspace", "CRM")
    
    # Check if SMS Inbox shortcut already exists in shortcuts child table
    sms_exists = any(s.link_to == "SMS Log" for s in ws.shortcuts)
    
    if sms_exists:
        # Already exists, don't duplicate
        return
    
    # Add SMS Inbox to shortcuts child table (appears in "Your Shortcuts" section)
    ws.append("shortcuts", {
        "label": "SMS Inbox",
        "link_to": "SMS Log",
        "type": "DocType",
        "color": "#4CAF50",
        "icon": "comment"
    })
    
    # Move to first position for visibility
    if len(ws.shortcuts) > 1:
        sms_shortcut = ws.shortcuts[-1]
        ws.shortcuts.remove(sms_shortcut)
        ws.shortcuts.insert(0, sms_shortcut)
        
        # Reindex
        for i, s in enumerate(ws.shortcuts):
            s.idx = i + 1
    
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    
    print("✓ Added SMS Inbox shortcut to CRM workspace")

