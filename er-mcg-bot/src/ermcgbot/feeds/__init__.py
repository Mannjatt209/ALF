"""Pluggable EHR trackboard feeds (synthetic, Epic, Cerner, Pulsecheck/HL7)."""

from .base import FeedNotConfigured, TrackboardFeed
from .fhir import (
    CernerFhirFeed,
    EpicFhirFeed,
    FhirTrackboardFeed,
    map_bundle_to_patients,
)
from .hl7 import Hl7AdtFeed, parse_adt_message
from .registry import available_feeds, get_feed
from .synthetic import SyntheticFeed

__all__ = [
    "TrackboardFeed",
    "FeedNotConfigured",
    "SyntheticFeed",
    "FhirTrackboardFeed",
    "EpicFhirFeed",
    "CernerFhirFeed",
    "map_bundle_to_patients",
    "Hl7AdtFeed",
    "parse_adt_message",
    "get_feed",
    "available_feeds",
]
