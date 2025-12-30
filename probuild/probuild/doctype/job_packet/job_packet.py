from __future__ import annotations

import frappe
from frappe.model.document import Document


class JobPacket(Document):
    def on_update(self):
        before = self.get_doc_before_save()
        before_status = getattr(before, "status", None) if before else None

        if self.status != "Approved":
            return

        if before_status == "Approved":
            return

        if getattr(self, "tasks_generated", 0):
            return

        project = self._resolve_project()
        tasks = _create_tasks_for_job_packet(self, project=project)
        if self.job_type == "Supply Only":
            _create_supply_only_dispatches(self, project=project)
            self.db_set("dispatch_generated", 1, update_modified=False)

        if tasks:
            self.db_set("tasks_generated", 1, update_modified=False)

    def _resolve_project(self) -> str:
        if self.project:
            return self.project

        if self.sales_order:
            project = frappe.db.get_value("Sales Order", self.sales_order, "project")
            if project:
                return project

        frappe.throw("Job Packet must be linked to a Project (or a Sales Order with a Project) before approval.")


def _create_tasks_for_job_packet(job_packet: JobPacket, project: str) -> list[str]:
    templates = _get_task_template(job_packet.job_type)
    created: dict[str, str] = {}

    for t in templates:
        task = frappe.get_doc(
            {
                "doctype": "Task",
                "project": project,
                "subject": t["subject"],
                "status": "Open",
                "probuild_team": t.get("team"),
            }
        )
        task.insert(ignore_permissions=True)
        created[t["key"]] = task.name

    # Add dependencies after tasks exist
    for t in templates:
        depends_on = t.get("depends_on", [])
        if not depends_on:
            continue
        task_name = created[t["key"]]
        task = frappe.get_doc("Task", task_name)
        for dep_key in depends_on:
            if dep_key not in created:
                continue
            task.append("depends_on", {"task": created[dep_key]})
        task.save(ignore_permissions=True)

    return list(created.values())


def _create_supply_only_dispatches(job_packet: JobPacket, project: str) -> None:
    for deliverable_type in ["PostsDispatch", "PanelsDispatch"]:
        doc = frappe.get_doc(
            {
                "doctype": "Dispatch Deliverable",
                "job_type": job_packet.job_type,
                "sales_order": job_packet.sales_order,
                "project": project,
                "job_packet": job_packet.name,
                "deliverable_type": deliverable_type,
                "status": "Planned",
            }
        )
        doc.insert(ignore_permissions=True)


def _get_task_template(job_type: str) -> list[dict]:
    if job_type == "Supply Only":
        return [
            {"key": "ps1", "subject": "Production Sheet 1", "team": "Production"},
            {"key": "m_posts", "subject": "Manufacture Posts", "team": "Production", "depends_on": ["ps1"]},
            {
                "key": "dispatch_posts",
                "subject": "Dispatch Posts (Freight/Pickup)",
                "team": "Production",
                "depends_on": ["m_posts"],
            },
            {"key": "await_measure", "subject": "Await Customer Measurements", "team": "Scheduler", "depends_on": ["dispatch_posts"]},
            {"key": "ps2", "subject": "Production Sheet 2 (Panels)", "team": "Production", "depends_on": ["await_measure"]},
            {"key": "m_panels", "subject": "Manufacture Panels", "team": "Production", "depends_on": ["ps2"]},
            {
                "key": "dispatch_panels",
                "subject": "Dispatch Panels (Freight/Pickup)",
                "team": "Production",
                "depends_on": ["m_panels"],
            },
            {"key": "closeout", "subject": "Closeout", "team": "Scheduler", "depends_on": ["dispatch_panels"]},
        ]

    # Supply & Install (default)
    return [
        {"key": "ps1", "subject": "Production Sheet 1", "team": "Production"},
        {"key": "m_posts", "subject": "Manufacture Posts", "team": "Production", "depends_on": ["ps1"]},
        {"key": "i_posts", "subject": "Install Posts", "team": "Installation", "depends_on": ["m_posts"]},
        {"key": "measure", "subject": "Measure Panels Gap & Confirm", "team": "Installation", "depends_on": ["i_posts"]},
        {"key": "ps2", "subject": "Production Sheet 2 (Panels)", "team": "Production", "depends_on": ["measure"]},
        {"key": "m_panels", "subject": "Manufacture Panels", "team": "Production", "depends_on": ["ps2"]},
        {"key": "i_panels", "subject": "Install Panels", "team": "Installation", "depends_on": ["m_panels"]},
        {"key": "closeout", "subject": "Closeout", "team": "Scheduler", "depends_on": ["i_panels"]},
    ]


