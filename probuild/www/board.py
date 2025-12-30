from __future__ import annotations

import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Login required for board.")
    context.no_cache = 1
    context.title = "Production Board"
    return context


