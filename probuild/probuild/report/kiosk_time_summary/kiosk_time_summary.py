from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def execute(filters=None):
    filters = filters or {}
    from_date = getdate(filters.get("from_date") or (date.today() - timedelta(days=7)))
    to_date = getdate(filters.get("to_date") or date.today())

    rows = frappe.db.sql(
        """
        select
            kt.worker as worker,
            kw.worker_name as worker_name,
            kt.task as task,
            t.subject as task_subject,
            sum(coalesce(kt.duration_seconds, 0)) as duration_seconds
        from `tabKiosk Time Log` kt
        left join `tabKiosk Worker` kw on kw.name = kt.worker
        left join `tabTask` t on t.name = kt.task
        where date(kt.started_at) between %s and %s
          and kt.status = 'Stopped'
        group by kt.worker, kt.task
        order by duration_seconds desc
        """,
        (from_date, to_date),
        as_dict=True,
    )

    for r in rows:
        r["hours"] = float(r["duration_seconds"]) / 3600.0

    columns = [
        {"fieldname": "worker_name", "label": "Worker", "fieldtype": "Data", "width": 180},
        {"fieldname": "task_subject", "label": "Task", "fieldtype": "Data", "width": 280},
        {"fieldname": "hours", "label": "Hours", "fieldtype": "Float", "width": 100},
        {"fieldname": "duration_seconds", "label": "Seconds", "fieldtype": "Int", "width": 100},
    ]

    return columns, rows


