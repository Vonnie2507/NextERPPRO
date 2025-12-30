/* global frappe */

frappe.query_reports["Probuild Low Stock"] = {
  filters: [
    {
      fieldname: "warehouse",
      label: "Warehouse (optional)",
      fieldtype: "Link",
      options: "Warehouse",
    },
  ],
};


