"""Command-line entry point for the prototype.

Usage:
    python -m ermcgbot.cli            # run the demo with bundled synthetic data
    python -m ermcgbot.cli --html out.html
"""
from __future__ import annotations

import argparse
import os

from .audit import AuditLog
from .criteria_engine import CriteriaEngine
from .notifier import ConsoleNotifier
from .pipeline import load_on_call, load_patients, run_screening
from .report import render_html

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))


def _default(path: str) -> str:
    return os.path.join(_ROOT, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patients", default=_default("data/synthetic_patients.json"))
    parser.add_argument("--criteria", default=_default("criteria/demo_criteria.json"))
    parser.add_argument("--on-call", default=_default("data/on_call.json"))
    parser.add_argument("--audit", default=_default("data/audit_log.jsonl"))
    parser.add_argument("--html", default=None, help="write an HTML report here")
    args = parser.parse_args(argv)

    patients = load_patients(args.patients)
    engine = CriteriaEngine.from_file(args.criteria)
    on_call = load_on_call(args.on_call)
    notifier = ConsoleNotifier()
    audit = AuditLog(args.audit)

    print(f"Screening {len(patients)} synthetic ED patients...\n")
    results = run_screening(patients, engine, notifier, on_call, audit)

    met = [r for r in results if r.meets_criteria]
    print(
        f"\nSummary: {len(met)}/{len(results)} patients met demonstration "
        f"admission criteria. Audit trail: {args.audit}"
    )

    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_html(results))
        print(f"HTML report written to {args.html}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
