from __future__ import annotations

import frappe


def boot_session(bootinfo):
    """Add Probuild configuration to the boot session (available as frappe.boot.*)"""
    # Google API key for Places/Street View
    bootinfo.probuild_google_api_key = frappe.conf.get("probuild_google_api_key", "")




