from __future__ import annotations

import frappe


def execute():
    # Update existing profiles or create new ones with correct Probuild hours
    # Production: 2 staff, 7am-3:30pm with 30min lunch = 7.5 hrs/person, Mon-Fri
    _create_or_update_profile(
        profile_name="Production Default",
        team="Production",
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
    _create_or_update_profile(
        profile_name="Installation Default",
        team="Installation",
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


def _create_or_update_profile(profile_name: str, team: str, weekday_capacity: dict[str, tuple[int, float]]):
    if frappe.db.exists("Capacity Profile", profile_name):
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
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Capacity Profile",
                "profile_name": profile_name,
                "team": team,
                "active": 1,
                "days": [
                    {
                        "doctype": "Capacity Profile Day",
                        "weekday": weekday,
                        "staff_count": staff_count,
                        "hours_per_staff": hours_per_staff,
                    }
                    for weekday, (staff_count, hours_per_staff) in weekday_capacity.items()
                ],
            }
        )
        doc.insert(ignore_permissions=True)


