# ER Admission-Criteria Screening Bot — Prototype

A demonstration prototype of an automated utilization-review assistant for the
Emergency Department. It scans an ED trackboard feed, flags patients who meet
admission criteria, and drafts a secure message to the on-call physician so the
admit decision can be made faster.

> **This prototype runs on 100% synthetic data and sends nothing to anyone.**
> It exists to demonstrate the concept to hospital administration and to scope
> the work needed for a compliant production system. It is **not** a medical
> device and **not** validated for clinical use.

## What it does (and what it deliberately does not)

| Concern | Prototype | Production (after approvals) |
|---|---|---|
| Patient data source | Bundled synthetic JSON | Hospital **FHIR / HL7 ADT feed** from the ED system — *not* screen-scraping a logged-in EHR session |
| Admission criteria | Transparent demo rules in `criteria/demo_criteria.json` (illustrative, **not MCG content**) | Licensed **MCG Cite / Indicia API** |
| Physician notification | Dry-run console output | **TigerConnect / secure messaging API** under a BAA — never plain SMS |
| Decision | Always a human (physician) | Always a human (physician) |
| Audit | JSONL audit log | Same, retained per policy |

The two hard lines this prototype is built around:

1. **No credential-driven session takeover or scraping.** Real data comes
   through a sanctioned integration (FHIR/HL7), not by automating your login.
2. **No PHI over insecure channels.** SMS is not HIPAA-compliant for patient
   data; production uses a secure clinical-messaging API.

## Run it

No dependencies — standard library Python 3.9+.

```bash
cd er-mcg-bot
python -m src.ermcgbot.cli --html report.html
# or, equivalently:
PYTHONPATH=src python -m ermcgbot.cli --html report.html
```

This prints a dry-run of each physician message, writes an audit trail to
`data/audit_log.jsonl`, and produces `report.html` — the static visual to show admin.

### See it run live

```bash
python -m src.ermcgbot.cli --live live_demo.html
```

Open `live_demo.html` in any browser and press **Start shift**. Patients arrive
on the trackboard over time; the bot scans each one and fires a dry-run secure
message to the on-call physician when criteria are met. Each alert has **ADMIT /
DECLINE** buttons — tapping one closes the human-in-the-loop: it updates the
trackboard row, logs the response, and ticks the "Admitted / Declined by MD"
counters. That is the whole safety model in one gesture: the bot surfaces the
candidate, the physician decides.

It's a single self-contained file (no server, no network) that embeds the same
synthetic data and criteria the Python engine uses — the in-browser screening
logic mirrors `criteria_engine.py`, so the demo and backend can't drift (both
flag 8 of 12). This is the version to project in the admin meeting.

## Connecting to your EHR (Pulsecheck, Epic, Cerner)

The screening logic is decoupled from the data source by a `TrackboardFeed`
interface (`src/ermcgbot/feeds/`). Every adapter normalizes its EHR's data into
the same `Patient` model, so nothing downstream changes when you switch vendors.

| `--feed` | Source | Transport | Status in prototype |
|---|---|---|---|
| `synthetic` | Bundled fake board | JSON file | Fully working |
| `epic` | Epic | SMART-on-FHIR **R4** | Mapping working (offline replay of a FHIR bundle); live transport gated on creds + BAA |
| `cerner` | Cerner / Oracle Health | SMART-on-FHIR **R4** | Same shared R4 mapper as Epic |
| `pulsecheck` / `hl7` | Pulsecheck / interface engine | **HL7v2 ADT** | Demographics + location parsed; clinical values need an ORU results feed |

Try the adapters offline (no credentials needed):

```bash
python -m src.ermcgbot.cli --feed epic        # replays data/sample_fhir_bundle.json
python -m src.ermcgbot.cli --feed cerner       # same FHIR R4 mapper
python -m src.ermcgbot.cli --feed pulsecheck   # parses data/sample_pulsecheck_adt.hl7
```

**What's real vs. stubbed:** the FHIR→Patient mapping (LOINC-coded vitals/labs,
location, chief complaint, flags) is real and unit-tested against a sample R4
bundle. The *live network transport* is deliberately disabled — turning it on
needs a SMART backend-services client, the hospital's FHIR base URL + scopes,
and a BAA. Epic and Cerner share one mapper because both expose FHIR R4 with the
same resource shapes; Pulsecheck's HL7 ADT path shows the honest limitation that
ADT carries demographics/location only (the `pulsecheck` demo flags 0 patients
because no labs arrive over ADT — those come from a separate ORU/results feed).

### Run the tests

```bash
cd er-mcg-bot
PYTHONPATH=src python -m unittest discover -s tests -v
```

### Prove it runs off the network

The screening path has no ML model and no third-party calls, so it runs with
all internet egress blocked. To demonstrate that to a security reviewer:

```bash
python -m src.ermcgbot.cli --offline --feed synthetic   # blocks all egress, still works
PYTHONPATH=src python -m unittest tests.test_offline -v  # proof test
```

See `docs/offline-deployment.md` for the internal-only / no-egress
architecture, host hardening, file-drop ingestion, and the on-prem story.

## How the criteria engine works

Each ruleset in `criteria/demo_criteria.json` has optional `all_of` (every
condition must be true) and `any_of` (at least one must be true) condition
lists. A condition is `{ "field": "labs.lactate", "op": ">=", "value": 2.0 }`.
Supported operators: `>= > <= < == != in not_in exists`. Missing values never
falsely fire a rule. This keeps the demo criteria fully auditable — and the
same `ScreeningResult` interface is what an MCG-API adapter would return, so
the swap to licensed criteria is a drop-in.

## Project layout

```
er-mcg-bot/
  criteria/demo_criteria.json       # illustrative rules (NOT MCG)
  data/synthetic_patients.json      # fake ED trackboard
  data/sample_fhir_bundle.json      # fake FHIR R4 bundle (Epic/Cerner demo)
  data/sample_pulsecheck_adt.hl7    # fake HL7v2 ADT messages (Pulsecheck demo)
  data/on_call.json                 # fake on-call roster (secure handles, not phones)
  src/ermcgbot/
    models.py            # Patient, ScreeningResult, MatchedCriterion
    criteria_engine.py   # config-driven rules engine (MCG-API-swappable)
    feeds/               # pluggable EHR adapters
      base.py            #   TrackboardFeed interface
      synthetic.py       #   bundled demo data
      fhir.py            #   Epic + Cerner (shared FHIR R4 mapper, LOINC table)
      hl7.py             #   Pulsecheck / HL7v2 ADT parser
      registry.py        #   name -> feed factory
    notifier.py          # ConsoleNotifier (default) + disabled TigerConnect stub
    audit.py             # append-only JSONL audit log
    pipeline.py          # feed -> screen -> notify -> audit
    report.py            # static HTML report
    live_demo.py         # animated live demo w/ physician ADMIT/DECLINE
    cli.py               # entry point (--feed, --live, --html)
  tests/test_criteria_engine.py
  tests/test_feeds.py
```

## Before this can touch a real patient

This is the checklist to take to admin alongside the demo:

- [ ] **CMIO / physician leadership** sign-off on using automated screening for
      admission *support* (human decision preserved).
- [ ] **Compliance / Privacy Officer** review; **BAA** with any third-party
      (AI/LLM vendor, TigerConnect) that touches PHI.
- [ ] **IT / Integration**: sanctioned FHIR/HL7 ADT feed from the ED system
      (Pulsecheck/Epic/athena, depending on the site) — no scraping.
- [ ] **MCG licensing**: use MCG Cite / Indicia via its API, not re-implemented
      criteria.
- [ ] **Secure messaging**: IT-approved TigerConnect API integration mapped to
      the real on-call schedule.
- [ ] **Validation & monitoring**: measure sensitivity/specificity against UR
      nurse review before any reliance; keep the audit trail.

A note on "replacing the UR nurse": frame this to admin as *augmentation* —
the bot does the first-pass screen so the UR RN spends time on the borderline
and complex cases instead of every chart. That is a much easier sell to
clinical leadership (and to risk management) than full replacement, and it
keeps a licensed clinician accountable for the criteria calls.
