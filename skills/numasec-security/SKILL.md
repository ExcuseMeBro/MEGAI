---
name: numasec-security
description: Hand off authorized AppSec or pentest work to the Numasec terminal security agent. Use when the user requests a security audit, vulnerability assessment, scoped pentest, CTF/lab workflow, evidence collection, or security report.
---

# Numasec security

Use Numasec as a separate security specialist; MEGAI remains the task orchestrator and source of project context.

## Safety gate

- Work only on systems the user owns, labs/CTFs, or targets with explicit authorization.
- Confirm the exact target and allowed scope before active probing. If either is unclear, ask.
- Start with `/opsec strict` and the least autonomy needed.
- Never place secrets or provider credentials in findings, evidence, reports, or share bundles.

## Handoff

Numasec is interactive. Do not launch it from a non-interactive agent tool call. Tell the user to open a terminal in the target workspace and run:

```bash
megai security
```

Then use the narrowest applicable flow:

```text
/doctor
/mode appsec
/opsec strict
/runbook list
/runbook run appsec-web-triage http://localhost:3000
/share
```

Use `/mode pentest` only for explicitly authorized pentest scope. Prefer a local lab or owned development target for initial validation.

## Return to MEGAI

Import only the generated report or share artifact needed for remediation. Treat scanner output as an observation, not a verified finding; require evidence and replay steps before reporting a vulnerability as confirmed.
