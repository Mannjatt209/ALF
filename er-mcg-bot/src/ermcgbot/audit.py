"""Append-only audit logging.

Compliance will ask "who was screened, what fired, what was sent, and when?"
before anything else. Every screen and every notification attempt is written
to a JSONL audit trail so that question has an answer from day one.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict


class AuditLog:
    def __init__(self, path: str):
        self.path = path

    def _write(self, record: Dict[str, Any]) -> None:
        record["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def record_screen(self, mrn: str, met: bool, criteria: list[str]) -> None:
        self._write(
            {
                "event": "screen",
                "mrn": mrn,
                "met_criteria": met,
                "criteria_fired": criteria,
            }
        )

    def record_notification(
        self, mrn: str, to_handle: str, result: Dict[str, str]
    ) -> None:
        self._write(
            {
                "event": "notification",
                "mrn": mrn,
                "to_handle": to_handle,
                "delivery": result,
            }
        )
