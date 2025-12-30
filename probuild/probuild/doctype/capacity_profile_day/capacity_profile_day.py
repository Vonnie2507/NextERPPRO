from __future__ import annotations

from frappe.model.document import Document


class CapacityProfileDay(Document):
    def validate(self):
        try:
            staff = float(self.staff_count or 0)
            hours = float(self.hours_per_staff or 0)
        except Exception:
            staff = 0
            hours = 0
        self.total_hours = staff * hours


