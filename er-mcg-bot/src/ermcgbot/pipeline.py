"""End-to-end screening pipeline that ties the pieces together.

Flow (all on synthetic data):
    trackboard feed -> criteria engine -> for matches: build + send (dry-run)
    notification -> audit log -> return results for reporting.
"""
from __future__ import annotations

import json
from typing import Dict, List

from .audit import AuditLog
from .criteria_engine import CriteriaEngine
from .models import Patient, ScreeningResult
from .notifier import Notifier, build_notification


def load_patients(path: str) -> List[Patient]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Patient.from_dict(row) for row in raw["patients"]]


def load_on_call(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["on_call"]


def run_screening(
    patients: List[Patient],
    engine: CriteriaEngine,
    notifier: Notifier,
    on_call: Dict[str, Dict[str, str]],
    audit: AuditLog | None = None,
) -> List[ScreeningResult]:
    """Screen every patient; notify (dry-run) for those who meet criteria."""
    results = engine.screen_all(patients)

    for result in results:
        fired = [m.criterion_id for m in result.matches]
        if audit:
            audit.record_screen(result.patient.mrn, result.meets_criteria, fired)

        if not result.meets_criteria:
            continue

        notification = build_notification(result, on_call)
        delivery = notifier.send(notification)
        if audit:
            audit.record_notification(
                result.patient.mrn, notification.to_handle, delivery
            )

    return results
