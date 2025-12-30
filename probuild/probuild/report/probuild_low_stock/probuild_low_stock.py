from __future__ import annotations

import frappe


def execute(filters=None):
    filters = filters or {}
    warehouse = filters.get("warehouse")

    wh_clause = ""
    params = []
    if warehouse:
        wh_clause = "and b.warehouse = %s"
        params.append(warehouse)

    rows = frappe.db.sql(
        f"""
        select
            b.item_code,
            b.warehouse,
            b.actual_qty,
            ir.warehouse_reorder_level as reorder_level,
            ir.warehouse_reorder_qty as reorder_qty
        from `tabBin` b
        left join `tabItem Reorder` ir
            on ir.parent = b.item_code
            and (ir.warehouse = b.warehouse or ir.warehouse is null)
        where coalesce(ir.warehouse_reorder_level, 0) > 0
          and b.actual_qty < ir.warehouse_reorder_level
          {wh_clause}
        order by (ir.warehouse_reorder_level - b.actual_qty) desc
        """,
        tuple(params),
        as_dict=True,
    )

    columns = [
        {"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "warehouse", "label": "Warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"fieldname": "actual_qty", "label": "On Hand", "fieldtype": "Float", "width": 110},
        {"fieldname": "reorder_level", "label": "Reorder Level", "fieldtype": "Float", "width": 130},
        {"fieldname": "reorder_qty", "label": "Reorder Qty", "fieldtype": "Float", "width": 120},
    ]
    return columns, rows


