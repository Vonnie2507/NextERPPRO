from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def execute(filters=None):
    filters = filters or {}
    team = filters.get("team") or "Production"
    from_date = getdate(filters.get("from_date") or date.today())
    to_date = getdate(filters.get("to_date") or (from_date + timedelta(days=30)))

    capacity_by_weekday = _get_capacity_by_weekday(team)
    planned = _get_planned_hours(team, from_date, to_date)

    columns = [
        {"fieldname": "day", "label": "Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "weekday", "label": "Weekday", "fieldtype": "Data", "width": 100},
        {"fieldname": "capacity_hours", "label": "Capacity (hrs)", "fieldtype": "Float", "width": 120},
        {"fieldname": "planned_hours", "label": "Planned (hrs)", "fieldtype": "Float", "width": 120},
        {"fieldname": "variance_hours", "label": "Variance (hrs)", "fieldtype": "Float", "width": 120},
        {"fieldname": "tasks", "label": "Tasks", "fieldtype": "Int", "width": 80},
    ]

    data = []
    d = from_date
    while d <= to_date:
        weekday = d.strftime("%A")
        capacity = float(capacity_by_weekday.get(weekday, 0))
        planned_hours, tasks = planned.get(d, (0.0, 0))
        data.append(
            {
                "day": d,
                "weekday": weekday,
                "capacity_hours": capacity,
                "planned_hours": planned_hours,
                "variance_hours": capacity - planned_hours,
                "tasks": tasks,
            }
        )
        d = d + timedelta(days=1)

    return columns, data


def _get_capacity_by_weekday(team: str) -> dict[str, float]:
    profile = frappe.get_all(
        "Capacity Profile",
        filters={"team": team, "active": 1},
        pluck="name",
        limit=1,
    )
    if not profile:
        return {}

    days = frappe.get_all(
        "Capacity Profile Day",
        filters={"parenttype": "Capacity Profile", "parent": profile[0]},
        fields=["weekday", "total_hours"],
    )
    return {d["weekday"]: float(d.get("total_hours") or 0) for d in days}


def _get_planned_hours(team: str, from_date: date, to_date: date) -> dict[date, tuple[float, int]]:
    # Prefer explicit planned date; fall back to expected end date for MVP.
    tasks = frappe.get_all(
        "Task",
        filters={
            "status": ["not in", ["Completed", "Cancelled"]],
            "probuild_team": team,
            "expected_time": [">", 0],
        },
        fields=["name", "expected_time", "probuild_planned_date", "exp_end_date"],
    )

    out: dict[date, tuple[float, int]] = {}
    for t in tasks:
        d = getdate(t.get("probuild_planned_date") or t.get("exp_end_date"))
        if not d:
            continue
        if d < from_date or d > to_date:
            continue
        hours = float(t.get("expected_time") or 0)
        prev_hours, prev_count = out.get(d, (0.0, 0))
        out[d] = (prev_hours + hours, prev_count + 1)
    return out


