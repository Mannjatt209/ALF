"""CSV-export trackboard feed — the lowest-barrier keyless integration.

Many EDs can export the trackboard to a CSV/flat file on a secure network share
on a schedule, with NO API key and NO live connection — just a file the bot
reads. This adapter maps that export into our common Patient model.

This is often the easiest thing for hospital IT to say yes to, because it
reuses report-export plumbing they already have and exposes no live interface.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List

from ..models import Patient
from .base import TrackboardFeed

# CSV column -> (group, field). Demographics map to the top level; everything
# else into vitals/labs/flags. Adjust to match the hospital's export columns.
_VITALS = {"hr", "sbp", "dbp", "rr", "temp_c", "spo2"}
_LABS = {"lactate", "troponin_ng_l", "wbc", "creatinine", "hgb"}
_FLAGS = {"chest_pain", "on_supplemental_o2", "gi_bleed"}

_TRUE = {"1", "true", "t", "yes", "y"}


def _num(value: str):
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return int(value) if value.lstrip("-").isdigit() else float(value)
    except ValueError:
        return None


def _row_to_patient(row: Dict[str, str]) -> Patient:
    vitals: Dict[str, Any] = {}
    labs: Dict[str, Any] = {}
    flags: Dict[str, Any] = {}
    for key, raw in row.items():
        if key is None:
            continue
        col = key.strip().lower()
        if col in _VITALS:
            v = _num(raw)
            if v is not None:
                vitals[col] = v
        elif col in _LABS:
            v = _num(raw)
            if v is not None:
                labs[col] = v
        elif col in _FLAGS:
            flags[col] = (raw or "").strip().lower() in _TRUE

    return Patient(
        mrn=row.get("mrn", "UNKNOWN") or "UNKNOWN",
        name=row.get("name", "Unknown") or "Unknown",
        age=int(_num(row.get("age", "0")) or 0),
        sex=(row.get("sex", "U") or "U")[:1].upper(),
        bed=row.get("bed", "ED-?") or "ED-?",
        arrival_time=row.get("arrival_time", ""),
        chief_complaint=row.get("chief_complaint", "") or "Not documented",
        vitals=vitals,
        labs=labs,
        flags=flags,
    )


class CsvFeed(TrackboardFeed):
    name = "CSV export (flat file, no API key)"

    def __init__(self, path: str):
        self.path = path

    def fetch(self) -> List[Patient]:
        with open(self.path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return [_row_to_patient(row) for row in reader]
