from __future__ import annotations

import frappe


def get_context(context):
    # Require the device to be logged in (e.g., a shared "kiosk" user),
    # then use worker PINs inside the kiosk UI for accountability.
    if frappe.session.user == "Guest":
        frappe.throw("Login required for kiosk mode.")

    context.no_cache = 1
    context.title = "Workshop Kiosk"
    return context


