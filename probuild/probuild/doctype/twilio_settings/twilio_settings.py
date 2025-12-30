# Copyright (c) 2024, Probuild and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TwilioSettings(Document):
    def validate(self):
        # Generate webhook URL based on site
        if frappe.local.site:
            site_url = frappe.utils.get_url()
            self.webhook_url = f"{site_url}/api/method/probuild.probuild.api.twilio.receive_sms"
    
    def get_auth_token(self):
        """Get decrypted auth token"""
        return self.get_password("auth_token")


def get_twilio_settings():
    """Get Twilio Settings singleton"""
    settings = frappe.get_single("Twilio Settings")
    if not settings.enabled:
        frappe.throw("Twilio SMS is not enabled. Please enable it in Twilio Settings.")
    return settings


def is_twilio_enabled():
    """Check if Twilio is enabled"""
    try:
        settings = frappe.get_single("Twilio Settings")
        return settings.enabled and settings.account_sid and settings.auth_token
    except Exception:
        return False

