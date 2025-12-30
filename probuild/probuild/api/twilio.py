# Copyright (c) 2024, Probuild and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import requests
from requests.auth import HTTPBasicAuth


@frappe.whitelist()
def send_sms(phone_number, message, linked_doctype=None, linked_name=None, contact_name=None):
    """
    Send an SMS via Twilio
    
    Args:
        phone_number: Recipient phone number (with country code)
        message: SMS message text
        linked_doctype: Optional - DocType to link the SMS log to
        linked_name: Optional - Document name to link the SMS log to
        contact_name: Optional - Contact name for reference
    
    Returns:
        dict with success status and message SID
    """
    from probuild.probuild.doctype.twilio_settings.twilio_settings import get_twilio_settings
    from probuild.probuild.doctype.sms_log.sms_log import create_sms_log
    
    try:
        settings = get_twilio_settings()
        
        # Normalize phone number
        phone_number = normalize_phone_number(phone_number, settings.default_country_code)
        
        # Twilio API endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.account_sid}/Messages.json"
        
        # Send SMS via Twilio REST API
        response = requests.post(
            url,
            data={
                "To": phone_number,
                "From": settings.phone_number,
                "Body": message
            },
            auth=HTTPBasicAuth(settings.account_sid, settings.get_auth_token())
        )
        
        result = response.json()
        
        if response.status_code in [200, 201]:
            # Success - create log
            log = create_sms_log(
                direction="Outbound",
                phone_number=phone_number,
                message=message,
                linked_doctype=linked_doctype,
                linked_name=linked_name,
                status="Sent",
                twilio_sid=result.get("sid"),
                contact_name=contact_name
            )
            
            return {
                "success": True,
                "message_sid": result.get("sid"),
                "log_name": log.name
            }
        else:
            # Failed - create error log
            error_msg = result.get("message", "Unknown error")
            log = create_sms_log(
                direction="Outbound",
                phone_number=phone_number,
                message=message,
                linked_doctype=linked_doctype,
                linked_name=linked_name,
                status="Failed",
                contact_name=contact_name,
                error_message=error_msg
            )
            
            frappe.log_error(f"Twilio SMS Error: {error_msg}", "Twilio SMS Failed")
            
            return {
                "success": False,
                "error": error_msg,
                "log_name": log.name
            }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Twilio SMS Exception")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def receive_sms():
    """
    Webhook endpoint to receive incoming SMS from Twilio
    
    Twilio sends POST request with:
    - From: Sender phone number
    - To: Your Twilio number
    - Body: Message text
    - MessageSid: Twilio message ID
    """
    from probuild.probuild.doctype.sms_log.sms_log import create_sms_log
    
    try:
        # Get data from Twilio webhook
        from_number = frappe.form_dict.get("From", "")
        to_number = frappe.form_dict.get("To", "")
        message_body = frappe.form_dict.get("Body", "")
        message_sid = frappe.form_dict.get("MessageSid", "")
        
        if not from_number or not message_body:
            return "Missing required fields"
        
        # Find linked Prospect/Opportunity by phone number
        linked_doctype, linked_name, contact_name = find_linked_record(from_number)
        
        # Create SMS log for incoming message
        log = create_sms_log(
            direction="Inbound",
            phone_number=from_number,
            message=message_body,
            linked_doctype=linked_doctype,
            linked_name=linked_name,
            status="Received",
            twilio_sid=message_sid,
            contact_name=contact_name
        )
        
        # Create notification for all users with Sales User role
        create_sms_notification(log, from_number, message_body, contact_name, linked_doctype, linked_name)
        
        # Return TwiML response (empty - no auto-reply)
        frappe.response["type"] = "text/xml"
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Twilio Webhook Error")
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def create_sms_notification(log, from_number, message_body, contact_name, linked_doctype, linked_name):
    """
    Create a notification for incoming SMS.
    Uses Frappe's built-in Notification Log system.
    """
    try:
        # Determine the notification subject
        sender = contact_name or from_number
        subject = f"New SMS from {sender}"
        
        # Truncate message for notification
        preview = message_body[:100] + "..." if len(message_body) > 100 else message_body
        
        # Get users to notify (System Manager and Sales User roles)
        users_to_notify = frappe.get_all(
            "Has Role",
            filters={"role": ["in", ["System Manager", "Sales User"]], "parenttype": "User"},
            fields=["parent"],
            distinct=True
        )
        
        for user_row in users_to_notify:
            user = user_row.parent
            
            # Skip disabled users and Guest
            if user in ["Guest", "Administrator"]:
                continue
            
            user_doc = frappe.get_cached_doc("User", user)
            if not user_doc.enabled:
                continue
            
            # Create notification log
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "document_type": linked_doctype or "SMS Log",
                "document_name": linked_name or log.name,
                "subject": subject,
                "email_content": f"<p><strong>{sender}:</strong> {preview}</p>",
                "read": 0
            })
            notification.insert(ignore_permissions=True)
        
        frappe.db.commit()
        
    except Exception as e:
        # Don't fail the webhook if notification fails
        frappe.log_error(frappe.get_traceback(), "SMS Notification Error")


def find_linked_record(phone_number):
    """
    Find a Prospect or Opportunity linked to a phone number
    
    Returns:
        tuple: (doctype, name, contact_name) or (None, None, None)
    """
    # Normalize the phone number for comparison
    normalized = normalize_phone_number(phone_number, "+61")
    phone_variants = [phone_number, normalized]
    
    # Remove + and spaces for additional matching
    clean_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
    phone_variants.append(clean_number)
    
    # Check recent SMS logs first (most likely to match recent conversations)
    recent_log = frappe.db.get_value(
        "SMS Log",
        filters={
            "phone_number": ["in", phone_variants],
            "linked_doctype": ["is", "set"],
            "direction": "Outbound"
        },
        fieldname=["linked_doctype", "linked_name", "contact_name"],
        order_by="sent_at desc"
    )
    
    if recent_log:
        return recent_log
    
    # Check Prospect's mobile field
    prospect = frappe.db.get_value(
        "Prospect",
        filters={"probuild_mobile": ["in", phone_variants]},
        fieldname=["name", "prospect_name"]
    )
    
    if prospect:
        return ("Prospect", prospect[0], prospect[1])
    
    # No match found
    return (None, None, None)


def normalize_phone_number(phone, default_country_code="+61"):
    """Normalize phone number to include country code"""
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # Already has country code
    if phone.startswith("+"):
        return phone
    
    # Australian mobile starting with 04
    if phone.startswith("04") and default_country_code == "+61":
        return "+61" + phone[1:]
    
    # Just digits, assume needs country code
    if phone.startswith("0"):
        return default_country_code + phone[1:]
    
    return default_country_code + phone


@frappe.whitelist()
def get_sms_templates(doctype):
    """Get SMS templates for a DocType"""
    from probuild.probuild.doctype.sms_template.sms_template import get_templates_for_doctype
    return get_templates_for_doctype(doctype)


@frappe.whitelist()
def get_sms_history(doctype, name):
    """Get SMS history for a document"""
    from probuild.probuild.doctype.sms_log.sms_log import get_sms_history
    return get_sms_history(doctype, name)


@frappe.whitelist()
def send_template_sms(template_name, phone_number, linked_doctype, linked_name):
    """Send an SMS using a template"""
    from probuild.probuild.doctype.sms_template.sms_template import render_template
    
    # Get context from linked document
    context = get_template_context(linked_doctype, linked_name)
    
    # Render the template
    message = render_template(template_name, context)
    
    # Send the SMS
    return send_sms(
        phone_number=phone_number,
        message=message,
        linked_doctype=linked_doctype,
        linked_name=linked_name,
        contact_name=context.get("customer_name")
    )


def get_template_context(doctype, name):
    """Get template context from a document"""
    context = {
        "company_name": frappe.defaults.get_global_default("company") or "Probuild"
    }
    
    try:
        doc = frappe.get_doc(doctype, name)
        
        if doctype == "Prospect":
            context["customer_name"] = doc.prospect_name
        elif doctype == "Opportunity":
            context["opportunity_name"] = doc.name
            context["job_nickname"] = doc.get("probuild_job_nickname", "")
            if doc.get("prospect"):
                prospect = frappe.get_doc("Prospect", doc.prospect)
                context["customer_name"] = prospect.prospect_name
    except Exception:
        pass
    
    return context

