"""Tests for the criteria engine and pipeline (synthetic data)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ermcgbot.criteria_engine import CriteriaEngine  # noqa: E402
from ermcgbot.models import Patient  # noqa: E402
from ermcgbot.notifier import ConsoleNotifier, build_notification  # noqa: E402
from ermcgbot.pipeline import (  # noqa: E402
    load_on_call,
    load_patients,
    run_screening,
)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _engine() -> CriteriaEngine:
    return CriteriaEngine.from_file(os.path.join(_ROOT, "criteria/demo_criteria.json"))


class CriteriaEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = _engine()

    def test_sepsis_fires_on_high_lactate_and_tachycardia(self):
        p = Patient.from_dict(
            {
                "mrn": "T1", "name": "x", "age": 60, "sex": "M", "bed": "1",
                "arrival_time": "t", "chief_complaint": "fever",
                "vitals": {"hr": 120, "rr": 18, "temp_c": 37.0},
                "labs": {"lactate": 3.0, "wbc": 9.0},
                "flags": {},
            }
        )
        result = self.engine.screen(p)
        ids = [m.criterion_id for m in result.matches]
        self.assertIn("sepsis_lactate", ids)

    def test_acs_requires_both_troponin_and_chest_pain(self):
        base = {
            "mrn": "T2", "name": "x", "age": 60, "sex": "M", "bed": "1",
            "arrival_time": "t", "chief_complaint": "cp",
            "vitals": {"hr": 80}, "labs": {"troponin_ng_l": 100},
            "flags": {"chest_pain": False},
        }
        # Troponin high but no chest pain -> no match.
        self.assertFalse(self.engine.screen(Patient.from_dict(base)).meets_criteria)
        # Add chest pain -> matches.
        base["flags"]["chest_pain"] = True
        ids = [m.criterion_id for m in self.engine.screen(Patient.from_dict(base)).matches]
        self.assertIn("acs_troponin", ids)

    def test_healthy_patient_meets_nothing(self):
        p = Patient.from_dict(
            {
                "mrn": "T3", "name": "x", "age": 30, "sex": "F", "bed": "1",
                "arrival_time": "t", "chief_complaint": "sprain",
                "vitals": {"hr": 72, "rr": 14, "temp_c": 36.6, "spo2": 99, "sbp": 120},
                "labs": {"lactate": 0.9, "wbc": 6.0, "troponin_ng_l": 3,
                         "creatinine": 0.8, "hgb": 14.0},
                "flags": {"chest_pain": False, "on_supplemental_o2": False,
                          "gi_bleed": False},
            }
        )
        self.assertFalse(self.engine.screen(p).meets_criteria)

    def test_missing_lab_does_not_crash_or_falsely_fire(self):
        p = Patient.from_dict(
            {
                "mrn": "T4", "name": "x", "age": 50, "sex": "M", "bed": "1",
                "arrival_time": "t", "chief_complaint": "?",
                "vitals": {}, "labs": {}, "flags": {},
            }
        )
        self.assertFalse(self.engine.screen(p).meets_criteria)


class PipelineTests(unittest.TestCase):
    def test_end_to_end_dry_run(self):
        patients = load_patients(os.path.join(_ROOT, "data/synthetic_patients.json"))
        on_call = load_on_call(os.path.join(_ROOT, "data/on_call.json"))
        notifier = ConsoleNotifier(sink=[])
        results = run_screening(patients, _engine(), notifier, on_call)
        met = [r for r in results if r.meets_criteria]
        self.assertGreater(len(met), 0)
        # One notification rendered per patient meeting criteria.
        self.assertEqual(len(notifier.sink), len(met))

    def test_notification_routes_acs_to_cardiology(self):
        on_call = load_on_call(os.path.join(_ROOT, "data/on_call.json"))
        p = Patient.from_dict(
            {
                "mrn": "T5", "name": "x", "age": 58, "sex": "F", "bed": "9",
                "arrival_time": "t", "chief_complaint": "chest pain",
                "vitals": {"hr": 90}, "labs": {"troponin_ng_l": 200},
                "flags": {"chest_pain": True},
            }
        )
        result = _engine().screen(p)
        note = build_notification(result, on_call)
        self.assertEqual(note.to_service, "Cardiology")


if __name__ == "__main__":
    unittest.main()
