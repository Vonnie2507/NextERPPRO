from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import frappe
from frappe.utils import getdate


def _require_logged_in():
    if frappe.session.user == "Guest":
        frappe.throw("Login required.")


def _task_due_date(t: dict[str, Any]) -> date | None:
    return getdate(t.get("probuild_planned_date") or t.get("exp_end_date"))


@frappe.whitelist()
def get_board_data() -> dict[str, Any]:
    _require_logged_in()

    today = date.today()
    soon = today + timedelta(days=7)

    tasks = frappe.get_all(
        "Task",
        filters={"status": ["not in", ["Completed", "Cancelled"]]},
        fields=[
            "name",
            "subject",
            "project",
            "status",
            "probuild_team",
            "probuild_planned_date",
            "exp_end_date",
        ],
        order_by="modified desc",
        limit=500,
    )

    due_today = []
    behind = []
    for t in tasks:
        d = _task_due_date(t)
        if not d:
            continue
        if d == today:
            due_today.append({**t, "due_date": d})
        elif d < today:
            behind.append({**t, "due_date": d})

    dispatches = frappe.get_all(
        "Dispatch Deliverable",
        filters={"status": ["not in", ["Cancelled"]]},
        fields=["name", "deliverable_type", "project", "status", "due_date", "dispatch_method", "job_packet"],
        order_by="modified desc",
        limit=500,
    )

    ready = [d for d in dispatches if d.get("status") == "Ready"]
    due_soon = []
    for d in dispatches:
        dd = getdate(d.get("due_date"))
        if dd and today <= dd <= soon:
            due_soon.append(d)

    return {
        "today": str(today),
        "due_today_tasks": due_today[:100],
        "behind_tasks": behind[:100],
        "ready_dispatches": ready[:100],
        "due_soon_dispatches": due_soon[:100],
    }


