/* global frappe */

frappe.query_reports["Probuild Capacity"] = {
  filters: [
    {
      fieldname: "team",
      label: "Team",
      fieldtype: "Select",
      options: "Production\nInstallation",
      default: "Production",
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), 0),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
      reqd: 1,
    },
  ],
};


