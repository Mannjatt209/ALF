"""Notification layer.

Design principles baked in for the compliance conversation with admin:

1. HUMAN IN THE LOOP. The message asks the physician to confirm; the bot
   never "admits" anyone. It surfaces a candidate and a recommendation.
2. NO PLAIN SMS for PHI. Carrier SMS is not HIPAA-compliant for patient
   information. The production target is a secure clinical messaging API
   (TigerConnect / TigerText, Epic Secure Chat, Spok, etc.).
3. SAFE BY DEFAULT. The default backend is a dry-run console notifier that
   sends nothing anywhere. The TigerConnect backend is a disabled stub that
   refuses to run until a hospital integration + BAA are in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import ScreeningResult


@dataclass
class Notification:
    """A message destined for an on-call physician about one patient."""

    to_service: str
    to_physician: str
    to_handle: str  # secure-messaging handle, NOT a phone number
    subject: str
    body: str


def build_notification(
    result: ScreeningResult, on_call: Dict[str, Dict[str, str]]
) -> Notification:
    """Compose the physician message for a patient who met criteria.

    Routes to the on-call physician for the service of the highest-priority
    (first) matched criterion.
    """
    primary = result.matches[0]
    contact = on_call.get(
        primary.service,
        {"physician": "On-Call Hospitalist", "handle": "hospitalist-oncall"},
    )
    p = result.patient

    criteria_lines = []
    for m in result.matches:
        conds = "; ".join(m.matched_conditions)
        criteria_lines.append(
            f"  - {m.label} -> recommend {m.recommended_status}\n"
            f"      basis: {conds}"
        )
    criteria_block = "\n".join(criteria_lines)

    body = (
        f"UR admission-criteria alert (automated screen — please verify)\n"
        f"Patient: {p.name}  MRN {p.mrn}  ({p.age}{p.sex})\n"
        f"Location: {p.bed}   Arrived: {p.arrival_time}\n"
        f"Chief complaint: {p.chief_complaint}\n\n"
        f"Met the following demonstration criteria:\n"
        f"{criteria_block}\n\n"
        f"This is decision SUPPORT only. Reply ADMIT to proceed, "
        f"DECLINE to dismiss, or open the chart to review."
    )
    return Notification(
        to_service=primary.service,
        to_physician=contact["physician"],
        to_handle=contact["handle"],
        subject=f"Admit candidate: {p.name} ({p.bed})",
        body=body,
    )


class Notifier:
    """Base notifier interface."""

    def send(self, notification: Notification) -> Dict[str, str]:
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Dry-run notifier: prints the message and sends nothing externally.

    This is the default and the only backend safe to run on a laptop demo.
    """

    def __init__(self, sink: List[str] | None = None):
        self.sink = sink if sink is not None else []

    def send(self, notification: Notification) -> Dict[str, str]:
        rendered = (
            f"\n=== SECURE MESSAGE (DRY RUN — NOT SENT) ===\n"
            f"To: {notification.to_physician} "
            f"<{notification.to_handle}> [{notification.to_service}]\n"
            f"Subject: {notification.subject}\n"
            f"{notification.body}\n"
            f"==========================================\n"
        )
        self.sink.append(rendered)
        print(rendered)
        return {"status": "dry_run", "channel": "console"}


class TigerConnectNotifier(Notifier):
    """Production target: secure messaging via the TigerConnect API.

    Intentionally DISABLED in this prototype. It must not be possible to send
    a real message to a clinician from a demo running on synthetic data, and a
    Business Associate Agreement (BAA) + IT-sanctioned integration are
    prerequisites before this is wired up.
    """

    def __init__(self, api_key: str | None = None, enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled

    def send(self, notification: Notification) -> Dict[str, str]:
        raise NotImplementedError(
            "TigerConnect delivery is disabled in the prototype. Enabling it "
            "requires: (1) a signed BAA, (2) an IT-sanctioned TigerConnect API "
            "integration, (3) routing through the real on-call schedule, and "
            "(4) sign-off from Compliance/Privacy. Use ConsoleNotifier for "
            "demos."
        )
