from __future__ import annotations

import frappe


def diagnose_lead_hooks():
    """Deep diagnostic for Lead doc_events hooks."""
    results = {}

    # 1. Check if probuild hooks are loaded
    try:
        from frappe import get_hooks
        lead_hooks = get_hooks("doc_events").get("Lead", {})
        results["lead_doc_events"] = lead_hooks
    except Exception as e:
        results["lead_doc_events_error"] = str(e)

    # 2. Check if the events module can be imported
    try:
        from probuild.probuild import events
        results["events_module"] = "OK"
        results["lead_before_insert_exists"] = hasattr(events, "lead_before_insert")
    except Exception as e:
        results["events_module_error"] = str(e)

    # 3. Check if reference module works
    try:
        from probuild.probuild.reference import next_base_ref
        ref = next_base_ref()
        results["next_base_ref_result"] = ref
    except Exception as e:
        results["next_base_ref_error"] = str(e)

    # 4. Check if custom fields exist on Lead
    try:
        fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Lead", "fieldname": ["like", "probuild%"]},
            fields=["fieldname", "fieldtype"],
        )
        results["lead_custom_fields"] = fields
    except Exception as e:
        results["lead_custom_fields_error"] = str(e)

    # 5. Try creating a test lead and see what happens
    try:
        test_lead = frappe.get_doc({
            "doctype": "Lead",
            "first_name": "HookTest",
            "last_name": f"Debug-{frappe.utils.random_string(5)}",
        })
        # Manually call before_insert hooks
        test_lead.run_method("before_insert")
        results["test_lead_base_ref"] = test_lead.get("probuild_base_ref")
        results["test_lead_lead_ref"] = test_lead.get("probuild_lead_ref")
        # Don't actually save, just test the hook
    except Exception as e:
        results["test_lead_error"] = str(e)

    # 6. Check hooks.py content
    try:
        import probuild.hooks as hooks_module
        results["hooks_doc_events"] = getattr(hooks_module, "doc_events", "NOT FOUND")
    except Exception as e:
        results["hooks_module_error"] = str(e)

    print("=" * 60)
    print("PROBUILD LEAD HOOKS DIAGNOSTIC")
    print("=" * 60)
    for key, value in results.items():
        print(f"{key}: {value}")
    print("=" * 60)

    return results


def create_real_test_lead():
    """Create an actual Lead in the database and print the Probuild refs."""
    import frappe

    lead = frappe.get_doc({
        "doctype": "Lead",
        "first_name": "RealTest",
        "last_name": f"Lead-{frappe.utils.random_string(5)}",
    })
    lead.insert(ignore_permissions=True)
    frappe.db.commit()

    # Re-fetch to confirm
    saved = frappe.get_doc("Lead", lead.name)
    print("=" * 60)
    print("CREATED LEAD IN DATABASE")
    print("=" * 60)
    print(f"Lead Name (ID): {saved.name}")
    print(f"probuild_base_ref: {saved.get('probuild_base_ref')}")
    print(f"probuild_lead_ref: {saved.get('probuild_lead_ref')}")
    print("=" * 60)
    print(f"View it at: http://localhost:8080/app/lead/{saved.name}")
    print("=" * 60)

    return {
        "name": saved.name,
        "probuild_base_ref": saved.get("probuild_base_ref"),
        "probuild_lead_ref": saved.get("probuild_lead_ref"),
    }

