"""Synthetic feed — reads the bundled fake trackboard from a JSON file.

This is the only feed safe to run anywhere: it touches no EHR and contains no
PHI. It is the default for demos and tests.
"""
from __future__ import annotations

import json
from typing import List

from ..models import Patient
from .base import TrackboardFeed


class SyntheticFeed(TrackboardFeed):
    name = "Synthetic (bundled demo data)"

    def __init__(self, path: str):
        self.path = path

    def fetch(self) -> List[Patient]:
        with open(self.path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return [Patient.from_dict(row) for row in raw["patients"]]
