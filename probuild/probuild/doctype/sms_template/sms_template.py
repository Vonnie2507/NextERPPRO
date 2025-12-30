# Copyright (c) 2024, Probuild and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SMSTemplate(Document):
    pass


def get_templates_for_doctype(doctype):
    """Get enabled SMS templates applicable for a DocType"""
    applicable = ["Both"]
    if doctype in ["Prospect", "Opportunity"]:
        applicable.append(doctype)
    
    return frappe.get_all(
        "SMS Template",
        filters={
            "enabled": 1,
            "applicable_for": ["in", applicable]
        },
        fields=["name", "template_name", "message_template"]
    )


def render_template(template_name, context):
    """Render an SMS template with context variables"""
    template = frappe.get_doc("SMS Template", template_name)
    message = template.message_template
    
    for key, value in context.items():
        placeholder = "{" + key + "}"
        message = message.replace(placeholder, str(value) if value else "")
    
    return message

