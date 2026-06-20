# Running the Screening Bot Off the Network

*How to deploy with no internet egress and no AI model in the patient-data
path — and how to prove it to a security reviewer.*

---

## The headline for your security team

**There is no machine-learning model in the screening path.** Admission
screening is deterministic rule evaluation (`lactate ≥ 2.0 and HR > 90`),
implemented in pure Python standard library (`criteria_engine.py`). There is
nothing to send to a cloud AI service, because no AI service is involved.

That means the strongest possible data-protection posture is also the *default*
design: **patient data never leaves the hospital's environment, and the process
makes zero internet connections.**

---

## "Off the network" — pick the right meaning

A bot that texts physicians cannot live on a *true* air-gap (a host with no
network connection at all), because it must reach two internal systems: the
EHR/interface-engine feed and the secure-messaging service. So there are two
real options. Name the distinction before your administrator does — it shows
you understand the constraint.

| Posture | What it means | Works for this bot? |
|---|---|---|
| **Internal-only, no internet egress** *(recommended)* | Runs on a segmented internal VLAN; firewalled so it can reach ONLY the EHR feed + TigerConnect; all public-internet egress blocked at the network. | **Yes** — full function, near-air-gap security |
| **True air-gap** | Host has no network at all; data moves by file drop; no outbound notifications possible. | Only for *batch reporting*, not live texting (see §4) |

The recommended posture gives you essentially all the security benefit of an
air-gap (PHI never touches the internet, no third-party cloud, no AI vendor)
while keeping the texting workflow working.

---

## 1. Reference architecture (internal-only, no egress)

```
  ┌─────────────────────── Hospital internal network (segmented VLAN) ──────────────────────┐
  │                                                                                          │
  │   EHR / interface engine            Screening Bot host                Secure messaging   │
  │   (Pulsecheck / Epic / Cerner)      (managed, hardened)               (TigerConnect      │
  │                                                                        on-prem/internal) │
  │     HL7v2 ADT + ORU   ───────────►   feeds/  →  criteria_engine        │                 │
  │     or FHIR R4 (internal URL)        →  notifier  ───────────────────► │                 │
  │                                      →  audit log → hospital SIEM                         │
  │                                                                                          │
  └──────────────────────────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │  ALL public-internet egress BLOCKED at firewall
                                          ✗  (no cloud, no AI API, no telemetry)
```

Key properties:
- The bot's host has **no route to the public internet** (deny-all egress,
  with a narrow allow-list to the EHR host and TigerConnect only).
- **No third-party cloud, no external LLM, no telemetry.** The codebase uses
  only the Python standard library, so there are no SaaS dependencies to
  exfiltrate to.
- Audit logs ship to the hospital's existing **SIEM** over the internal network.

---

## 2. Verifying it really makes no egress (the live demo for security)

The repo ships a process-wide egress guard so you can *prove* the claim.

```bash
# Block ALL outbound connections, then run the full pipeline anyway:
python -m src.ermcgbot.cli --offline --feed synthetic
```

With the guard active, any attempt to open an outbound socket raises
`NetworkBlocked`. The screen still completes (8/12 flagged) because nothing in
the path needs the network. Run the dedicated proof test in front of the
reviewer:

```bash
PYTHONPATH=src python -m unittest tests.test_offline -v
```

It asserts three things: (1) an internet connection attempt is blocked,
(2) an allow-listed internal host is *not* blocked, and (3) the full screening
pipeline produces identical results with egress disabled.

> In production, the OS/network firewall is the primary egress control. The
> in-process guard (`offline_guard.py`) is defense-in-depth and, just as
> usefully, a repeatable verification artifact.

---

## 3. Locking egress down at the host (production)

The in-app guard is a backstop; enforce it at the infrastructure layer too:

- **Network:** default-deny egress firewall rule; allow-list only the EHR host
  and TigerConnect endpoints (specific IP:port). No DNS to public resolvers.
- **Host:** disable outbound on the OS firewall (`nftables`/Windows Firewall)
  except the allow-list; no package managers reaching the internet at runtime.
- **Build/supply chain:** vendor all dependencies at build time on a connected
  build host, then deploy the artifact to the isolated host (this project has
  no third-party Python deps, which keeps that trivial).
- **Secrets:** the EHR credential lives in an on-prem vault, injected at
  runtime — never baked into the image or committed to git.

---

## 4. Stricter isolation: file-drop ingestion (toward air-gap)

If security wants the screening host to not even *connect* to the EHR, use the
classic interface-engine pattern: the EHR exports HL7 ADT/ORU (or a FHIR
bundle) to a **watched folder** on a one-way share; the bot reads files and
never opens a network socket inbound or outbound.

The existing HL7 adapter already parses these messages — point it at the dropped
files instead of a socket. (Outbound notification still requires reaching
TigerConnect, so true zero-network applies only if you run in *report-only*
mode and let a human relay results.)

---

## 5. If you ever want AI, keep it on-prem too

You do **not** need an LLM for MCG-style screening — keep it out of the PHI path
entirely. But if a future feature needs language understanding (e.g., parsing
free-text chief complaints):

- Self-host an **open-weights model on an on-prem GPU**, fully offline. PHI
  never leaves the building; no AI vendor, no BAA needed because no third party
  is involved.
- Keep it as a *separate, optional* component so the core deterministic screen
  remains the system of record and stays fully auditable.

---

## 6. What to say in the meeting

> "The screening logic is deterministic rules, not an AI model, so there is
> nothing to send to a cloud service. We can run it on a segmented internal
> VLAN with **all internet egress blocked at the firewall** — it reaches only
> the EHR feed and TigerConnect, both already inside our network. I can
> demonstrate the process running with every outbound connection blocked and
> still producing correct results. Patient data never touches the public
> internet and never reaches any AI vendor."

That removes the cloud/AI/3rd-party-disclosure objection entirely, and leaves
only the internal controls (credential vaulting, access control, audit) — which
are the same controls your other internal clinical systems already use.

*Planning aid, not legal advice. Final network architecture and controls must
be approved by your hospital's Security/Privacy Officer.*
