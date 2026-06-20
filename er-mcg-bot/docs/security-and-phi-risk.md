# Security & PHI Risk Assessment — ED Admission-Screening Bot

*A briefing document for the conversation with administration, IT, and the
Privacy/Security Officer. Written to be handed to a security reviewer, not to
get around one.*

---

## 0. How to use this document

Do not frame the meeting as "convince me the PHI risk is acceptable." Frame it
as: **"Here is the full risk surface, here are the controls that close each
gap, and I want to build this inside your governance, not around it."** That
reframe is the single most important thing in this file. A clinician who shows
up having already done the security threat-modeling is an asset; one who shows
up with a personal API key is a liability. Be the first one.

**The honest bottom line up front:** if *you personally* obtain a Pulsecheck
API key and run this bot on a personal laptop, that is a high-severity risk and
your administrator is correct to refuse it. The same system, built with the
controls below and run inside the hospital's sanctioned environment, can have a
**near-zero net-new PHI footprint** — because it only moves data the hospital
already holds, through systems the hospital already trusts. Those are two very
different proposals. Make sure you are pitching the second one.

---

## 1. Why an API key is the "crown jewels," not a convenience

A read API key scoped to the ED trackboard does not expose *one* chart. It can
pull PHI for **every patient in the ED, continuously, for as long as the key is
valid.** Treat it accordingly:

- **Blast radius:** a leaked key is a *mass* breach (potentially >500 records →
  mandatory HHS OCR + media notification), not a single-patient incident.
- **Where it lives is the whole game.** A key hardcoded in source, committed to
  git, sitting in a `.env` on a laptop, or stored in a personal cloud account
  is the most common way real breaches happen. None of those are acceptable.
- **Static keys are weaker than short-lived tokens.** Prefer **SMART-on-FHIR
  backend-services OAuth** (short-lived, signed JWT assertions, scoped) over a
  long-lived static API key wherever the vendor supports it. Epic and Cerner
  both do; ask whether your Pulsecheck interface can.

**Controls that make a key defensible:**
- Stored in a managed secrets vault (AWS Secrets Manager, Azure Key Vault,
  HashiCorp Vault) — never in code, never in git, never on a personal device.
- **Least privilege / minimum necessary** (a HIPAA principle): read-only, ED
  scope only, only the fields the criteria need — not "all patient data."
- Automatic **rotation** and immediate revocation capability.
- **IP allow-listing** so the key only works from the hospital's sanctioned
  compute.

---

## 2. The full PHI leak surface (threat model)

| # | Vector | Risk if uncontrolled | Control |
|---|---|---|---|
| 1 | **The API credential** | Mass PHI pull if leaked | Vault, least-privilege scope, rotation, OAuth over static key, IP allow-list |
| 2 | **Data in transit** | Interception / MITM | TLS 1.2+, certificate validation on (never disabled), optional cert pinning |
| 3 | **Data at rest** (caches, logs, audit trail) | PHI on disk in plaintext | AES-256 encryption at rest, encrypted volumes, no PHI in plaintext logs |
| 4 | **The AI/LLM path** *(see §3)* | PHI disclosed to a 3rd-party model | Keep PHI out of the LLM entirely; if used, BAA + zero-retention + no-training |
| 5 | **Where the bot runs** | Unmanaged endpoint = weakest link | HIPAA-eligible managed cloud/on-prem with a BAA — **not a personal laptop** |
| 6 | **Notification channel** | PHI on carrier SMS, lock screens, phone backups (iCloud) | Secure messaging (TigerConnect): encrypted, access-controlled, remote-wipeable, no PHI on lock screen |
| 7 | **Access control to the bot/dashboard** | Unauthenticated UI = open door | SSO + MFA + role-based access control (RBAC) |
| 8 | **Audit log itself** | The audit trail contains PHI references | Access-controlled, encrypted, retained per policy, monitored |
| 9 | **Monitoring/anomaly detection** | A quiet compromise goes unnoticed | Ship logs to the hospital SIEM; alert on anomalous access volume |
| 10 | **Software supply chain** | Vulnerable dependencies | Minimal dependencies (this prototype uses only the Python standard library), dependency scanning |
| 11 | **The BAA chain** | A gap anywhere voids compliance | Signed BAAs end-to-end: Pulsecheck/EHR, cloud host, messaging vendor, any AI vendor |

---

## 3. The AI dimension — the part security teams now ask about first

This is the newest and least-understood risk, so address it head-on:

- **Sending patient data to a third-party LLM is a disclosure of PHI.** It
  requires a **BAA with that AI vendor**, and many consumer LLM endpoints will
  not sign one or contractually prohibit PHI. *(Anthropic, for example, offers
  HIPAA-eligible use under a BAA with zero-retention options — but that has to
  be set up deliberately; it is not the default for a consumer account.)*
- **Prompt retention / training on inputs** is a real leak vector: if the
  vendor stores or trains on prompts, PHI could resurface elsewhere. Require
  contractual **zero data retention** and **no training on inputs.**
- **The strongest move: keep PHI out of the model entirely.** This
  MCG-criteria use case is fundamentally a **deterministic rules evaluation** —
  "is lactate ≥ X and HR > Y?" That is exactly what this prototype's
  `criteria_engine.py` does, with **no LLM in the PHI path at all.** Telling
  your security officer "patient data never leaves our environment and is never
  sent to any AI model" removes their single biggest objection in one sentence.
  Reserve any LLM (under a BAA) for non-PHI tasks like drafting message wording.

---

## 4. Why the prototype in this repo is already safe to demo

Use this to show good faith — you built the demo *without* touching PHI on
purpose:

- **100% synthetic data.** Fabricated names, MRNs, and values. No real patient
  information is loaded, stored, or transmitted.
- **Sends nothing.** The default notifier is a dry-run console printer; the
  TigerConnect backend is a *disabled stub* that refuses to run until a BAA and
  IT-sanctioned integration exist.
- **No live EHR connectivity.** The Epic/Cerner/Pulsecheck adapters run in
  offline "replay" mode against sample files; live transport is gated and
  raises an explicit "not configured" error.
- **No LLM in the screening path.** Criteria evaluation is deterministic and
  fully auditable.
- **Audit logging built in from day one** — the first thing Compliance asks for.

---

## 5. Controls required before real PHI — mapped to the HIPAA Security Rule

Bring this as your pre-go-live checklist. It maps to the three safeguard
categories your Security Officer already works in.

**Administrative safeguards**
- [ ] Signed **BAA chain**: EHR/Pulsecheck, cloud host, messaging vendor, any AI vendor.
- [ ] **Risk analysis** documented and accepted by the Security Officer.
- [ ] Workforce access policies; who may operate/view the bot and its logs.
- [ ] **Incident response & breach notification** plan (HIPAA Breach Notification Rule).

**Physical safeguards**
- [ ] Runs in a **HIPAA-eligible managed environment**, not on personal/unmanaged devices.
- [ ] Endpoint controls (disk encryption, EDR) on any device that touches the system.

**Technical safeguards**
- [ ] **Access control:** SSO + MFA + RBAC; unique user IDs.
- [ ] **Encryption** in transit (TLS 1.2+) and at rest (AES-256).
- [ ] **Audit controls:** tamper-evident logging shipped to the SIEM; anomaly alerts.
- [ ] **Secrets management:** vaulted, rotated, least-privilege API credentials.
- [ ] **Data minimization & retention:** pull/keep only the minimum necessary; purge caches.
- [ ] **Pre-go-live security review / penetration test.**

---

## 6. Questions to put to the Pulsecheck vendor (do not assume — ask)

You cannot assert "the API is secure" without evidence from the vendor. Request:

- Their **SOC 2 Type II** report and/or **HITRUST** certification.
- A signed **BAA** (or confirmation one is in place with your hospital).
- **API security model:** OAuth/SMART vs. static key, available scopes,
  token lifetime, rate limits, IP allow-listing, and their side's audit logging.
- Their **breach notification SLA** and data-handling/retention terms.

Whether the integration is "secure enough" is a function of *their*
certifications **and** *your* configuration. Both have to be right.

---

## 7. What getting it wrong costs (so the stakes are explicit)

- **HIPAA civil penalties** scale into the **millions of dollars per year** per
  violation category; willful neglect is the top tier.
- A breach of **500+ individuals** triggers mandatory **HHS Office for Civil
  Rights** reporting, individual notice, and **media notification.**
- **State law** adds requirements (e.g., Washington's data-breach statute).
- **Personal exposure:** a workforce member who stands up a shadow system on a
  personal key can face termination and be named as the breach's root cause.
  This is the concrete reason to route the key through IT, not your laptop.

---

## 8. Bottom line for the meeting

1. **Concede the point up front:** "You're right that an API key handled wrong
   is a serious PHI risk." That earns credibility instantly.
2. **Then neutralize it:** the screening can run with **no PHI sent to any AI
   model**, **inside the hospital's HIPAA environment**, on a **least-privilege,
   vaulted, rotatable credential under the existing BAA**, notifying through
   **TigerConnect, which the hospital already trusts.** Net new PHI exposure is
   minimal because nothing leaves systems they already control.
3. **Ask for the right thing:** not "give me an API key," but "sponsor this
   through IT/Security so the credential, hosting, and BAAs are handled
   properly." That is the sentence that turns your Security Officer from an
   opponent into your project sponsor.

*This document is a planning aid, not legal advice. Final architecture and
controls must be reviewed and approved by your hospital's Privacy/Security
Officer and Compliance team.*
