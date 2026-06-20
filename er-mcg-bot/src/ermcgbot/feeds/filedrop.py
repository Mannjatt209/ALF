"""File-drop feed — reads HL7 messages an interface engine writes to a folder.

The classic keyless integration: the EHR's interface engine drops HL7 ADT/ORU
files into a watched directory on a secure share. The bot reads the folder and
never opens a network socket — which also makes it the natural fit for a
no-egress / near-air-gap deployment (see docs/offline-deployment.md).
"""
from __future__ import annotations

import glob
import os
from typing import List

from ..models import Patient
from .base import TrackboardFeed
from .hl7 import parse_adt_message


class FileDropFeed(TrackboardFeed):
    name = "File drop (HL7 in a watched folder, no API key)"

    def __init__(self, directory: str, pattern: str = "*.hl7"):
        self.directory = directory
        self.pattern = pattern

    def fetch(self) -> List[Patient]:
        patients: List[Patient] = []
        for path in sorted(glob.glob(os.path.join(self.directory, self.pattern))):
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            # One file may hold several messages separated by a blank line.
            for message in content.split("\n\n"):
                if message.strip():
                    patients.append(parse_adt_message(message))
        return patients
