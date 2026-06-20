"""Data models for the ER MCG-screening prototype.

Everything here operates on SYNTHETIC data only. No real patient information
(PHI) is ever loaded, stored, or transmitted by this prototype.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _get_path(data: Dict[str, Any], path: str) -> Any:
    """Resolve a dotted field path like 'vitals.hr' against a nested dict."""
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


@dataclass
class Patient:
    """A single ED trackboard row (synthetic).

    In production this object is populated from the hospital's FHIR/HL7 ADT
    feed, NOT by screen-scraping an authenticated EHR session.
    """

    mrn: str
    name: str
    age: int
    sex: str
    bed: str
    arrival_time: str
    chief_complaint: str
    vitals: Dict[str, Any] = field(default_factory=dict)
    labs: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Patient":
        return cls(
            mrn=raw["mrn"],
            name=raw["name"],
            age=int(raw["age"]),
            sex=raw["sex"],
            bed=raw["bed"],
            arrival_time=raw["arrival_time"],
            chief_complaint=raw["chief_complaint"],
            vitals=raw.get("vitals", {}),
            labs=raw.get("labs", {}),
            flags=raw.get("flags", {}),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mrn": self.mrn,
            "name": self.name,
            "age": self.age,
            "sex": self.sex,
            "bed": self.bed,
            "arrival_time": self.arrival_time,
            "chief_complaint": self.chief_complaint,
            "vitals": self.vitals,
            "labs": self.labs,
            "flags": self.flags,
        }

    def get(self, path: str) -> Any:
        """Look up a value by dotted path (e.g. 'vitals.hr', 'labs.lactate')."""
        return _get_path(self.as_dict(), path)


@dataclass
class MatchedCriterion:
    """Result of one ruleset matching against one patient."""

    criterion_id: str
    label: str
    description: str
    recommended_status: str  # e.g. "Inpatient" or "Observation"
    service: str
    matched_conditions: List[str] = field(default_factory=list)


@dataclass
class ScreeningResult:
    """Outcome of screening a single patient against all criteria."""

    patient: Patient
    matches: List[MatchedCriterion] = field(default_factory=list)

    @property
    def meets_criteria(self) -> bool:
        return len(self.matches) > 0
