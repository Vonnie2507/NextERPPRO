from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # Reuse Task.expected_time as planned hours; add team + planned date fields.
    fields = {
        "Task": [
            {
                "fieldname": "probuild_sb",
                "fieldtype": "Section Break",
                "label": "Probuild",
                "insert_after": "actual_time",
                "collapsible": 1,
            },
            {
                "fieldname": "probuild_team",
                "fieldtype": "Select",
                "label": "Team",
                "options": "Production\nInstallation\nSales\nScheduler\nAccounts",
                "insert_after": "probuild_sb",
            },
            {
                "fieldname": "probuild_planned_date",
                "fieldtype": "Date",
                "label": "Planned Date",
                "insert_after": "probuild_team",
            },
        ]
    }

    create_custom_fields(fields, update=True)
    frappe.clear_cache(doctype="Task")


