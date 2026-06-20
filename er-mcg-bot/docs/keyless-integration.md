# Running Without an API Key

*How to feed the bot patient data using no vendor API key — and the one line
you must not cross.*

---

## The key fact

An API key is the *newer* integration path, not the only one. The traditional,
far-more-common hospital integration methods use **no API key at all**. So
"we can't get an API key" is not a blocker.

## Keyless options (all supported by the prototype)

| `--feed` | Method | API key? | What IT does | Carries vitals/labs? |
|---|---|---|---|---|
| `csv` | **Flat-file export** — EHR writes the trackboard to a CSV on a secure share on a schedule | No | Reuse existing report-export tooling | Yes (whatever columns they export) |
| `filedrop` | **Interface-engine file drop** — engine writes HL7 ADT/ORU files to a watched folder | No | Add a file route on the interface engine | ADT = demographics/location; add ORU for labs |
| `pulsecheck` / `hl7` | **Live HL7 feed** — interface engine streams HL7 over MLLP/TCP | No | Add the bot as an interface endpoint | ADT + ORU together = full clinical picture |
| (DB) | **Read-only reporting DB** — view into Clarity/Caboodle or Cerner reporting tables | No (DB service account) | Provision a read-only account | Yes |

Try the keyless feeds right now, with the network blocked:

```bash
python -m src.ermcgbot.cli --offline --feed csv        # 5 patients, 4 flagged
python -m src.ermcgbot.cli --offline --feed filedrop   # reads HL7 files from a folder
```

The **CSV export** is usually the easiest "yes" from IT: it reuses report
plumbing they already have, exposes no live interface, and produces a file you
can also eyeball. The **interface feed** (`hl7`) is the production-grade keyless
method most EDs already run for other downstream systems.

## Why keyless is also *more secure*, not less

- **No long-lived credential to leak.** A flat-file export or an internal HL7
  route has no portable secret that can end up in git or on a laptop.
- **Naturally off-network.** File-drop and folder reads open no sockets — they
  pair directly with the no-egress deployment (`docs/offline-deployment.md`).
- **Minimum necessary by construction.** IT controls exactly which columns/
  segments land in the export, so the bot only ever sees what it needs.

## The line you must not cross

There is exactly one keyless method that is **not acceptable**, and it is the
one that skips IT entirely: pointing the bot at your own logged-in Pulsecheck
session and **screen-scraping the web page / driving your authenticated session
with browser automation (Selenium, Playwright, an RPA bot on your login).**

Why it's disqualifying:
- It is **credential sharing** and **unauthorized automated access** — almost
  always a violation of the vendor terms and your hospital's acceptable-use
  policy.
- It puts **your personal login** behind an automated process pulling PHI for
  every ED patient continuously — if anything goes wrong, you are the named
  cause of the breach.
- It is brittle (breaks on any UI change) and invisible to IT security
  monitoring — exactly the "shadow IT" pattern compliance exists to stop.

> Robotic process automation (RPA) *can* be done compliantly — but only with
> its **own IT-provisioned service account** and Security sign-off, never by
> hijacking a clinician's personal session. If you find yourself reaching for
> "just have it read my screen after I log in," stop: use the CSV export or HL7
> feed instead and bring IT in.

## Bottom line

You do not need an API key. Ask IT for the **easiest keyless feed they can give
you — a scheduled CSV export of the ED board, or an HL7 route off the interface
engine.** Both are routine for them, neither involves a portable secret, and
both keep this inside their governance, which is what turns it from a liability
into a sanctioned project.

*Planning aid, not legal advice. Any integration must be approved by your
hospital's IT, Security, and Privacy/Compliance teams.*
