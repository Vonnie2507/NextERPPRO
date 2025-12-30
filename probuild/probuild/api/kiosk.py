from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime


def _require_logged_in():
    if frappe.session.user == "Guest":
        frappe.throw("Login required.")


def _validate_worker_pin(worker: str, pin: str) -> None:
    doc = frappe.get_doc("Kiosk Worker", worker)
    if not doc.enabled:
        frappe.throw("Worker is disabled.")
    stored = frappe.get_password("Kiosk Worker", worker, "pin")
    if stored != pin:
        frappe.throw("Invalid PIN.")


@frappe.whitelist()
def list_workers() -> list[dict[str, Any]]:
    _require_logged_in()
    return frappe.get_all(
        "Kiosk Worker",
        filters={"enabled": 1},
        fields=["name", "worker_name"],
        order_by="worker_name asc",
    )


@frappe.whitelist()
def list_open_tasks(limit: int = 200) -> list[dict[str, Any]]:
    _require_logged_in()
    limit = min(int(limit or 200), 500)
    return frappe.get_all(
        "Task",
        filters={"status": ["not in", ["Completed", "Cancelled"]]},
        fields=["name", "subject", "project", "status", "probuild_team", "expected_time", "probuild_planned_date", "exp_end_date"],
        order_by="modified desc",
        limit=limit,
    )


@frappe.whitelist()
def get_active_timer(worker: str) -> dict[str, Any] | None:
    _require_logged_in()
    running = frappe.get_all(
        "Kiosk Time Log",
        filters={"worker": worker, "status": "Running"},
        fields=["name", "task", "started_at", "station"],
        order_by="started_at desc",
        limit=1,
    )
    return running[0] if running else None


@frappe.whitelist()
def start_timer(worker: str, pin: str, task: str, station: str | None = None) -> str:
    _require_logged_in()
    _validate_worker_pin(worker, pin)

    existing = frappe.get_all(
        "Kiosk Time Log",
        filters={"worker": worker, "status": "Running"},
        fields=["name", "task"],
        limit=1,
    )
    if existing:
        if existing[0]["task"] == task:
            return existing[0]["name"]
        frappe.throw("You already have a running timer. Stop it before starting another task.")

    project = frappe.db.get_value("Task", task, "project")
    log = frappe.get_doc(
        {
            "doctype": "Kiosk Time Log",
            "worker": worker,
            "task": task,
            "project": project,
            "status": "Running",
            "started_at": now_datetime(),
            "station": station,
        }
    )
    log.insert(ignore_permissions=True)
    return log.name


@frappe.whitelist()
def stop_timer(worker: str, pin: str, task: str | None = None) -> str:
    _require_logged_in()
    _validate_worker_pin(worker, pin)

    filters = {"worker": worker, "status": "Running"}
    if task:
        filters["task"] = task

    running = frappe.get_all(
        "Kiosk Time Log",
        filters=filters,
        fields=["name"],
        order_by="started_at desc",
        limit=1,
    )
    if not running:
        frappe.throw("No running timer found.")

    log = frappe.get_doc("Kiosk Time Log", running[0]["name"])
    log.status = "Stopped"
    log.stopped_at = now_datetime()
    log.save(ignore_permissions=True)
    return log.name


