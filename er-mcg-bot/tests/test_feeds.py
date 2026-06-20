"""Tests for the pluggable EHR feed adapters (synthetic data only)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ermcgbot.criteria_engine import CriteriaEngine  # noqa: E402
from ermcgbot.feeds import (  # noqa: E402
    CernerFhirFeed,
    EpicFhirFeed,
    FeedNotConfigured,
    FhirTrackboardFeed,
    Hl7AdtFeed,
    get_feed,
    map_bundle_to_patients,
    parse_adt_message,
)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BUNDLE = os.path.join(_ROOT, "data/sample_fhir_bundle.json")
_HL7 = os.path.join(_ROOT, "data/sample_pulsecheck_adt.hl7")


def _engine():
    return CriteriaEngine.from_file(os.path.join(_ROOT, "criteria/demo_criteria.json"))


class SyntheticFeedTests(unittest.TestCase):
    def test_loads_bundled_patients(self):
        feed = get_feed("synthetic", path=os.path.join(_ROOT, "data/synthetic_patients.json"))
        self.assertEqual(len(feed.fetch()), 12)


class FhirFeedTests(unittest.TestCase):
    def test_epic_offline_replay_maps_and_screens(self):
        feed = EpicFhirFeed(sample_bundle_path=_BUNDLE)
        patients = feed.fetch()
        self.assertEqual(len(patients), 3)
        by_bed = {p.bed: p for p in patients}
        # Vitals/labs mapped from LOINC-coded Observations.
        self.assertEqual(by_bed["ED-21"].labs["lactate"], 3.6)
        self.assertEqual(by_bed["ED-21"].vitals["hr"], 116)
        # Chest-pain flag derived from Encounter.reasonCode text.
        self.assertTrue(by_bed["ED-08"].flags["chest_pain"])

        engine = _engine()
        flagged = [p for p in patients if engine.screen(p).meets_criteria]
        self.assertEqual(len(flagged), 2)  # sepsis + ACS; laceration is clear

    def test_cerner_uses_same_mapper(self):
        epic = EpicFhirFeed(sample_bundle_path=_BUNDLE).fetch()
        cerner = CernerFhirFeed(sample_bundle_path=_BUNDLE).fetch()
        self.assertEqual([p.mrn for p in epic], [p.mrn for p in cerner])

    def test_live_fetch_is_gated(self):
        feed = FhirTrackboardFeed(base_url="https://example/fhir", enabled=True)
        with self.assertRaises(FeedNotConfigured):
            feed.fetch()

    def test_inactive_encounter_skipped(self):
        bundle = {
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "X", "gender": "male"}},
                {"resource": {"resourceType": "Encounter", "status": "finished",
                              "subject": {"reference": "Patient/X"}}},
            ]
        }
        self.assertEqual(map_bundle_to_patients(bundle), [])


class Hl7FeedTests(unittest.TestCase):
    def test_parse_adt_demographics_and_location(self):
        with open(_HL7, "r", encoding="utf-8") as fh:
            messages = [m for m in fh.read().split("\n\n") if m.strip()]
        feed = Hl7AdtFeed(messages=messages)
        patients = feed.fetch()
        self.assertEqual(len(patients), 2)
        self.assertEqual(patients[0].mrn, "SYN-3001")
        self.assertEqual(patients[0].sex, "M")
        self.assertEqual(patients[0].bed, "ED-ROOM21-A")

    def test_single_message_parse(self):
        msg = "MSH|^~\\&|X\rPID|1||M99^^^H^MR||Doe^Jane||19800101|F\rPV1|1|E|ED^R5^B"
        p = parse_adt_message(msg)
        self.assertEqual(p.mrn, "M99")
        self.assertEqual(p.name, "Jane Doe")
        self.assertEqual(p.bed, "ED-R5-B")


class RegistryTests(unittest.TestCase):
    def test_unknown_feed_raises(self):
        with self.assertRaises(ValueError):
            get_feed("meditech")


if __name__ == "__main__":
    unittest.main()
