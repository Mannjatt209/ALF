"""HL7v2 ADT feed — the path for Pulsecheck ED and older interface engines.

Many ED systems (including Pulsecheck deployments) surface census and movement
as HL7v2 ADT messages (A01 admit, A04 register, A08 update) over an interface
engine. This adapter parses the demographic + location fields (PID / PV1) into
our Patient model.

Scope note: ADT carries demographics and location, NOT lab/vital values. In a
real deployment the clinical values that the criteria engine needs come from
ORU^R01 result messages (or the FHIR feed). This parser handles the ADT half
and leaves vitals/labs empty unless merged with a results feed — which is an
honest reflection of how HL7 integrations are actually built.
"""
from __future__ import annotations

from typing import Dict, List

from ..models import Patient
from .base import TrackboardFeed


def _split_segments(message: str) -> List[List[str]]:
    segments = []
    for line in message.replace("\r\n", "\r").replace("\n", "\r").split("\r"):
        line = line.strip()
        if line:
            segments.append(line.split("|"))
    return segments


def _field(seg: List[str], idx: int, default: str = "") -> str:
    return seg[idx] if idx < len(seg) and seg[idx] else default


def parse_adt_message(message: str) -> Patient:
    """Parse one HL7v2 ADT message into a Patient (demographics + location)."""
    pid: List[str] = []
    pv1: List[str] = []
    for seg in _split_segments(message):
        if seg[0] == "PID":
            pid = seg
        elif seg[0] == "PV1":
            pv1 = seg

    # PID-3 patient ID list, PID-5 name (XPN: family^given), PID-7 DOB,
    # PID-8 sex. PV1-3 assigned location (PL: point^room^bed...).
    mrn = _field(pid, 3, "UNKNOWN").split("^")[0]
    name_parts = _field(pid, 5).split("^")
    family = name_parts[0] if name_parts else ""
    given = name_parts[1] if len(name_parts) > 1 else ""
    name = f"{given} {family}".strip() or "Unknown"
    dob = _field(pid, 7)
    sex = _field(pid, 8, "U")[:1].upper() or "U"

    loc = _field(pv1, 3)
    bed = "-".join([p for p in loc.split("^")[:3] if p]) or "ED-?"

    age = 0
    if len(dob) >= 4 and dob[:4].isdigit():
        from datetime import date

        age = max(0, date.today().year - int(dob[:4]))

    return Patient(
        mrn=mrn,
        name=name,
        age=age,
        sex=sex,
        bed=bed,
        arrival_time=_field(pv1, 44),  # PV1-44 admit date/time
        chief_complaint="(from ADT; clinical values via results feed)",
        vitals={},
        labs={},
        flags={},
    )


class Hl7AdtFeed(TrackboardFeed):
    """Parses a batch of HL7v2 ADT messages (e.g. a Pulsecheck census export)."""

    name = "HL7v2 ADT (Pulsecheck / interface engine)"

    def __init__(self, messages: List[str] | None = None):
        self.messages = messages or []

    def fetch(self) -> List[Patient]:
        return [parse_adt_message(m) for m in self.messages]
