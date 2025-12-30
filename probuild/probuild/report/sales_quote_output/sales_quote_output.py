from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def execute(filters=None):
    filters = filters or {}
    from_date = getdate(filters.get("from_date") or (date.today() - timedelta(days=30)))
    to_date = getdate(filters.get("to_date") or date.today())

    rows = frappe.db.sql(
        """
        select
            q.owner as sales_user,
            count(*) as quotes_created,
            sum(coalesce(q.grand_total, 0)) as total_value,
            sum(case when q.status = 'Ordered' then 1 else 0 end) as ordered_count,
            sum(case when q.status = 'Lost' then 1 else 0 end) as lost_count
        from `tabQuotation` q
        where date(q.transaction_date) between %s and %s
        group by q.owner
        order by total_value desc
        """,
        (from_date, to_date),
        as_dict=True,
    )

    for r in rows:
        created = float(r.get("quotes_created") or 0)
        ordered = float(r.get("ordered_count") or 0)
        r["conversion_rate"] = (ordered / created) * 100 if created else 0

    columns = [
        {"fieldname": "sales_user", "label": "Sales User", "fieldtype": "Data", "width": 200},
        {"fieldname": "quotes_created", "label": "Quotes", "fieldtype": "Int", "width": 80},
        {"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 140},
        {"fieldname": "ordered_count", "label": "Ordered", "fieldtype": "Int", "width": 90},
        {"fieldname": "lost_count", "label": "Lost", "fieldtype": "Int", "width": 80},
        {"fieldname": "conversion_rate", "label": "Conversion %", "fieldtype": "Float", "width": 120},
    ]

    return columns, rows


