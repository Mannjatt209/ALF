"""Trackboard feed abstraction.

A *feed* is anything that can produce the current ED census as a list of
`Patient` objects in our common model. The rest of the system (criteria
engine, notifier, audit) never knows or cares which EHR the data came from.

That decoupling is the whole point of this layer: the hospital can run this
against Pulsecheck today and Epic or Cerner tomorrow by swapping the feed,
with zero changes to the screening logic.
"""
from __future__ import annotations

import abc
from typing import List

from ..models import Patient


class TrackboardFeed(abc.ABC):
    """Base interface every EHR adapter implements."""

    #: Human-readable source name, e.g. "Epic (FHIR R4)".
    name: str = "feed"

    @abc.abstractmethod
    def fetch(self) -> List[Patient]:
        """Return the current ED trackboard as normalized Patient objects."""
        raise NotImplementedError


class FeedNotConfigured(RuntimeError):
    """Raised when a live feed is selected without the credentials/approvals.

    Live EHR connectivity is intentionally gated. Surfacing a clear error
    (rather than silently doing nothing) keeps the prototype honest about what
    still needs IT, a BAA, and vendor onboarding before real data flows.
    """
