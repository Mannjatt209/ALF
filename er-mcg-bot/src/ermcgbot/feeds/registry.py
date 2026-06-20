"""Feed registry / factory.

Pick a data source by name. `synthetic` works out of the box; the EHR feeds
either replay a saved bundle offline (demo) or raise FeedNotConfigured until a
sanctioned, credentialed integration is in place.
"""
from __future__ import annotations

from typing import Any

from .base import TrackboardFeed
from .csv_feed import CsvFeed
from .fhir import CernerFhirFeed, EpicFhirFeed
from .filedrop import FileDropFeed
from .hl7 import Hl7AdtFeed
from .synthetic import SyntheticFeed

#: Map a CLI/config name to a feed constructor.
_FEEDS = {
    "synthetic": SyntheticFeed,
    "epic": EpicFhirFeed,
    "cerner": CernerFhirFeed,
    "pulsecheck": Hl7AdtFeed,  # Pulsecheck typically integrates via HL7v2 ADT
    "hl7": Hl7AdtFeed,
    "csv": CsvFeed,            # flat-file export, no API key
    "filedrop": FileDropFeed,  # interface-engine HL7 drop folder, no API key
}


def available_feeds() -> list[str]:
    return sorted(_FEEDS)


def get_feed(name: str, **config: Any) -> TrackboardFeed:
    key = name.lower()
    if key not in _FEEDS:
        raise ValueError(
            f"Unknown feed {name!r}. Available: {', '.join(available_feeds())}"
        )
    return _FEEDS[key](**config)
