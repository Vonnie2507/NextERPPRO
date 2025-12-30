from __future__ import annotations

import frappe


def check_probuild_doctypes() -> list[str]:
    """Dev helper: verify expected Probuild DocTypes exist."""
    expected = ["Job Packet", "Dispatch Deliverable", "Kiosk Worker", "Kiosk Time Log"]
    return [d for d in expected if frappe.db.exists("DocType", d)]


def print_probuild_doctypes() -> None:
    print(check_probuild_doctypes())


def print_probuild_module_doctypes() -> None:
    """Print all DocTypes that ERPNext currently believes belong to the Probuild module."""
    doctypes = frappe.get_all("DocType", filters={"module": "Probuild"}, pluck="name")  # type: ignore[arg-type]
    print(sorted(doctypes))


def print_installed_apps() -> None:
    print(frappe.get_installed_apps())


def print_task_dependency_fields() -> None:
    meta = frappe.get_meta("Task")
    candidates = ["depends_on", "depends_on_tasks", "depends_on_task", "depends_on_task", "depends_on_task", "depends_on_tasks"]
    out = {}
    for f in meta.fields:
        if "depend" in f.fieldname:
            out[f.fieldname] = f.fieldtype
    print(out)


def print_task_depends_on_options() -> None:
    meta = frappe.get_meta("Task")
    f = meta.get_field("depends_on")
    print({"fieldtype": f.fieldtype, "options": f.options})


def print_task_time_fields() -> None:
    meta = frappe.get_meta("Task")
    out = {}
    for f in meta.fields:
        if any(k in f.fieldname for k in ["hour", "time", "exp_", "expected"]):
            out[f.fieldname] = f.fieldtype
    print(out)


def print_capacity_profiles() -> None:
    profiles = frappe.get_all("Capacity Profile", fields=["name", "team", "active"])
    print(profiles)


def create_sample_job_packet(job_type: str = "Supply Only") -> None:
    """Create a tiny sample Project + Job Packet and approve it to test automation."""
    company = _ensure_company()
    project = frappe.get_doc(
        {
            "doctype": "Project",
            "project_name": f"Sample {job_type}",
            "status": "Open",
            "company": company,
        }
    ).insert(ignore_permissions=True)

    jp = frappe.get_doc(
        {
            "doctype": "Job Packet",
            "job_type": job_type,
            "project": project.name,
            "status": "Approved",
            "fence_style": "TestStyle",
        }
    )
    jp.insert(ignore_permissions=True)

    tasks = frappe.get_all("Task", filters={"project": project.name}, pluck="name")
    dispatches = frappe.get_all("Dispatch Deliverable", filters={"project": project.name}, pluck="name")
    print({"project": project.name, "job_packet": jp.name, "tasks": len(tasks), "dispatches": len(dispatches)})


def _ensure_company() -> str:
    existing = frappe.get_all("Company", pluck="name", limit=1)
    if existing:
        return existing[0]

    company = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": "Probuild PVC",
            "abbr": "PRO",
            "default_currency": "AUD",
            "country": "Australia",
        }
    ).insert(ignore_permissions=True)
    return company.name


def print_capacity_profile_details() -> None:
    """Print daily capacity breakdown for Production and Installation profiles."""
    for profile_name in ["Production Default", "Installation Default"]:
        if not frappe.db.exists("Capacity Profile", profile_name):
            print(f"{profile_name}: NOT FOUND")
            continue
        doc = frappe.get_doc("Capacity Profile", profile_name)
        print(f"\n{profile_name} ({doc.team}):")
        for day in doc.days:
            staff = float(day.staff_count or 0)
            hours = float(day.hours_per_staff or 0)
            total = staff * hours
            print(f"  {day.weekday}: {int(staff)} staff × {hours}h = {total}h capacity")


def create_sample_lead_quote_project_invoice() -> None:
    """Lightweight ref test without needing full ERP accounting setup."""
    from probuild.probuild.reference import build_milestone_invoice_ref, next_quote_ref

    lead = frappe.get_doc({"doctype": "Lead", "first_name": "Test", "last_name": "Lead"}).insert(ignore_permissions=True)
    base = lead.probuild_base_ref

    print(
        {
            "lead": lead.name,
            "lead_ref": getattr(lead, "probuild_lead_ref", None),
            "base_ref": base,
            "quote_ref_example": next_quote_ref(base),
            "job_ref_example": f"{base}-J",
            "milestone_invoice_example": build_milestone_invoice_ref(base, 1, 5).display_ref,
            "variation_example": f"{base}-VAR-1",
            "credit_example": f"{base}-CR-1",
        }
    )


