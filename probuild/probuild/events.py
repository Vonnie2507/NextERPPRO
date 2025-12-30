from __future__ import annotations

import frappe
from frappe.utils import cint

from probuild.probuild.reference import (
    build_milestone_invoice_ref,
    next_base_ref,
    next_credit_ref,
    next_milestone_index,
    next_quote_ref,
    next_variation_ref,
)


# ============================================================
# AUTONAME HOOKS - Set document names to Probuild refs
# ============================================================
# Lead no longer gets custom naming - it uses default ERPNext IDs
# and behaves like a contact (one per email/phone).
# Opportunity is now the "pipeline" record with MMYY-###-P format.


def opportunity_autoname(doc, method=None):
    """Set Opportunity name to MMYY-###-P format (P = Pipeline/Prospect)."""
    if doc.name and not doc.name.startswith("new-opportunity"):
        return  # Already named
    
    # Opportunity always gets its own unique base ref (the job/deal number)
    base = next_base_ref()
    doc.probuild_base_ref = base
    doc.name = f"{base}-P"


def quotation_autoname(doc, method=None):
    """Set Quotation name to MMYY-###-Q# format."""
    if doc.name and not doc.name.startswith("new-quotation"):
        return

    base = None
    # Primary: get base ref from linked Opportunity
    if doc.get("opportunity"):
        base = frappe.db.get_value("Opportunity", doc.opportunity, "probuild_base_ref")
    # Fallback: check for probuild_opportunity field if we add one
    if not base and doc.get("probuild_opportunity"):
        base = frappe.db.get_value("Opportunity", doc.probuild_opportunity, "probuild_base_ref")

    if not base:
        # Fall back to ERPNext default naming if no Opportunity linked
        return

    doc.probuild_base_ref = base
    doc.probuild_quote_ref = next_quote_ref(base)
    doc.name = doc.probuild_quote_ref


def project_autoname(doc, method=None):
    """Set Project name to MMYY-###-J format if base ref is provided."""
    if doc.name and not doc.name.startswith("new-project"):
        return
    base = doc.get("probuild_base_ref")
    if not base:
        return  # Let ERPNext use default naming
    doc.probuild_job_ref = f"{base}-J"
    doc.name = doc.probuild_job_ref


def project_validate(doc, method=None):
    """Ensure job ref field is set when base ref exists."""
    base = doc.get("probuild_base_ref")
    if base and not doc.get("probuild_job_ref"):
        doc.probuild_job_ref = f"{base}-J"


def sales_invoice_autoname(doc, method=None):
    """Set Sales Invoice name to MMYY-###-INV-#/N or VAR-# or CR-# format."""
    if doc.name and not doc.name.startswith("new-sales-invoice"):
        return

    base = doc.get("probuild_base_ref")
    if not base and doc.get("project"):
        base = frappe.db.get_value("Project", doc.project, "probuild_base_ref")

    if not base:
        return  # Let ERPNext use default naming

    doc.probuild_base_ref = base

    kind = doc.get("probuild_invoice_kind") or ("Credit" if doc.get("is_return") else "Milestone")
    doc.probuild_invoice_kind = kind

    if kind == "Milestone":
        if not doc.get("probuild_milestone_total") and doc.get("project"):
            total = frappe.db.get_value("Project", doc.project, "probuild_milestone_total")
            if total:
                doc.probuild_milestone_total = cint(total)
        if not doc.get("probuild_milestone_total"):
            doc.probuild_milestone_total = 1

        if not doc.get("probuild_milestone_index"):
            doc.probuild_milestone_index = next_milestone_index(base)

        ref = build_milestone_invoice_ref(base, cint(doc.probuild_milestone_index), cint(doc.probuild_milestone_total))
        doc.probuild_display_ref = ref.display_ref
        doc.name = doc.probuild_display_ref

    elif kind == "Variation":
        if not doc.get("probuild_variation_no"):
            var_ref = next_variation_ref(base)
            doc.probuild_display_ref = var_ref
            try:
                doc.probuild_variation_no = cint(var_ref.split("-")[-1])
            except Exception:
                doc.probuild_variation_no = 0
        else:
            doc.probuild_display_ref = f"{base}-VAR-{cint(doc.probuild_variation_no)}"
        doc.name = doc.probuild_display_ref

    else:  # Credit
        if not doc.get("probuild_credit_no"):
            cr_ref = next_credit_ref(base)
            doc.probuild_display_ref = cr_ref
            try:
                doc.probuild_credit_no = cint(cr_ref.split("-")[-1])
            except Exception:
                doc.probuild_credit_no = 0
        else:
            doc.probuild_display_ref = f"{base}-CR-{cint(doc.probuild_credit_no)}"
        doc.name = doc.probuild_display_ref
