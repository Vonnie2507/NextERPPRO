from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime


def current_mmyy() -> str:
    dt = now_datetime()
    return f"{dt.month:02d}{dt.year % 100:02d}"


def next_base_ref() -> str:
    # Monthly-reset sequence: 0125-001, 0125-002, ...
    mmyy = current_mmyy()
    return make_autoname(f"{mmyy}-.###")


def next_quote_ref(base_ref: str) -> str:
    # Per-lead quote counter: 0125-001-Q1, Q2, ...
    return make_autoname(f"{base_ref}-Q.#")


def next_variation_ref(base_ref: str) -> str:
    return make_autoname(f"{base_ref}-VAR-.#")


def next_credit_ref(base_ref: str) -> str:
    return make_autoname(f"{base_ref}-CR-.#")


@dataclass(frozen=True)
class InvoiceDisplayRef:
    display_ref: str
    milestone_index: int | None = None
    milestone_total: int | None = None


def build_milestone_invoice_ref(base_ref: str, index: int, total: int) -> InvoiceDisplayRef:
    return InvoiceDisplayRef(display_ref=f"{base_ref}-INV-{index}/{total}", milestone_index=index, milestone_total=total)


def next_milestone_index(base_ref: str) -> int:
    # NOTE: we intentionally look at the custom field, not docname, because ERPNext invoice
    # names remain internal. This keeps numbering human-friendly and stable.
    max_idx = frappe.db.sql(
        """
        select max(coalesce(probuild_milestone_index, 0))
        from `tabSales Invoice`
        where probuild_base_ref = %s
          and probuild_invoice_kind = 'Milestone'
          and docstatus < 2
        """,
        (base_ref,),
    )[0][0]
    return int(max_idx or 0) + 1





