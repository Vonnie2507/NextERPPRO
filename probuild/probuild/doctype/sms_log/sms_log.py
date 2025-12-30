# Copyright (c) 2024, Probuild and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SMSLog(Document):
    pass


def create_sms_log(direction, phone_number, message, linked_doctype=None, linked_name=None, 
                   status="Pending", twilio_sid=None, contact_name=None, error_message=None):
    """Create an SMS Log entry"""
    log = frappe.get_doc({
        "doctype": "SMS Log",
        "direction": direction,
        "phone_number": phone_number,
        "message": message,
        "linked_doctype": linked_doctype,
        "linked_name": linked_name,
        "status": status,
        "twilio_sid": twilio_sid,
        "contact_name": contact_name,
        "sent_at": frappe.utils.now_datetime(),
        "error_message": error_message
    })
    log.insert(ignore_permissions=True)
    frappe.db.commit()
    return log


def get_sms_history(doctype, name):
    """Get SMS history for a linked document"""
    return frappe.get_all(
        "SMS Log",
        filters={
            "linked_doctype": doctype,
            "linked_name": name
        },
        fields=["name", "direction", "phone_number", "message", "status", "sent_at", "contact_name"],
        order_by="sent_at desc"
    )

