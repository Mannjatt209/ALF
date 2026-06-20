"""Proves the screening pipeline runs with all network egress blocked.

This is the test you run in front of a security reviewer: with outbound
connections hard-blocked, the full synthetic pipeline still completes — because
nothing in the screening path touches the network.
"""
import os
import socket
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ermcgbot import offline_guard  # noqa: E402
from ermcgbot.criteria_engine import CriteriaEngine  # noqa: E402
from ermcgbot.feeds import get_feed  # noqa: E402
from ermcgbot.notifier import ConsoleNotifier  # noqa: E402
from ermcgbot.pipeline import load_on_call, run_screening  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class OfflineGuardTests(unittest.TestCase):
    def tearDown(self):
        offline_guard.deactivate()

    def test_outbound_connection_is_blocked_when_active(self):
        offline_guard.activate()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.assertRaises(offline_guard.NetworkBlocked):
            s.connect(("93.184.216.34", 80))  # would be an internet egress
        s.close()

    def test_allowlist_permits_only_named_host(self):
        offline_guard.activate(allow={("10.0.0.5", 443)})
        # The internal EHR host is allowed past the guard (it then fails to
        # actually connect in this test env, but NOT with NetworkBlocked).
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.01)
        try:
            s.connect(("10.0.0.5", 443))
        except offline_guard.NetworkBlocked:
            self.fail("allow-listed host should not be blocked by the guard")
        except OSError:
            pass  # timeout/refused is fine — the point is it wasn't *blocked*
        finally:
            s.close()

    def test_full_pipeline_runs_with_egress_blocked(self):
        offline_guard.activate()  # block everything
        feed = get_feed("synthetic", path=os.path.join(_ROOT, "data/synthetic_patients.json"))
        engine = CriteriaEngine.from_file(os.path.join(_ROOT, "criteria/demo_criteria.json"))
        on_call = load_on_call(os.path.join(_ROOT, "data/on_call.json"))
        results = run_screening(feed.fetch(), engine, ConsoleNotifier(sink=[]), on_call)
        met = [r for r in results if r.meets_criteria]
        self.assertEqual(len(met), 8)  # same result as online — nothing needed the network


if __name__ == "__main__":
    unittest.main()
