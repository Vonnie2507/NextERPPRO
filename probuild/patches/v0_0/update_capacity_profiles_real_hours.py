from __future__ import annotations

import frappe


def execute():
    """Update capacity profiles with real Probuild working hours."""
    # Production: 2 staff, 7am-3:30pm with 30min lunch = 7.5 hrs/person, Mon-Fri
    _update_profile(
        profile_name="Production Default",
        weekday_capacity={
            "Monday": (2, 7.5),
            "Tuesday": (2, 7.5),
            "Wednesday": (2, 7.5),
            "Thursday": (2, 7.5),
            "Friday": (2, 7.5),
            "Saturday": (0, 0),
            "Sunday": (0, 0),
        },
    )

    # Installation: 2 staff, 6am-2:30pm with 30min lunch = 8 hrs/person, Mon-Fri
    _update_profile(
        profile_name="Installation Default",
        weekday_capacity={
            "Monday": (2, 8),
            "Tuesday": (2, 8),
            "Wednesday": (2, 8),
            "Thursday": (2, 8),
            "Friday": (2, 8),
            "Saturday": (0, 0),
            "Sunday": (0, 0),
        },
    )


def _update_profile(profile_name: str, weekday_capacity: dict[str, tuple[int, float]]):
    if not frappe.db.exists("Capacity Profile", profile_name):
        return
    doc = frappe.get_doc("Capacity Profile", profile_name)
    doc.days = []
    for weekday, (staff_count, hours_per_staff) in weekday_capacity.items():
        doc.append(
            "days",
            {
                "weekday": weekday,
                "staff_count": staff_count,
                "hours_per_staff": hours_per_staff,
            },
        )
    doc.save(ignore_permissions=True)

