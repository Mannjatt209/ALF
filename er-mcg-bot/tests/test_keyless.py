"""Tests for the keyless feeds (CSV export, file drop) — synthetic data only."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ermcgbot.criteria_engine import CriteriaEngine  # noqa: E402
from ermcgbot.feeds import get_feed  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _engine():
    return CriteriaEngine.from_file(os.path.join(_ROOT, "criteria/demo_criteria.json"))


class CsvFeedTests(unittest.TestCase):
    def setUp(self):
        self.feed = get_feed(
            "csv", path=os.path.join(_ROOT, "data/sample_trackboard_export.csv")
        )

    def test_loads_and_types_values(self):
        patients = self.feed.fetch()
        self.assertEqual(len(patients), 5)
        p = {x.mrn: x for x in patients}["SYN-4001"]
        self.assertEqual(p.vitals["hr"], 112)        # int
        self.assertEqual(p.labs["lactate"], 3.4)     # float
        self.assertFalse(p.flags["chest_pain"])      # bool

    def test_csv_screens_same_as_engine(self):
        engine = _engine()
        flagged = [p for p in self.feed.fetch() if engine.screen(p).meets_criteria]
        # sepsis(4001), ACS(4002), hypoxia(4004), GI-bleed(4005); sprain(4003) clear
        self.assertEqual(len(flagged), 4)


class FileDropTests(unittest.TestCase):
    def test_reads_hl7_files_from_directory(self):
        # The data/ dir contains sample_pulsecheck_adt.hl7 (2 ADT messages).
        feed = get_feed("filedrop", directory=os.path.join(_ROOT, "data"))
        patients = feed.fetch()
        self.assertEqual(len(patients), 2)
        self.assertEqual(patients[0].mrn, "SYN-3001")


if __name__ == "__main__":
    unittest.main()
