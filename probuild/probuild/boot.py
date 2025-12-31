from __future__ import annotations

import frappe


def boot_session(bootinfo):
    """Add Probuild configuration to the boot session (available as frappe.boot.*)"""
    # Google API key for Places/Street View
    bootinfo.probuild_google_api_key = frappe.conf.get("probuild_google_api_key", "")
    
    # Unread SMS count for notification badge
    if frappe.session.user != "Guest":
        try:
            bootinfo.unread_sms_count = frappe.db.count("SMS Log", filters={
                "direction": "Inbound",
                "read": 0
            }) or 0
        except Exception:
            bootinfo.unread_sms_count = 0




