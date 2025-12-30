from __future__ import annotations

from datetime import datetime

import frappe
from frappe.model.document import Document


class KioskTimeLog(Document):
    def validate(self):
        if self.started_at and self.stopped_at:
            started = _to_dt(self.started_at)
            stopped = _to_dt(self.stopped_at)
            self.duration_seconds = max(0, int((stopped - started).total_seconds()))


def _to_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return frappe.utils.get_datetime(value)


