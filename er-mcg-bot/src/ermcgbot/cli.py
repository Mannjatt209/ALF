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
from .feeds import available_feeds, get_feed
from .live_demo import load_json, render_live_html
from .notifier import ConsoleNotifier
from .pipeline import load_on_call, run_screening
from .report import render_html

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))


def _default(path: str) -> str:
    return os.path.join(_ROOT, path)


def build_feed(name: str, source: str, default_patients: str):
    """Construct the selected trackboard feed.

    For the prototype, the EHR feeds run in offline 'replay' mode against a
    saved bundle/export so the adapters can be demonstrated without live
    credentials. Live connectivity stays gated (see feeds/*.py).
    """
    name = name.lower()
    if name == "synthetic":
        return get_feed("synthetic", path=source or default_patients)
    if name in ("epic", "cerner"):
        return get_feed(
            name, sample_bundle_path=source or _default("data/sample_fhir_bundle.json")
        )
    if name in ("pulsecheck", "hl7"):
        path = source or _default("data/sample_pulsecheck_adt.hl7")
        with open(path, "r", encoding="utf-8") as fh:
            # ADT messages in the sample file are separated by a blank line.
            messages = [m for m in fh.read().split("\n\n") if m.strip()]
        return get_feed(name, messages=messages)
    raise ValueError(f"Unknown feed {name!r}. Available: {available_feeds()}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feed", default="synthetic",
        help=f"data source: {', '.join(available_feeds())} (default: synthetic)",
    )
    parser.add_argument(
        "--feed-source", default=None,
        help="override the feed's input file (patients JSON, FHIR bundle, or HL7 export)",
    )
    parser.add_argument("--patients", default=_default("data/synthetic_patients.json"))
    parser.add_argument("--criteria", default=_default("criteria/demo_criteria.json"))
    parser.add_argument("--on-call", default=_default("data/on_call.json"))
    parser.add_argument("--audit", default=_default("data/audit_log.jsonl"))
    parser.add_argument("--html", default=None, help="write a static HTML report here")
    parser.add_argument(
        "--live", default=None,
        help="write an animated live-simulation HTML demo here",
    )
    args = parser.parse_args(argv)

    feed = build_feed(args.feed, args.feed_source, args.patients)
    patients = feed.fetch()
    engine = CriteriaEngine.from_file(args.criteria)
    on_call = load_on_call(args.on_call)
    notifier = ConsoleNotifier()
    audit = AuditLog(args.audit)

    print(f"Source: {feed.name}")
    print(f"Screening {len(patients)} ED patients...\n")
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

    if args.live:
        live = render_live_html(
            load_json(args.patients),
            load_json(args.criteria),
            load_json(args.on_call),
        )
        with open(args.live, "w", encoding="utf-8") as fh:
            fh.write(live)
        print(f"Live demo written to {args.live} — open it in a browser.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
