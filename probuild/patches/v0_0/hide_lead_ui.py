"""
Patch: Hide Lead from CRM Workspace UI

This patch removes Lead shortcuts, links, and sidebar entries from the CRM workspace
so that sales staff don't see the Lead DocType in day-to-day workflow.
The DocType remains in the database for internal ERPNext references.
"""

from __future__ import annotations

import json
import frappe


def execute():
    # 1. Hide Lead from CRM workspace shortcuts and content
    _hide_lead_from_crm_workspace()
    
    # 2. Hide Lead from sidebar navigation by setting in_create property
    _hide_lead_from_global_create()
    
    # 3. Add Prospect shortcut to CRM workspace for easy access
    _add_prospect_shortcut_to_crm_workspace()
    
    # 4. Hide the Leads tab/field on Prospect form
    _hide_leads_on_prospect()
    
    # 5. Hide irrelevant Opportunity fields (Organization, Analytics sections)
    _hide_opportunity_clutter()
    
    frappe.clear_cache()


def _hide_lead_from_crm_workspace():
    """Remove Lead shortcuts and links from CRM workspace"""
    
    if not frappe.db.exists("Workspace", "CRM"):
        return
    
    workspace = frappe.get_doc("Workspace", "CRM")
    
    # Remove Lead from shortcuts
    shortcuts_to_remove = []
    for i, shortcut in enumerate(workspace.shortcuts):
        if shortcut.link_to == "Lead":
            shortcuts_to_remove.append(shortcut)
    
    for shortcut in shortcuts_to_remove:
        workspace.shortcuts.remove(shortcut)
    
    # Remove Lead from links
    links_to_remove = []
    for link in workspace.links:
        if link.link_to == "Lead":
            links_to_remove.append(link)
    
    for link in links_to_remove:
        workspace.links.remove(link)
    
    # Update content JSON to remove Lead shortcut references
    if workspace.content:
        try:
            content = json.loads(workspace.content)
            # Filter out any Lead shortcuts from content
            content = [
                item for item in content
                if not (
                    item.get("type") == "shortcut" and 
                    item.get("data", {}).get("shortcut_name") == "Lead"
                )
            ]
            workspace.content = json.dumps(content)
        except (json.JSONDecodeError, TypeError):
            pass
    
    workspace.save(ignore_permissions=True)


def _hide_lead_from_global_create():
    """
    Hide Lead from global search/create dialogs by creating a Property Setter.
    This prevents Lead from appearing in the "New" dialog across the system.
    """
    
    # Create Property Setter to hide Lead from global search
    if not frappe.db.exists("Property Setter", {"doc_type": "Lead", "property": "in_create"}):
        frappe.get_doc({
            "doctype": "Property Setter",
            "doctype_or_field": "DocType",
            "doc_type": "Lead",
            "property": "in_create",
            "property_type": "Check",
            "value": "0",
        }).insert(ignore_permissions=True)
    
    # Also hide Lead from standard search
    if not frappe.db.exists("Property Setter", {"doc_type": "Lead", "property": "search_fields"}):
        # Set empty search_fields to prevent it appearing in global search results
        pass  # We don't want to break search entirely, just hide from navigation


def _add_prospect_shortcut_to_crm_workspace():
    """Add Prospect shortcut to CRM workspace for easy access"""
    
    if not frappe.db.exists("Workspace", "CRM"):
        return
    
    workspace = frappe.get_doc("Workspace", "CRM")
    
    # Check if Prospect shortcut already exists
    has_prospect_shortcut = any(
        shortcut.link_to == "Prospect" for shortcut in workspace.shortcuts
    )
    
    if not has_prospect_shortcut:
        # Add Prospect shortcut at the beginning
        workspace.append("shortcuts", {
            "type": "DocType",
            "link_to": "Prospect",
            "label": "Prospect",
            "color": "Blue",
            "format": "{} Total"
        })
    
    # Update content JSON to add Prospect shortcut at the beginning of shortcuts section
    if workspace.content:
        try:
            content = json.loads(workspace.content)
            # Check if Prospect shortcut exists in content
            has_prospect_in_content = any(
                item.get("type") == "shortcut" and 
                item.get("data", {}).get("shortcut_name") == "Prospect"
                for item in content
            )
            
            if not has_prospect_in_content:
                # Find position of first shortcut and insert Prospect before it
                for i, item in enumerate(content):
                    if item.get("type") == "shortcut":
                        prospect_shortcut = {
                            "id": f"probuild_prospect_{frappe.generate_hash(length=8)}",
                            "type": "shortcut",
                            "data": {
                                "shortcut_name": "Prospect",
                                "col": 3
                            }
                        }
                        content.insert(i, prospect_shortcut)
                        break
                
                workspace.content = json.dumps(content)
        except (json.JSONDecodeError, TypeError):
            pass
    
    workspace.save(ignore_permissions=True)


def _hide_leads_on_prospect():
    """
    Hide the 'leads' field/tab on the Prospect form.
    Probuild uses Prospect + Opportunity, not Leads.
    """
    
    # Create Property Setter to hide the leads field on Prospect
    ps_name = "Prospect-leads-hidden"
    if not frappe.db.exists("Property Setter", ps_name):
        frappe.get_doc({
            "doctype": "Property Setter",
            "name": ps_name,
            "doctype_or_field": "DocField",
            "doc_type": "Prospect",
            "field_name": "leads",
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
        }).insert(ignore_permissions=True)
    
    # Also hide the leads_tab section break if it exists
    ps_name_tab = "Prospect-leads_tab-hidden"
    if not frappe.db.exists("Property Setter", ps_name_tab):
        if frappe.db.exists("DocField", {"parent": "Prospect", "fieldname": "leads_tab"}):
            frappe.get_doc({
                "doctype": "Property Setter",
                "name": ps_name_tab,
                "doctype_or_field": "DocField",
                "doc_type": "Prospect",
                "field_name": "leads_tab",
                "property": "hidden",
                "property_type": "Check",
                "value": "1",
            }).insert(ignore_permissions=True)


def _hide_opportunity_clutter():
    """
    Hide irrelevant Opportunity fields that don't apply to a fencing business.
    Organization details, Analytics, etc.
    """
    
    # Fields to hide on Opportunity
    fields_to_hide = [
        # Organization section
        "organization_details_section",
        "no_of_employees",
        "annual_revenue",
        "customer_group",
        "industry",
        "market_segment",
        "website",
        "city",
        "state",
        "country",
        # Analytics section
        "section_break_analytics",
        "utm_source",
        "utm_content",
        "utm_campaign",
        "utm_medium",
        # Other unnecessary fields
        "conversion_rate",
        "base_opportunity_amount",
    ]
    
    for fieldname in fields_to_hide:
        ps_name = f"Opportunity-{fieldname}-hidden"
        if not frappe.db.exists("Property Setter", ps_name):
            # Check if field exists
            if frappe.db.exists("DocField", {"parent": "Opportunity", "fieldname": fieldname}):
                frappe.get_doc({
                    "doctype": "Property Setter",
                    "name": ps_name,
                    "doctype_or_field": "DocField",
                    "doc_type": "Opportunity",
                    "field_name": fieldname,
                    "property": "hidden",
                    "property_type": "Check",
                    "value": "1",
                }).insert(ignore_permissions=True)

