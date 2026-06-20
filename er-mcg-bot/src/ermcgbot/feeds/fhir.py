"""FHIR R4 trackboard feed — the path for Epic and Cerner (Oracle Health).

Both Epic and Cerner expose a SMART-on-FHIR R4 API, so they share one mapper.
The vendor-specific subclasses below differ only in base URL conventions and
auth notes; the resource->Patient mapping is identical because the FHIR R4
resource shapes are standardized.

WHAT IS REAL HERE vs. STUBBED:
  * REAL & TESTED: `map_bundle_to_patients()` converts a FHIR R4 Bundle of
    Patient / Encounter / Observation resources into our common Patient model,
    including LOINC-coded vitals and labs. You can run it offline against a
    sample bundle (see data/sample_fhir_bundle.json) to prove the mapping.
  * STUBBED: the live network transport (`_fetch_bundle`). Pulling real data
    requires a SMART backend-services client, the hospital's FHIR endpoint,
    registered scopes, and a BAA. That is deliberately not wired up here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models import Patient
from .base import FeedNotConfigured, TrackboardFeed

# LOINC code -> (group, field) in our Patient model. This table is the heart of
# the integration: it maps standardized lab/vital codes to the fields the
# criteria engine reads. Extend it as criteria need more inputs.
LOINC_MAP: Dict[str, tuple] = {
    "8867-4": ("vitals", "hr"),            # Heart rate
    "9279-1": ("vitals", "rr"),            # Respiratory rate
    "8310-5": ("vitals", "temp_c"),        # Body temperature (C)
    "8480-6": ("vitals", "sbp"),           # Systolic BP
    "8462-4": ("vitals", "dbp"),           # Diastolic BP
    "2708-6": ("vitals", "spo2"),          # Oxygen saturation (SpO2)
    "59408-5": ("vitals", "spo2"),         # SpO2 (pulse oximetry)
    "2524-7": ("labs", "lactate"),         # Lactate
    "89579-7": ("labs", "troponin_ng_l"),  # Troponin I, high-sensitivity
    "6690-2": ("labs", "wbc"),             # WBC count
    "2160-0": ("labs", "creatinine"),      # Creatinine
    "718-7": ("labs", "hgb"),              # Hemoglobin
    "3151-8": ("flags", "_o2_flow"),       # Inhaled O2 flow rate -> O2 flag
}

# Keyword hints used to derive boolean flags from free-text reason/condition.
_FLAG_KEYWORDS = {
    "chest_pain": ("chest pain",),
    "gi_bleed": ("gi bleed", "melena", "hematochezia", "gi hemorrhage"),
}


def _entries(bundle: Dict[str, Any], rtype: str) -> List[Dict[str, Any]]:
    out = []
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == rtype:
            out.append(res)
    return out


def _patient_name(res: Dict[str, Any]) -> str:
    names = res.get("name", [])
    if not names:
        return "Unknown"
    n = names[0]
    if n.get("text"):
        return n["text"]
    given = " ".join(n.get("given", []))
    return f"{given} {n.get('family', '')}".strip() or "Unknown"


def _age_from_birthdate(birth: Optional[str]) -> int:
    if not birth or len(birth) < 4:
        return 0
    try:
        # Approximate; production should compute against encounter date.
        from datetime import date

        year = int(birth[:4])
        return max(0, date.today().year - year)
    except ValueError:
        return 0


def _ref_id(reference: str) -> str:
    # "Patient/123" -> "123"
    return reference.split("/")[-1] if reference else ""


def map_bundle_to_patients(bundle: Dict[str, Any]) -> List[Patient]:
    """Convert a FHIR R4 Bundle into normalized Patient objects.

    Expects a Bundle containing Patient, Encounter (in-progress, ED location),
    and Observation resources. One Patient is emitted per active Encounter.
    """
    patients_by_id = {p.get("id"): p for p in _entries(bundle, "Patient")}

    # Group observations by the patient they reference.
    obs_by_patient: Dict[str, List[Dict[str, Any]]] = {}
    for obs in _entries(bundle, "Observation"):
        pid = _ref_id(obs.get("subject", {}).get("reference", ""))
        obs_by_patient.setdefault(pid, []).append(obs)

    results: List[Patient] = []
    for enc in _entries(bundle, "Encounter"):
        if enc.get("status") not in (None, "in-progress", "arrived", "triaged"):
            continue
        pid = _ref_id(enc.get("subject", {}).get("reference", ""))
        pres = patients_by_id.get(pid, {})

        # Location: first location display on the encounter.
        bed = "ED-?"
        locs = enc.get("location", [])
        if locs:
            bed = locs[0].get("location", {}).get("display", bed)

        # Chief complaint + flags from reasonCode text.
        reason_text = ""
        for rc in enc.get("reasonCode", []):
            reason_text += " " + (rc.get("text", "") or "")
            for coding in rc.get("coding", []):
                reason_text += " " + (coding.get("display", "") or "")
        reason_text = reason_text.strip()

        vitals: Dict[str, Any] = {}
        labs: Dict[str, Any] = {}
        flags: Dict[str, Any] = {
            "chest_pain": False,
            "on_supplemental_o2": False,
            "gi_bleed": False,
        }

        # Derive keyword flags from the reason text.
        low = reason_text.lower()
        for flag, kws in _FLAG_KEYWORDS.items():
            if any(kw in low for kw in kws):
                flags[flag] = True

        # Map observations via LOINC.
        for obs in obs_by_patient.get(pid, []):
            for coding in obs.get("code", {}).get("coding", []):
                code = coding.get("code")
                if code not in LOINC_MAP:
                    continue
                group, field = LOINC_MAP[code]
                value = obs.get("valueQuantity", {}).get("value")
                if value is None:
                    continue
                if field == "_o2_flow":
                    if value and value > 0:
                        flags["on_supplemental_o2"] = True
                elif group == "vitals":
                    vitals[field] = value
                elif group == "labs":
                    labs[field] = value
                break

        results.append(
            Patient(
                mrn=pres.get("id", pid) or "UNKNOWN",
                name=_patient_name(pres),
                age=_age_from_birthdate(pres.get("birthDate")),
                sex=(pres.get("gender", "U")[:1].upper() or "U"),
                bed=bed,
                arrival_time=(enc.get("period", {}) or {}).get("start", ""),
                chief_complaint=reason_text or "Not documented",
                vitals=vitals,
                labs=labs,
                flags=flags,
            )
        )
    return results


class FhirTrackboardFeed(TrackboardFeed):
    """Base FHIR R4 feed. Subclassed per vendor (Epic, Cerner)."""

    name = "FHIR R4"

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        enabled: bool = False,
        sample_bundle_path: Optional[str] = None,
    ):
        self.base_url = base_url
        self.token = token
        self.enabled = enabled
        # Offline "replay" mode: map a saved bundle, no network. Used for demos.
        self.sample_bundle_path = sample_bundle_path

    def _fetch_bundle(self) -> Dict[str, Any]:
        """Live transport — intentionally not implemented in the prototype."""
        raise FeedNotConfigured(
            f"Live {self.name} connectivity is not enabled. Production needs: a "
            f"SMART-on-FHIR backend-services client, the hospital's FHIR base "
            f"URL + registered scopes (e.g. Encounter.read, Observation.read), "
            f"and a signed BAA. For a demo, pass sample_bundle_path to replay a "
            f"saved FHIR bundle offline."
        )

    def fetch(self) -> List[Patient]:
        if self.sample_bundle_path:
            import json

            with open(self.sample_bundle_path, "r", encoding="utf-8") as fh:
                bundle = json.load(fh)
        else:
            bundle = self._fetch_bundle()
        return map_bundle_to_patients(bundle)


class EpicFhirFeed(FhirTrackboardFeed):
    """Epic via SMART-on-FHIR R4.

    Production notes: register a backend app in the Epic App Orchard /
    vendor-services portal; use the hospital's FHIR base URL
    (e.g. https://<org>/api/FHIR/R4); query active ED encounters then their
    Observations. Mapping is shared `map_bundle_to_patients`.
    """

    name = "Epic (FHIR R4)"


class CernerFhirFeed(FhirTrackboardFeed):
    """Cerner / Oracle Health via SMART-on-FHIR R4.

    Production notes: register via the Oracle Health (Cerner) code console;
    use the tenant FHIR base URL
    (e.g. https://fhir-ehr.cerner.com/r4/<tenant>); same R4 resource shapes,
    so the shared mapper applies unchanged.
    """

    name = "Cerner / Oracle Health (FHIR R4)"
